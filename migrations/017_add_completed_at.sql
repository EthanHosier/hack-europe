-- Add nullable completed_at timestamp to case table
ALTER TABLE "case"
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
