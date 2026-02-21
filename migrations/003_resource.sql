-- Resource: temporary hospital, gas station, etc.
-- Idempotent: safe to run if table already exists.

CREATE TABLE IF NOT EXISTS resource (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  location VARCHAR(255)
);
