"""Twilio Media Stream WebSocket handler (connected, start, media, stop, mark, dtmf)."""

import json
import logging

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

webhook_logger = logging.getLogger("uvicorn.error")


async def handle_voice_media_stream(websocket: WebSocket) -> None:
    """
    Handle a single Twilio bidirectional Media Stream.
    Receives: connected, start, media, stop, mark, dtmf.
    Sends: media (TTS), mark, clear when implemented.
    """
    await websocket.accept()
    stream_sid: str | None = None
    call_sid: str | None = None
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
                if media.get("track") == "inbound" and stream_sid:
                    try:
                        chunk_num = int(media.get("chunk") or "0")
                        if chunk_num <= 2 or chunk_num % 50 == 0:
                            webhook_logger.debug(
                                "voice_ws_media stream_sid=%s chunk=%s",
                                stream_sid,
                                chunk_num,
                            )
                    except (TypeError, ValueError):
                        pass
            elif event == "stop":
                stop = msg.get("stop") or {}
                webhook_logger.info(
                    "voice_ws_stop stream_sid=%s call_sid=%s",
                    msg.get("streamSid"),
                    stop.get("callSid"),
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
