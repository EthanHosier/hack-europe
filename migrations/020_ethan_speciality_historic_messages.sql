-- ethan_speciality_historic_messages: store inbound SMS for the speciality number.
-- Idempotent: safe to run if table already exist.

CREATE TABLE IF NOT EXISTS ethan_speciality_historic_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_from VARCHAR(64) NOT NULL,
  text_content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ethan_speciality_historic_messages_phone_from ON ethan_speciality_historic_messages(phone_from);
CREATE INDEX IF NOT EXISTS idx_ethan_speciality_historic_messages_created_at ON ethan_speciality_historic_messages(created_at);
