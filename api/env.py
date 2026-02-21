"""Load and validate required environment variables from project root .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root is parent of api/
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_POSTGRES_URL = os.environ.get("SUPABASE_POSTGRES_URL")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is required; set it in .env at project root")
if not SUPABASE_POSTGRES_URL:
    raise RuntimeError("SUPABASE_POSTGRES_URL is required; set it in .env at project root")
