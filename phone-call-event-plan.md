# Plan: Twilio Voice Call → Real-Time Transcript → Conversation Agent → TTS Back

## High-Level Flow

1. **Incoming call** → Twilio hits your **voice webhook** (HTTP).
2. **Answer + stream** → You return TwiML that **connects** the call to a **WebSocket** (bidirectional Media Stream).
3. **Audio in** → Twilio sends caller audio to your WebSocket (base64 mulaw 8kHz).
4. **Transcription** → You turn that audio into text (Whisper or Realtime API).
5. **Agent** → A “conversation agent” gets the transcript, extracts info, and decides: **ask a follow-up** or **end call** (with a final message).
6. **TTS** → Agent’s reply text is turned into speech (ElevenLabs).
7. **Audio out** → You convert TTS to **8kHz mulaw**, base64, and send over the same WebSocket to Twilio so the user hears it.
8. **End call** → When the agent says “end call”, you close the WebSocket (and optionally hang up via Twilio REST if needed).

---

## 1. Twilio Voice + Media Streams

- **New webhook (HTTP)**

  - e.g. `POST /twilio/webhooks/voice` (or `/voice/incoming`).
  - Twilio sends `CallSid`, `From`, `To`, etc.
  - You **must** respond with **TwiML** (XML), not JSON.

- **TwiML for “answer and stream”**

  - Use **`<Connect><Stream url="wss://...">`** so the call is **bidirectional**:
    - You receive caller audio.
    - You send audio back (TTS).
  - The `url` must be a **public WSS URL** to your own WebSocket server (see below).
  - No query params on `url`; pass call context via **`<Parameter>`** (e.g. `CallSid`, `From`).

- **WebSocket server**

  - Twilio opens **one WebSocket per call** to the URL you put in `<Stream>`.
  - Messages: `connected`, `start` (with `streamSid`, `callSid`, `customParams`), `media` (base64 mulaw chunks), `stop`.
  - You **send back** audio as JSON: `{"event":"media","streamSid":"...","media":{"payload":"<base64 mulaw>"}}`.
  - **Important:** Your API runs on **ECS** (long-lived process), so a WebSocket server in the same FastAPI app is feasible (e.g. with `websockets` or Starlette WebSocket). You’ll need a **public URL** that reaches that server (same host as API or a dedicated subdomain) and **WSS** (TLS).
  - If the API is behind CloudFront/ALB, confirm they support WebSocket upgrade (ALB does; CloudFront can with the right config).

- **Infra / URL**
  - Ensure the voice webhook URL and the Media Stream `wss://` URL are reachable from the internet (and that Twilio can connect to the WSS host).
  - Optional: **statusCallback** on `<Stream>` to get `stream-started` / `stream-stopped` / `stream-error` for logging.

---

## 2. Real-Time Transcription (Whisper)

- **Two main options:**

  - **OpenAI Realtime API (WebSocket)**
    - True streaming: send audio chunks, get incremental transcripts (e.g. `conversation.item.input_audio_transcription.delta`).
    - Input: PCM 24 kHz mono (you’d need to convert from Twilio’s mulaw 8kHz → PCM and resample, or use an intermediate format the Realtime API accepts).
  - **Whisper HTTP API (batch)**
    - Send chunks of audio (e.g. every 2–5 seconds or on silence); get back text.
    - Simpler integration; slightly higher latency and no true “streaming” UX.

- **Recommendation for “real time”**

  - **Option A:** Realtime API for lowest latency and incremental text.
  - **Option B:** Whisper on fixed or VAD-based chunks (e.g. 3–5 s) to keep the pipeline simpler; agent reacts on each chunk.

- **Format pipeline**
  - Twilio → base64 mulaw 8kHz.
  - Decode mulaw → linear PCM, resample to 24kHz (for Realtime) or 16kHz (common for Whisper file API).
  - Send to OpenAI; get transcript (streaming or per chunk).

---

## 3. Conversation Agent

- **Role:**

  - Consumes **accumulated transcript** (and optionally previous turns).
  - Extracts **structured information** (e.g. name, incident type, location, severity).
  - Decides: **continue** (next question or prompt) or **end call** (with a closing message).

- **Design choices:**

  - **State:** Keep per-call state (e.g. by `CallSid` or `streamSid`): transcript buffer, extracted fields, turn count.
  - **Trigger:** Run agent after each new transcript segment (or every N seconds) so it can interrupt with a question or closing.
  - **Output:**
    - **Continue:** One or more “questions” or statements to speak (text).
    - **End call:** Single final message to say, then you close the stream / hang up.

- **Implementation**
  - LLM (e.g. OpenAI chat API) with a system prompt that:
    - Defines the “information to extract”.
    - Returns structured output: e.g. `{ "action": "ask" | "end_call", "message": "...", "extracted": { ... } }`.
  - Optionally use a small schema (e.g. Pydantic) and force JSON so you can reliably parse “message” for TTS and “action” for flow control.

---

## 4. TTS (ElevenLabs) and Sending Back Over Twilio

- **Flow:**

  - Agent returns **text** → call ElevenLabs TTS (streaming or one-shot).
  - Get audio (e.g. MP3 or PCM).
  - **Convert to 8kHz mulaw** (resample + linear PCM → mulaw), then base64.
  - Send chunks to Twilio over the **same** WebSocket using the `media` message format above.

- **ElevenLabs**

  - Use streaming endpoint if you want to start playing before the full sentence is generated.
  - Output: e.g. MP3 or PCM; you’ll resample and encode to 8kHz mulaw in your service (Python `audioop` + resampling is a proven path; avoid incorrect mulaw helpers that produce bad audio).

- **Ordering / timing**
  - Send media frames in order; optionally respect Twilio’s timing (e.g. 20ms per chunk) so playback is smooth.
  - Don’t close the WebSocket until you’ve sent all TTS for the current reply (and optionally a short silence), so the user hears the full phrase.

---

## 5. End Call

- **Bidirectional stream:** When your WebSocket server **closes** the connection, Twilio ends the stream. What happens next to the call is defined by the TwiML you returned (e.g. if the only instruction was `<Connect><Stream>`, the call typically ends when the stream ends).
- If you want an explicit hangup: use Twilio REST **Update Call** or **Delete Call** with the `CallSid` from the `start` message.

---

## 6. Suggested Components (No Code Yet)

| Component                                                 | Responsibility                                                                                                                                    |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Voice webhook** (`POST /twilio/webhooks/voice`)         | Validate Twilio request, return TwiML with `<Connect><Stream url="wss://...">` (+ optional `<Parameter>`s).                                       |
| **WebSocket server** (e.g. `/ws/voice` or dedicated path) | Accept Twilio Media Stream connections; parse `start` / `media` / `stop`; hold per-call state.                                                    |
| **Audio pipeline (in)**                                   | Decode base64 mulaw → PCM, resample to 24kHz (or 16kHz); buffer and send to Whisper/Realtime.                                                     |
| **Transcription**                                         | Call OpenAI Realtime (WebSocket) or Whisper (HTTP) per chunk; output transcript segments.                                                         |
| **Conversation agent**                                    | Input: transcript + state. Output: `ask` + message or `end_call` + message; optionally persist `extracted` to DB.                                 |
| **TTS pipeline**                                          | Text → ElevenLabs → audio → resample + mulaw encode → base64 → send `media` messages on WebSocket.                                                |
| **Call state store**                                      | In-memory (e.g. dict by `streamSid`) or Redis for transcript, extracted data, and agent turn history (needed if you scale to multiple instances). |

---

## 7. Environment / Config

- **Twilio:** Already have SID, token, number; add a **Twilio Voice** number (or use same number if it supports voice) and point its “A call comes in” webhook to `https://your-api/twilio/webhooks/voice`.
- **OpenAI:** API key for Realtime and/or Whisper.
- **ElevenLabs:** API key; choose a **voice_id** for the agent.
- **Optional:** Redis (or similar) for shared call state if you run more than one API instance.

---

## 8. Deployment / Infra Notes

- **WebSocket URL:** Your ECS service must be reachable on **WSS** (e.g. same host as API or a path like `wss://api.example.com/ws/voice`).
- **ALB:** Enable WebSocket support on the target group / listener.
- **Timeouts:** Increase ALB idle timeout (e.g. 600s) so long calls don’t get cut.
- **Logging:** Log `CallSid`, `streamSid`, and high-level events (stream start/stop, agent decisions, errors) for debugging.

---

## 9. Optional: Persistence and UI

- **DB:** Store call summary when the stream ends: `CallSid`, `From`, `To`, started/ended time, final transcript or summary, **extracted** fields from the agent.
- **UI:** Reuse existing patterns; e.g. a “calls” view that lists calls and shows extracted info, similar to how you handle SMS.

---

## 10. Order of Implementation (Suggested)

1. **Voice webhook** – Return TwiML that uses `<Connect><Stream>` to a test WSS URL; confirm the call connects and stays up.
2. **WebSocket server** – Accept Twilio, log `start`/`media`/`stop`; no transcription yet.
3. **Inbound audio pipeline** – Mulaw decode + resample; send to Whisper (chunked) or Realtime; log transcript.
4. **Conversation agent** – Input transcript + state; output ask/end + message (no TTS yet).
5. **TTS + outbound audio** – ElevenLabs → 8kHz mulaw → WebSocket `media`; then wire agent message → TTS → send.
6. **End-call flow** – Agent says “end call” → send final TTS → close WebSocket (and optionally REST hangup).
7. **Persistence and cleanup** – Save call + extracted data; optional statusCallback; tune timeouts and errors.
