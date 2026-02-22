-- Add P2P flag and AI analysis fields to case table
ALTER TABLE "case"
  ADD COLUMN IF NOT EXISTS p2p BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS confidence INT,
  ADD COLUMN IF NOT EXISTS required_capability TEXT,
  ADD COLUMN IF NOT EXISTS parsed_need_type TEXT,
  ADD COLUMN IF NOT EXISTS recommended_action TEXT;
