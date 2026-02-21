-- Add SMS delivery metadata needed for Twilio in/out flows.
-- Idempotent: safe to run if columns/constraints already exist.

ALTER TABLE text_message
ADD COLUMN IF NOT EXISTS direction VARCHAR(16);

ALTER TABLE text_message
ADD COLUMN IF NOT EXISTS provider_message_sid VARCHAR(64);

ALTER TABLE text_message
ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(64);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'text_message_direction_check'
  ) THEN
    ALTER TABLE text_message
    ADD CONSTRAINT text_message_direction_check
    CHECK (direction IN ('Inbound', 'Outbound') OR direction IS NULL);
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_text_message_provider_message_sid
ON text_message(provider_message_sid)
WHERE provider_message_sid IS NOT NULL;
