"""ElevenLabs text-to-speech: call the voice generation API and return μ-law 8kHz audio for Twilio."""

import logging
from typing import Optional

import env

logger = logging.getLogger("uvicorn.error")

# Model: eleven_multilingual_v2 is the default; set ELEVEN_LABS_MODEL_ID=eleven_v3 for v3 if available
_DEFAULT_MODEL_ID = "eleven_multilingual_v2"
# Default voice (Rachel); override with ELEVEN_LABS_VOICE_ID env if set
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
# Twilio expects μ-law 8kHz; ElevenLabs can return it directly
OUTPUT_FORMAT = "ulaw_8000"
ELEVEN_TTS_URL_TEMPLATE = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def text_to_speech(text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
    """
    Generate speech from text using ElevenLabs API.
    Returns raw μ-law 8kHz audio bytes suitable for Twilio Media Stream, or None on error.
    """
    if not text or not text.strip():
        return None
    api_key = getattr(env, "ELEVEN_LABS_API_KEY", None) or ""
    if not api_key:
        logger.warning("elevenlabs_skip ELEVEN_LABS_API_KEY not set")
        return None
    vid = voice_id or getattr(env, "ELEVEN_LABS_VOICE_ID", None) or DEFAULT_VOICE_ID
    model_id = getattr(env, "ELEVEN_LABS_MODEL_ID", None) or _DEFAULT_MODEL_ID
    url = ELEVEN_TTS_URL_TEMPLATE.format(voice_id=vid)
    url = f"{url}?output_format={OUTPUT_FORMAT}"
    headers = {
        "Accept": "audio/*",
        "Content-Type": "application/json",
        "xi-api-key": api_key,
    }
    payload = {"text": text.strip(), "model_id": model_id}
    try:
        import json as _json
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            url,
            data=_json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.fp.read().decode("utf-8", errors="replace") if e.fp else ""
        logger.error(
            "elevenlabs_tts_error status=%s body=%s",
            e.code,
            body[:500] if body else "(none)",
        )
        return None
    except Exception:
        logger.exception("elevenlabs_tts_error")
        return None
