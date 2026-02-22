"""Twilio Media Stream WebSocket handler (connected, start, media, stop, mark, dtmf)."""

import asyncio
import base64
import io
import json
import logging
import math
import struct

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

import env
from elevenlabs import text_to_speech as elevenlabs_tts
from voice_agent import VoiceAgent

import psycopg
from agent import EmergencyAgent

webhook_logger = logging.getLogger("uvicorn.error")
try:
    _voice_agent = VoiceAgent()
    _voice_agent_init_error: Exception | None = None
except Exception as exc:
    _voice_agent = None
    _voice_agent_init_error = exc
    webhook_logger.warning(
        "voice_agent_disabled reason=%s",
        exc,
    )

# Log when this many consecutive silent chunks (~50 chunks/sec → 50 ≈ 1 sec, 100 ≈ 2 sec)
SILENCE_CHUNKS_FOR_LOG = 50
# Minimum chunks of audio to send to Whisper (~0.5 sec)
MIN_CHUNKS_FOR_WHISPER = 25
# Audio threshold: chunk is "silent" if RMS (linear PCM, 0–32767) is below this
AUDIO_SILENCE_THRESHOLD = 200
# Twilio outbound media: 20ms per chunk at 8kHz μ-law = 160 bytes
OUTBOUND_CHUNK_BYTES = 160

# G.711 μ-law decode table (8-bit mulaw -> 16-bit linear)
_MULAW_EXPAND_TABLE: list[int] = []


def _build_mulaw_table() -> None:
    global _MULAW_EXPAND_TABLE
    if _MULAW_EXPAND_TABLE:
        return
    for u in range(256):
        u = 255 - u
        sign = u & 0x80
        exp = (u >> 4) & 0x07
        mant = u & 0x0F
        sample = ((mant << 3) + 0x84) << exp
        sample = -sample if sign else sample
        sample = max(-32768, min(32767, sample))
        _MULAW_EXPAND_TABLE.append(sample)


def _mulaw_payload_rms(payload_base64: str) -> float:
    """Decode base64 mulaw to linear PCM and return RMS. Returns 0.0 if decode fails."""
    try:
        raw = base64.b64decode(payload_base64, validate=True)
        if not raw:
            return 0.0
        _build_mulaw_table()
        linear = [_MULAW_EXPAND_TABLE[b] for b in raw]
        n = len(linear)
        if n == 0:
            return 0.0
        sum_sq = sum(x * x for x in linear)
        return math.sqrt(sum_sq / n)
    except Exception:
        return 0.0


def _is_silent(payload_base64: str) -> bool:
    """True if chunk audio level (RMS) is below the silence threshold."""
    return _mulaw_payload_rms(payload_base64) < AUDIO_SILENCE_THRESHOLD


def _mulaw_payloads_to_wav(payloads_base64: list[str], sample_rate: int = 8000) -> bytes | None:
    """Decode base64 μ-law payloads to 16-bit PCM and return a WAV file in memory. Returns None if empty or invalid."""
    if not payloads_base64:
        return None
    _build_mulaw_table()
    samples: list[int] = []
    for p in payloads_base64:
        try:
            raw = base64.b64decode(p, validate=True)
            for b in raw:
                samples.append(_MULAW_EXPAND_TABLE[b])
        except Exception:
            continue
    if not samples:
        return None
    # WAV: RIFF + fmt + data
    pcm = struct.pack(f"<{len(samples)}h", *samples)
    n = len(pcm)
    byte_rate = sample_rate * 2
    header = (
        b"RIFF"
        + struct.pack("<I", 36 + n)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, byte_rate, 2, 16)
        + b"data"
        + struct.pack("<I", n)
    )
    return header + pcm


async def _send_tts_to_call(websocket: WebSocket, stream_sid: str, text: str) -> None:
    """Generate TTS for text via ElevenLabs and stream μ-law chunks back over the call."""
    loop = asyncio.get_event_loop()
    try:
        audio_bytes = await loop.run_in_executor(None, lambda: elevenlabs_tts(text))
    except Exception:
        webhook_logger.exception("voice_ws_tts_generate_error stream_sid=%s", stream_sid)
        return
    if not audio_bytes:
        return
    try:
        for i in range(0, len(audio_bytes), OUTBOUND_CHUNK_BYTES):
            chunk = audio_bytes[i : i + OUTBOUND_CHUNK_BYTES]
            if not chunk:
                break
            payload_b64 = base64.b64encode(chunk).decode("ascii")
            msg = {
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": payload_b64},
            }
            await websocket.send_json(msg)
            await asyncio.sleep(0.02)
    except Exception:
        webhook_logger.exception("voice_ws_tts_send_error stream_sid=%s", stream_sid)


async def _whisper_transcribe(wav_bytes: bytes) -> str | None:
    """Transcribe WAV bytes with OpenAI Whisper. Returns None if key missing or API error."""
    if not env.OPENAI_API_KEY:
        webhook_logger.warning("voice_ws_whisper_skip OPENAI_API_KEY not set")
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=env.OPENAI_API_KEY)
        file_like = io.BytesIO(wav_bytes)
        file_like.name = "audio.wav"
        resp = client.audio.transcriptions.create(model="whisper-1", file=file_like, response_format="text")
        return (resp if isinstance(resp, str) else getattr(resp, "text", None)) or None
    except Exception:
        webhook_logger.exception("voice_ws_whisper_error")
        return None


async def handle_voice_media_stream(websocket: WebSocket) -> None:
    """
    Handle a single Twilio bidirectional Media Stream.
    Receives: connected, start, media, stop, mark, dtmf.
    Detects silence; logs when 2 seconds pass without talking.
    """
    await websocket.accept()
    stream_sid: str | None = None
    call_sid: str | None = None
    consecutive_silent_chunks = 0
    max_consecutive_silent_chunks_seen = 0
    last_chunk_was_silent: bool | None = None
    media_chunk_count = 0
    already_logged_2s_silence = False
    utterance_buffer: list[str] = []
    conversation_history: list[dict[str, str]] = []

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                webhook_logger.warning("voice_ws_invalid_json stream_sid=%s raw=%s", stream_sid, raw[:200])
                continue

            event = msg.get("event")
            if event == "connected":
                webhook_logger.info(
                    "voice_ws_connected protocol=%s version=%s",
                    msg.get("protocol"),
                    msg.get("version"),
                )
            elif event == "start":
                stream_sid = msg.get("streamSid")
                start = msg.get("start") or {}
                call_sid = start.get("callSid")
                custom = start.get("customParameters") or {}
                webhook_logger.info(
                    "voice_ws_start stream_sid=%s call_sid=%s custom=%s",
                    stream_sid,
                    call_sid,
                    json.dumps(custom, ensure_ascii=False),
                )
            elif event == "media":
                media = msg.get("media") or {}
                if media.get("track") != "inbound" or not stream_sid:
                    continue
                payload = media.get("payload")
                if not payload:
                    continue
                media_chunk_count += 1
                rms = _mulaw_payload_rms(payload)
                silent = rms < AUDIO_SILENCE_THRESHOLD
                last_chunk_was_silent = silent
                # Periodic RMS at DEBUG for tuning
                if media_chunk_count % 50 == 0:
                    webhook_logger.debug(
                        "voice_ws_media_rms stream_sid=%s chunks=%s rms=%.0f silent=%s",
                        stream_sid,
                        media_chunk_count,
                        rms,
                        silent,
                    )
                utterance_buffer.append(payload)
                if silent:
                    consecutive_silent_chunks += 1
                    if consecutive_silent_chunks > max_consecutive_silent_chunks_seen:
                        max_consecutive_silent_chunks_seen = consecutive_silent_chunks
                    if consecutive_silent_chunks >= SILENCE_CHUNKS_FOR_LOG and not already_logged_2s_silence:
                        webhook_logger.info(
                            "voice_ws_2s_silence stream_sid=%s call_sid=%s — 2 seconds without talking",
                            stream_sid,
                            call_sid,
                        )
                        # Transcribe utterance (audio before the 2s silence) with Whisper
                        speech_payloads = utterance_buffer[:-SILENCE_CHUNKS_FOR_LOG]
                        if len(speech_payloads) >= MIN_CHUNKS_FOR_WHISPER:
                            wav_bytes = _mulaw_payloads_to_wav(speech_payloads)
                            if wav_bytes:
                                text = await _whisper_transcribe(wav_bytes)
                                if text is not None:
                                    transcript = text.strip()
                                    webhook_logger.info(
                                        "voice_ws_whisper_transcription stream_sid=%s call_sid=%s text=%s",
                                        stream_sid,
                                        call_sid,
                                        transcript,
                                    )
                                    if transcript:
                                        loop = asyncio.get_event_loop()
                                        try:
                                            if _voice_agent is None:
                                                response_text = (
                                                    "Voice AI is unavailable right now. "
                                                    "Please try again later."
                                                )
                                                should_end_call = False
                                                info = None
                                            else:
                                                response_text, info, should_end_call = await loop.run_in_executor(
                                                    None,
                                                    lambda: _voice_agent.process_utterance(
                                                        transcript, conversation_history
                                                    ),
                                                )
                                        except Exception:
                                            webhook_logger.exception(
                                                "voice_ws_agent_error stream_sid=%s", stream_sid
                                            )
                                            response_text = "I'm sorry, I had a small problem. Please try again."
                                            should_end_call = False
                                            info = None
                                        conversation_history.append({"role": "user", "content": transcript})
                                        conversation_history.append({"role": "assistant", "content": response_text})
                                        if should_end_call and info and call_sid:
                                            try:
                                                emergency_agent = EmergencyAgent(env.SUPABASE_URL)
                                                with psycopg.connect(env.SUPABASE_POSTGRES_URL) as conn:
                                                    case_id = emergency_agent.create_case(
                                                        info, f"voice-{call_sid}", conn
                                                    )
                                                    webhook_logger.info(
                                                        "voice_ws_case_created stream_sid=%s case_id=%s",
                                                        stream_sid,
                                                        case_id,
                                                    )
                                            except Exception:
                                                webhook_logger.exception(
                                                    "voice_ws_case_create_error stream_sid=%s",
                                                    stream_sid,
                                                )
                                        if response_text:
                                            if should_end_call:
                                                await _send_tts_to_call(
                                                    websocket, stream_sid, response_text
                                                )
                                                break
                                            asyncio.create_task(
                                                _send_tts_to_call(
                                                    websocket, stream_sid, response_text
                                                )
                                            )
                                else:
                                    webhook_logger.info(
                                        "voice_ws_whisper_transcription stream_sid=%s call_sid=%s text=(none)",
                                        stream_sid,
                                        call_sid,
                                    )
                        utterance_buffer = []
                        already_logged_2s_silence = True
                else:
                    consecutive_silent_chunks = 0
                    already_logged_2s_silence = False
            elif event == "stop":
                stop = msg.get("stop") or {}
                webhook_logger.info(
                    "voice_ws_stop stream_sid=%s call_sid=%s",
                    msg.get("streamSid"),
                    stop.get("callSid"),
                )
                webhook_logger.debug(
                    "voice_ws_silence_stats stream_sid=%s max_consecutive_silent_chunks=%s (need %s for 2s log)",
                    stream_sid,
                    max_consecutive_silent_chunks_seen,
                    SILENCE_CHUNKS_FOR_LOG,
                )
                break
            elif event == "mark":
                webhook_logger.debug("voice_ws_mark stream_sid=%s mark=%s", stream_sid, msg.get("mark"))
            elif event == "dtmf":
                webhook_logger.info(
                    "voice_ws_dtmf stream_sid=%s digit=%s",
                    stream_sid,
                    (msg.get("dtmf") or {}).get("digit"),
                )
            else:
                webhook_logger.debug("voice_ws_unknown event=%s stream_sid=%s", event, stream_sid)
    except WebSocketDisconnect:
        webhook_logger.info("voice_ws_disconnect stream_sid=%s call_sid=%s", stream_sid, call_sid)
    except Exception:
        webhook_logger.exception("voice_ws_error stream_sid=%s call_sid=%s", stream_sid, call_sid)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
