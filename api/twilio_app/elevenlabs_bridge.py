"""
Twilio Media Stream <-> ElevenLabs Conversational AI bridge.
Converts audio between Twilio μ-law 8kHz and ElevenLabs PCM 16-bit 16kHz.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import struct
from typing import TYPE_CHECKING

import env

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger("uvicorn.error")

ELEVENLABS_CONVAI_URL = "wss://api.elevenlabs.io/v1/convai/conversation"

# ── Audio conversion: μ-law 8kHz (Twilio) ↔ PCM 16-bit 16kHz (ElevenLabs) ──

_MULAW_EXPAND: list[int] = []


def _build_mulaw_table() -> None:
    global _MULAW_EXPAND
    if _MULAW_EXPAND:
        return
    for u in range(256):
        x = 255 - u
        sign = x & 0x80
        exp = (x >> 4) & 0x07
        mant = x & 0x0F
        sample = ((mant << 3) + 0x84) << exp
        sample = -sample if sign else sample
        _MULAW_EXPAND.append(max(-32768, min(32767, sample)))


def _linear_to_mulaw(sample: int) -> int:
    sign = 0x80 if sample < 0 else 0
    sample = min(8031, abs(sample))
    sample += 0x84
    exp = 7
    for i in range(8):
        if sample <= (0x0F << (i + 3)):
            exp = i
            break
    mant = (sample >> (exp + 3)) & 0x0F
    u = sign | (exp << 4) | mant
    return 255 - u


def mulaw_8k_to_pcm_16k(mulaw_b64: str) -> bytes | None:
    """Decode Twilio μ-law 8kHz base64 → PCM 16-bit 16kHz (2x upsample)."""
    try:
        raw = base64.b64decode(mulaw_b64, validate=True)
        if not raw:
            return None
        _build_mulaw_table()
        samples_8k = [_MULAW_EXPAND[b] for b in raw]
        samples_16k: list[int] = []
        for s in samples_8k:
            samples_16k.extend([s, s])
        return struct.pack(f"<{len(samples_16k)}h", *samples_16k)
    except Exception:
        return None


def pcm_16k_to_mulaw_8k(pcm_16k: bytes) -> bytes:
    """Convert PCM 16-bit 16kHz → μ-law 8kHz (take every 2nd sample)."""
    n = len(pcm_16k) // 2
    if n == 0:
        return b""
    samples = struct.unpack(f"<{n}h", pcm_16k)
    samples_8k = [samples[i] for i in range(0, len(samples), 2)]
    return bytes(_linear_to_mulaw(s) for s in samples_8k)


def _get_signed_url(agent_id: str) -> str:
    """Get a signed WebSocket URL for private agents, or build a public one."""
    api_key = env.ELEVEN_LABS_API_KEY
    if api_key:
        import httpx
        resp = httpx.get(
            f"https://api.elevenlabs.io/v1/convai/conversation/get-signed-url?agent_id={agent_id}",
            headers={"xi-api-key": api_key},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("signed_url", f"{ELEVENLABS_CONVAI_URL}?agent_id={agent_id}")
    return f"{ELEVENLABS_CONVAI_URL}?agent_id={agent_id}"


async def run_elevenlabs_bridge(
    twilio_ws: "WebSocket",
    stream_sid: str,
    call_sid: str,
) -> None:
    """Bridge Twilio Media Stream audio to/from ElevenLabs Conversational AI."""
    agent_id = env.ELEVENLABS_AGENT_ID
    if not agent_id:
        logger.warning("elevenlabs_bridge ELEVENLABS_AGENT_ID not set")
        return

    try:
        import websockets
    except ImportError:
        logger.error("elevenlabs_bridge websockets package not installed")
        return

    elevenlabs_ws = None
    try:
        ws_url = _get_signed_url(agent_id)
        elevenlabs_ws = await websockets.connect(
            ws_url,
            ping_interval=None,
            close_timeout=5,
        )
        logger.info("elevenlabs_bridge_connected stream_sid=%s agent_id=%s", stream_sid, agent_id)

        import time
        last_agent_audio_at: float = 0.0
        ECHO_COOLDOWN_S = 1.5  # silence user mic for 1.5s after last agent audio chunk

        async def twilio_to_elevenlabs():
            """Forward Twilio media payloads to ElevenLabs as user_audio_chunk."""
            try:
                media_count = 0
                send_count = 0
                dropped_count = 0
                convert_fail_count = 0
                while True:
                    raw = await twilio_ws.receive_text()
                    msg = json.loads(raw)
                    ev = msg.get("event", "")

                    if ev == "stop":
                        logger.info("elevenlabs_twilio_stop stream_sid=%s sent=%s dropped=%s convert_fails=%s", stream_sid, send_count, dropped_count, convert_fail_count)
                        break
                    if ev != "media":
                        if ev not in ("connected", "start"):
                            logger.info("elevenlabs_twilio_event stream_sid=%s event=%s", stream_sid, ev)
                        continue

                    media_count += 1

                    # Half-duplex: drop user audio while agent is speaking
                    # (prevents phone echo from triggering ElevenLabs interruptions)
                    if time.monotonic() - last_agent_audio_at < ECHO_COOLDOWN_S:
                        dropped_count += 1
                        continue

                    if media_count <= 5 or media_count % 200 == 0:
                        logger.info("elevenlabs_twilio_media stream_sid=%s count=%s sent=%s dropped=%s", stream_sid, media_count, send_count, dropped_count)

                    payload = (msg.get("media") or {}).get("payload")
                    if not payload:
                        continue

                    pcm = mulaw_8k_to_pcm_16k(payload)
                    if pcm:
                        send_count += 1
                        await elevenlabs_ws.send(json.dumps({
                            "user_audio_chunk": base64.b64encode(pcm).decode("ascii"),
                        }))
                    else:
                        convert_fail_count += 1
                        if convert_fail_count <= 5:
                            logger.warning("elevenlabs_twilio_convert_fail stream_sid=%s count=%s payload_len=%s", stream_sid, media_count, len(payload))
            except asyncio.CancelledError:
                logger.info("elevenlabs_twilio_exit stream_sid=%s reason=cancelled sent=%s dropped=%s", stream_sid, send_count, dropped_count)
            except Exception as e:
                logger.warning("elevenlabs_twilio_exit stream_sid=%s error=%s sent=%s dropped=%s", stream_sid, e, send_count, dropped_count)

        async def elevenlabs_to_twilio():
            """Forward ElevenLabs audio to Twilio + handle ping/pong and interruptions."""
            event_count = 0
            audio_chunk_count = 0
            try:
                while True:
                    try:
                        raw = await elevenlabs_ws.recv()
                    except Exception as e:
                        logger.info("elevenlabs_recv_exit stream_sid=%s error=%s events=%s audio_chunks=%s", stream_sid, e, event_count, audio_chunk_count)
                        break

                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("elevenlabs_json_error stream_sid=%s raw=%s", stream_sid, raw[:200])
                        continue

                    msg_type = data.get("type", "")
                    event_count += 1

                    if msg_type == "audio":
                        nonlocal last_agent_audio_at
                        last_agent_audio_at = time.monotonic()
                        audio_b64 = (data.get("audio_event") or {}).get("audio_base_64")
                        if audio_b64:
                            audio_chunk_count += 1
                            if audio_chunk_count <= 3 or audio_chunk_count % 100 == 0:
                                logger.info("elevenlabs_audio_chunk stream_sid=%s chunk=%s b64_len=%s", stream_sid, audio_chunk_count, len(audio_b64))
                            pcm_16k = base64.b64decode(audio_b64)
                            ulaw_8k = pcm_16k_to_mulaw_8k(pcm_16k)
                            if ulaw_8k:
                                await twilio_ws.send_json({
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {"payload": base64.b64encode(ulaw_8k).decode("ascii")},
                                })

                    elif msg_type == "interruption":
                        logger.info("elevenlabs_interruption stream_sid=%s", stream_sid)
                        await twilio_ws.send_json({"event": "clear", "streamSid": stream_sid})

                    elif msg_type == "ping":
                        event_id = (data.get("ping_event") or {}).get("event_id")
                        if event_id is not None:
                            logger.info("elevenlabs_ping stream_sid=%s event_id=%s", stream_sid, event_id)
                            await elevenlabs_ws.send(json.dumps({
                                "type": "pong",
                                "event_id": event_id,
                            }))

                    elif msg_type == "conversation_initiation_metadata":
                        logger.info("elevenlabs_conversation_initiated stream_sid=%s", stream_sid)

                    elif msg_type == "user_transcript":
                        transcript = (data.get("user_transcription_event") or {}).get("user_transcript", "")
                        logger.info("elevenlabs_user_transcript stream_sid=%s text=%s", stream_sid, transcript[:200])

                    elif msg_type == "agent_response":
                        response = (data.get("agent_response_event") or {}).get("agent_response", "")
                        logger.info("elevenlabs_agent_response stream_sid=%s text=%s", stream_sid, response[:200])

                    elif msg_type == "vad_score":
                        pass  # too noisy to log

                    else:
                        logger.info("elevenlabs_event stream_sid=%s type=%s data=%s", stream_sid, msg_type, json.dumps(data)[:300])

            except asyncio.CancelledError:
                logger.info("elevenlabs_exit stream_sid=%s reason=cancelled events=%s audio_chunks=%s", stream_sid, event_count, audio_chunk_count)
            except Exception as e:
                logger.warning("elevenlabs_exit stream_sid=%s error=%s events=%s audio_chunks=%s", stream_sid, e, event_count, audio_chunk_count)

        twilio_task = asyncio.create_task(twilio_to_elevenlabs())
        elevenlabs_task = asyncio.create_task(elevenlabs_to_twilio())
        done, pending = await asyncio.wait(
            [twilio_task, elevenlabs_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in done:
            which = "twilio" if t == twilio_task else "elevenlabs"
            logger.info("elevenlabs_task_completed stream_sid=%s task=%s", stream_sid, which)
        for t in pending:
            t.cancel()
        await asyncio.gather(twilio_task, elevenlabs_task, return_exceptions=True)

    except Exception:
        logger.exception("elevenlabs_bridge_error stream_sid=%s", stream_sid)
    finally:
        if elevenlabs_ws:
            try:
                await elevenlabs_ws.close()
            except Exception:
                pass


async def handle_elevenlabs_voice_stream(websocket: "WebSocket") -> None:
    """WebSocket handler: accept Twilio, then run the ElevenLabs bridge."""
    await websocket.accept()
    stream_sid: str | None = None
    call_sid: str | None = None
    try:
        for _ in range(2):
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            ev = msg.get("event")
            if ev == "connected":
                logger.info("elevenlabs_voice_ws_connected stream_sid=%s", msg.get("streamSid"))
            elif ev == "start":
                stream_sid = msg.get("streamSid")
                start = msg.get("start") or {}
                call_sid = start.get("callSid")
                logger.info("elevenlabs_voice_ws_start stream_sid=%s call_sid=%s", stream_sid, call_sid)
                break
        if stream_sid:
            await run_elevenlabs_bridge(websocket, stream_sid, call_sid or "")
        else:
            logger.warning("elevenlabs_voice_ws no stream_sid")
    except Exception:
        logger.exception("elevenlabs_voice_ws_error")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
