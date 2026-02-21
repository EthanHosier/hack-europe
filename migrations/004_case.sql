-- Case (Incident): Severity 1-5, Status Open/In Progress/Resolved.
-- candidates and assigned_helpers via junction tables to "user".
-- Idempotent: safe to run if types/tables already exist.

DO $$ BEGIN
  CREATE TYPE case_status AS ENUM ('Open', 'In Progress', 'Resolved');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS "case" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(255) NOT NULL,
  severity SMALLINT NOT NULL CHECK (severity >= 1 AND severity <= 5),
  status case_status NOT NULL DEFAULT 'Open',
  summary TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Junction: case candidates (Person[] -> users)
CREATE TABLE IF NOT EXISTS case_candidates (
  case_id UUID NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  PRIMARY KEY (case_id, user_id)
);

-- Junction: assigned helpers (Person[] -> users)
CREATE TABLE IF NOT EXISTS case_assigned_helpers (
  case_id UUID NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  PRIMARY KEY (case_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_case_candidates_case_id ON case_candidates(case_id);
CREATE INDEX IF NOT EXISTS idx_case_candidates_user_id ON case_candidates(user_id);
CREATE INDEX IF NOT EXISTS idx_case_assigned_helpers_case_id ON case_assigned_helpers(case_id);
CREATE INDEX IF NOT EXISTS idx_case_assigned_helpers_user_id ON case_assigned_helpers(user_id);
