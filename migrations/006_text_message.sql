-- Text Message: source (WhatsApp, SMS), raw text, sentiment, geo-coords.
-- Idempotent: safe to run if types/table already exist.

DO $$ BEGIN
  CREATE TYPE message_source AS ENUM ('WhatsApp', 'SMS');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS text_message (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source message_source NOT NULL,
  target VARCHAR(64) NOT NULL,
  raw_text TEXT NOT NULL,
  sentiment DOUBLE PRECISION,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_text_message_target ON text_message(target);
CREATE INDEX IF NOT EXISTS idx_text_message_created_at ON text_message(created_at);
