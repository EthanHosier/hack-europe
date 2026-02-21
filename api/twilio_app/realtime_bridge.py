"""
Twilio Media Stream <-> OpenAI Realtime API bridge.
Forwards audio both ways with format conversion (μ-law 8kHz <-> PCM 24kHz).
One WebSocket to Twilio, one to OpenAI Realtime; low-latency speech-to-speech.
Uses function calling to extract structured emergency data and create a case.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import struct
import time
import uuid
from typing import TYPE_CHECKING

import psycopg

import env
from agent import EmergencyAgent, EmergencyInfo

if TYPE_CHECKING:
    from fastapi import WebSocket

webhook_logger = logging.getLogger("uvicorn.error")

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime"
REALTIME_INPUT_RATE = 24000
REALTIME_OUTPUT_RATE = 24000
TWILIO_RATE = 8000

REALTIME_INSTRUCTIONS = """\
You are an emergency dispatcher on a live phone call. Speak English only. Be calm but efficient.

Your ONLY job: collect these four items, then call the tool. Nothing else.
1. Full name
2. Social security number
3. Current location (address or landmark)
4. What the emergency is

Rules:
- ONE question per turn. Max 1-2 short sentences.
- Do NOT make small talk, ask how they are, or chat. Stay on task.
- If they give extra info, acknowledge briefly ("Got it.") and ask the next missing item.
- If they go off topic, gently redirect: "I understand. I just need [missing item] to get help to you."
- Infer category (fuel/medical/shelter/food_water/rescue/other) and severity (1-5) from what they tell you. Do not ask them about category or severity.
- Once you have all four, immediately call create_emergency_case. Never read JSON aloud.
- After the tool call, say only: "Help is on the way. You can hang up when ready. Stay safe." Then stop.
- NEVER mention tools, functions, or technical details.

Start with: "Emergency services, what's your name?\""""

EMERGENCY_TOOL = {
    "type": "function",
    "name": "create_emergency_case",
    "description": "Create an emergency case once all four required fields (full_name, social_security_number, location, emergency_description) have been collected from the caller.",
    "parameters": {
        "type": "object",
        "properties": {
            "full_name": {"type": "string", "description": "Caller's full name"},
            "social_security_number": {"type": "string", "description": "Caller's SSN"},
            "location": {"type": "string", "description": "Caller's current location"},
            "emergency_description": {"type": "string", "description": "What happened and what they need"},
            "category": {
                "type": "string",
                "enum": ["fuel", "medical", "shelter", "food_water", "rescue", "other"],
            },
            "severity": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["full_name", "social_security_number", "location", "emergency_description", "category", "severity"],
    },
}

# μ-law decode table (8-bit -> 16-bit linear), same as voice_ws
_MULAW_EXPAND: list[int] = []


def _build_mulaw_expand() -> None:
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


# Linear 16-bit -> μ-law (G.711 encode). BIAS 0x84; segment + mantissa.
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


def mulaw_8k_to_pcm_24k(mulaw_base64: str) -> bytes | None:
    """Decode Twilio μ-law 8kHz base64 to PCM 16-bit 24kHz mono (base64 not applied here; return raw bytes)."""
    try:
        raw = base64.b64decode(mulaw_base64, validate=True)
        if not raw:
            return None
        _build_mulaw_expand()
        # 8kHz -> 24kHz: each sample becomes 3 samples (nearest neighbor)
        samples_8k = [_MULAW_EXPAND[b] for b in raw]
        samples_24k: list[int] = []
        for s in samples_8k:
            samples_24k.extend([s, s, s])
        return struct.pack(f"<{len(samples_24k)}h", *samples_24k)
    except Exception:
        return None


def pcm_24k_to_mulaw_8k(pcm_24k: bytes) -> bytes:
    """Convert PCM 16-bit 24kHz to μ-law 8kHz (every 3rd sample, then encode)."""
    n = len(pcm_24k) // 2
    if n == 0:
        return b""
    samples = struct.unpack(f"<{n}h", pcm_24k)
    # Downsample: take every 3rd
    samples_8k = [samples[i] for i in range(0, len(samples), 3)]
    return bytes(_linear_to_mulaw(s) for s in samples_8k)


async def run_realtime_bridge(
    twilio_ws,
    stream_sid: str,
    call_sid: str,
) -> None:
    """
    Connect to OpenAI Realtime, send session.update with instructions,
    then forward Twilio audio -> OpenAI and OpenAI response.audio.delta -> Twilio.
    """
    api_key = getattr(env, "OPENAI_API_KEY", None) or ""
    if not api_key:
        webhook_logger.warning("realtime_bridge OPENAI_API_KEY not set")
        return

    try:
        import websockets
    except ImportError:
        webhook_logger.error("realtime_bridge websockets package not installed; pip install websockets")
        return

    openai_ws = None
    try:
        # Use additional_headers (not extra_headers) so headers aren't passed to
        # loop.create_connection(), which uvloop rejects.
        openai_ws = await websockets.connect(
            OPENAI_REALTIME_URL,
            additional_headers={"Authorization": f"Bearer {api_key}"},
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
        )
        webhook_logger.info("realtime_bridge_openai stream_sid=%s", stream_sid)

        # Session update with tool + instructions + VAD
        await openai_ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "output_modalities": ["audio"],
                        "instructions": REALTIME_INSTRUCTIONS,
                        "tools": [EMERGENCY_TOOL],
                        "tool_choice": "auto",
                        "audio": {
                            "input": {
                                "format": {"type": "audio/pcm", "rate": 24000},
                                "turn_detection": {
                                    "type": "server_vad",
                                    "threshold": 0.8,
                                    "prefix_padding_ms": 500,
                                    "silence_duration_ms": 800,
                                    "create_response": True,
                                    "interrupt_response": False,
                                },
                            },
                            "output": {
                                "format": {"type": "audio/pcm", "rate": 24000},
                                "voice": "alloy",
                            },
                        },
                    },
                }
            )
        )
        # Trigger an initial greeting from the assistant.
        await openai_ws.send(json.dumps({"type": "response.create"}))

        # Half-duplex: drop user audio while AI speaks + cooldown after
        ai_speaking = False
        ai_done_at: float = 0.0  # monotonic time when AI stopped speaking
        ECHO_COOLDOWN_S = 1.0  # ignore user audio for this long after AI finishes

        async def twilio_to_openai():
            """Forward Twilio media events to OpenAI input_audio_buffer.append."""
            try:
                webhook_logger.info("realtime_twilio_listener_started stream_sid=%s", stream_sid)
                media_count = 0
                while True:
                    raw = await twilio_ws.receive_text()
                    msg = json.loads(raw)
                    ev = msg.get("event", "")
                    if ev != "media":
                        webhook_logger.info("realtime_twilio_event stream_sid=%s event=%s", stream_sid, ev)
                    else:
                        media_count += 1
                        if media_count <= 3 or media_count % 100 == 0:
                            webhook_logger.info("realtime_twilio_event stream_sid=%s event=media count=%s", stream_sid, media_count)
                    if ev == "stop":
                        webhook_logger.info(
                            "realtime_twilio_stop stream_sid=%s (call ended from Twilio)",
                            stream_sid,
                        )
                        break
                    if ev != "media":
                        continue
                    # Drop audio while AI is speaking or during echo cooldown
                    if ai_speaking or (time.monotonic() - ai_done_at < ECHO_COOLDOWN_S):
                        continue
                    media = msg.get("media") or {}
                    if media.get("track") != "inbound":
                        continue
                    payload = media.get("payload")
                    if not payload:
                        continue
                    pcm = mulaw_8k_to_pcm_24k(payload)
                    if pcm:
                        await openai_ws.send(
                            json.dumps(
                                {
                                    "type": "input_audio_buffer.append",
                                    "audio": base64.b64encode(pcm).decode("ascii"),
                                }
                            )
                        )
            except asyncio.CancelledError:
                webhook_logger.info("realtime_twilio_exit stream_sid=%s reason=cancelled", stream_sid)
            except Exception as e:
                webhook_logger.warning(
                    "realtime_twilio_exit stream_sid=%s reason=error error=%s",
                    stream_sid,
                    e,
                )

        async def _handle_tool_call(call_id: str, fn_name: str, fn_args: str) -> None:
            """Execute tool call, send result back, and trigger a goodbye response."""
            webhook_logger.info(
                "realtime_tool_call stream_sid=%s call_id=%s fn=%s args=%s",
                stream_sid, call_id, fn_name, fn_args[:200],
            )
            if fn_name != "create_emergency_case":
                await openai_ws.send(json.dumps({
                    "type": "conversation.item.create",
                    "item": {"type": "function_call_output", "call_id": call_id, "output": '{"error": "unknown function"}'},
                }))
                await openai_ws.send(json.dumps({"type": "response.create"}))
                return

            result_msg = '{"status": "error", "message": "failed to create case"}'
            try:
                args = json.loads(fn_args)
                info = EmergencyInfo(
                    full_name=args.get("full_name"),
                    social_security_number=args.get("social_security_number"),
                    location=args.get("location"),
                    emergency_description=args.get("emergency_description"),
                    category=args.get("category", "other"),
                    severity=args.get("severity", 3),
                )
                emergency_agent = EmergencyAgent(env.SUPABASE_URL)
                with psycopg.connect(env.SUPABASE_POSTGRES_URL) as conn:
                    user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"voice-{call_sid}"))
                    case_id = emergency_agent.create_case(info, user_id, conn)
                result_msg = json.dumps({"status": "ok", "case_id": case_id})
                webhook_logger.info(
                    "realtime_case_created stream_sid=%s case_id=%s call_sid=%s",
                    stream_sid, case_id, call_sid,
                )
            except Exception:
                webhook_logger.exception("realtime_case_create_error stream_sid=%s", stream_sid)

            # Send tool result so the model can confirm + say goodbye
            await openai_ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {"type": "function_call_output", "call_id": call_id, "output": result_msg},
            }))
            await openai_ws.send(json.dumps({"type": "response.create"}))

        async def _end_call_via_twilio() -> None:
            """Use Twilio REST API to hang up the call after the goodbye plays."""
            try:
                from twilio.rest import Client as TwilioClient
                client = TwilioClient(env.TWILIO_ACCOUNT_SID, env.TWILIO_AUTH_TOKEN)
                client.calls(call_sid).update(status="completed")
                webhook_logger.info("realtime_call_ended stream_sid=%s call_sid=%s", stream_sid, call_sid)
            except Exception:
                webhook_logger.exception("realtime_call_end_error stream_sid=%s", stream_sid)

        async def openai_to_twilio():
            """Forward OpenAI audio deltas to Twilio media and handle tool calls."""
            openai_event_count = 0
            case_created = False
            try:
                webhook_logger.info("realtime_openai_listener_started stream_sid=%s", stream_sid)
                while True:
                    try:
                        message = await openai_ws.recv()
                    except Exception as recv_err:
                        webhook_logger.info(
                            "realtime_openai_exit stream_sid=%s reason=recv_error error=%s",
                            stream_sid, recv_err,
                        )
                        break
                    if isinstance(message, bytes):
                        message = message.decode("utf-8")
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        continue
                    typ = data.get("type") or ""
                    openai_event_count += 1
                    # Log non-audio events (audio deltas are too frequent)
                    if typ != "response.output_audio.delta":
                        webhook_logger.info(
                            "realtime_openai_event stream_sid=%s type=%s",
                            stream_sid, typ,
                        )

                    # --- Audio: forward to Twilio, mark AI as speaking ---
                    if typ == "response.output_audio.delta":
                        nonlocal ai_speaking, ai_done_at
                        ai_speaking = True
                        audio_b64 = data.get("delta") or data.get("audio")
                        if audio_b64:
                            pcm_24k = base64.b64decode(audio_b64)
                            ulaw_8k = pcm_24k_to_mulaw_8k(pcm_24k)
                            if ulaw_8k:
                                chunk_b64 = base64.b64encode(ulaw_8k).decode("ascii")
                                await twilio_ws.send_json(
                                    {"event": "media", "streamSid": stream_sid, "media": {"payload": chunk_b64}}
                                )

                    # --- AI finished speaking: clear flag, record time, flush buffer ---
                    elif typ == "response.output_audio.done":
                        ai_speaking = False
                        ai_done_at = time.monotonic()
                        try:
                            await openai_ws.send(json.dumps({"type": "input_audio_buffer.clear"}))
                        except Exception:
                            pass
                        if case_created:
                            webhook_logger.info(
                                "realtime_goodbye_done stream_sid=%s — ending call",
                                stream_sid,
                            )
                            await asyncio.sleep(1.5)
                            await _end_call_via_twilio()
                            break

                    # --- Function call complete: execute tool ---
                    elif typ == "response.done":
                        response = data.get("response", {})
                        for output_item in response.get("output", []):
                            if output_item.get("type") == "function_call":
                                await _handle_tool_call(
                                    output_item.get("call_id", ""),
                                    output_item.get("name", ""),
                                    output_item.get("arguments", "{}"),
                                )
                                case_created = True

                    elif typ == "error":
                        webhook_logger.warning("realtime_bridge_openai_error stream_sid=%s body=%s", stream_sid, data)

            except asyncio.CancelledError:
                webhook_logger.info(
                    "realtime_openai_exit stream_sid=%s reason=cancelled events_received=%s",
                    stream_sid, openai_event_count,
                )
            except Exception as e:
                webhook_logger.warning(
                    "realtime_openai_exit stream_sid=%s reason=error error=%s events_received=%s",
                    stream_sid, e, openai_event_count,
                )

        # Run both directions; stop when Twilio disconnects or OpenAI closes
        twilio_task = asyncio.create_task(twilio_to_openai())
        openai_task = asyncio.create_task(openai_to_twilio())
        done, pending = await asyncio.wait(
            [twilio_task, openai_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        # Log which task(s) finished (can be both if they closed at once)
        for t in done:
            which = "twilio" if t == twilio_task else "openai"
            webhook_logger.info(
                "realtime_task_completed stream_sid=%s task=%s",
                stream_sid,
                which,
            )
        for t in pending:
            t.cancel()
        await asyncio.gather(twilio_task, openai_task, return_exceptions=True)
    except Exception:
        webhook_logger.exception("realtime_bridge_error stream_sid=%s", stream_sid)
    finally:
        if openai_ws:
            try:
                await openai_ws.close()
            except Exception:
                pass


async def handle_realtime_voice_stream(websocket: "WebSocket") -> None:
    """WebSocket handler: accept Twilio, then run the Realtime bridge."""
    await websocket.accept()
    stream_sid: str | None = None
    call_sid: str | None = None
    try:
        # Consume connected + start to get stream_sid and call_sid
        for _ in range(2):
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            ev = msg.get("event")
            if ev == "connected":
                webhook_logger.info("realtime_voice_ws_connected stream_sid=%s", msg.get("streamSid"))
            elif ev == "start":
                stream_sid = msg.get("streamSid")
                start = msg.get("start") or {}
                call_sid = start.get("callSid")
                webhook_logger.info("realtime_voice_ws_start stream_sid=%s call_sid=%s", stream_sid, call_sid)
                break
        if stream_sid:
            await run_realtime_bridge(websocket, stream_sid, call_sid or "")
        else:
            webhook_logger.warning("realtime_voice_ws no stream_sid")
    except Exception:
        webhook_logger.exception("realtime_voice_ws_error")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
