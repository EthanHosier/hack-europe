-- Add nullable stress_level field to case table
DO $$ BEGIN
  CREATE TYPE stress_level AS ENUM ('Low', 'Medium', 'High');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE "case"
  ADD COLUMN IF NOT EXISTS stress_level stress_level;
