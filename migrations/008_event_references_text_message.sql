-- Event can optionally reference a source text message.
-- Idempotent: safe to run if column already exists.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'event' AND column_name = 'text_message_id'
  ) THEN
    ALTER TABLE event
    ADD COLUMN text_message_id UUID REFERENCES text_message(id) ON DELETE SET NULL;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_event_text_message_id ON event(text_message_id);
