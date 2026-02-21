-- Specialty: skills like EMT, Alpine Guide, Mechanic, etc.
-- Idempotent: safe to run if table already exists.

CREATE TABLE IF NOT EXISTS specialty (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT
);
