-- User table: ID, Name, Phone, Role, Status, location
-- Role: Victim, Responder, Admin. Status: Safe, Active, Injured.
-- Idempotent: safe to run if types/table already exist (e.g. from a previous Alembic run).

DO $$ BEGIN
  CREATE TYPE user_role AS ENUM ('Victim', 'Responder', 'Admin');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE user_status AS ENUM ('Safe', 'Active', 'Injured');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS "user" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  phone VARCHAR(64),
  role user_role NOT NULL,
  status user_status NOT NULL,
  location VARCHAR(255)
);
