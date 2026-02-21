"""Load and validate required environment variables from project root .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root is parent of api/
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_POSTGRES_URL = os.environ.get("SUPABASE_POSTGRES_URL")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")
WORKFLOW_WEBHOOK_URL = os.environ.get("WORKFLOW_WEBHOOK_URL")
# Optional: WSS URL for Twilio Media Stream (voice calls). If set, incoming calls are connected to this stream.
VOICE_STREAM_WS_URL = os.environ.get("VOICE_STREAM_WS_URL")
# Optional: Google APIs (Gemini, Maps). CI may run without them (e.g. OpenAPI export).
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
# Optional: OpenAI API key for voice transcription (Whisper).
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# Optional: ElevenLabs API key for TTS (voice reply on calls).
ELEVEN_LABS_API_KEY = os.environ.get("ELEVEN_LABS_API_KEY")
if GOOGLE_API_KEY is not None:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is required; set it in .env at project root")
if not SUPABASE_POSTGRES_URL:
    raise RuntimeError("SUPABASE_POSTGRES_URL is required; set it in .env at project root")
if not TWILIO_ACCOUNT_SID:
    raise RuntimeError("TWILIO_ACCOUNT_SID is required; set it in .env at project root")
if not TWILIO_AUTH_TOKEN:
    raise RuntimeError("TWILIO_AUTH_TOKEN is required; set it in .env at project root")
if not TWILIO_FROM_NUMBER:
    raise RuntimeError("TWILIO_FROM_NUMBER is required; set it in .env at project root")
if not WORKFLOW_WEBHOOK_URL:
    raise RuntimeError("WORKFLOW_WEBHOOK_URL is required; set it in .env at project root")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required; set it in .env at project root")
if not ELEVEN_LABS_API_KEY:
    raise RuntimeError("ELEVEN_LABS_API_KEY is required; set it in .env at project root")