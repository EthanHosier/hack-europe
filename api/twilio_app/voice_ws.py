"""Twilio Media Stream WebSocket handler (connected, start, media, stop, mark, dtmf)."""

import base64
import json
import logging
import math

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

webhook_logger = logging.getLogger("uvicorn.error")

# Log when this many consecutive silent chunks (~50 chunks/sec → 50 ≈ 1 sec, 100 ≈ 2 sec)
SILENCE_CHUNKS_FOR_LOG = 50
# Audio threshold: chunk is "silent" if RMS (linear PCM, 0–32767) is below this
AUDIO_SILENCE_THRESHOLD = 200

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
                # Log sound/silence transitions (not every chunk)
                if last_chunk_was_silent is False and silent:
                    webhook_logger.info(
                        "voice_ws_silence_detected stream_sid=%s call_sid=%s rms=%.0f threshold=%s",
                        stream_sid,
                        call_sid,
                        rms,
                        AUDIO_SILENCE_THRESHOLD,
                    )
                elif last_chunk_was_silent is True and not silent:
                    webhook_logger.info(
                        "voice_ws_sound_detected stream_sid=%s call_sid=%s rms=%.0f threshold=%s",
                        stream_sid,
                        call_sid,
                        rms,
                        AUDIO_SILENCE_THRESHOLD,
                    )
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
