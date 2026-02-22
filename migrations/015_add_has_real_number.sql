-- Add has_real_number column to track which users have real phone numbers vs test numbers
ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS has_real_number BOOLEAN DEFAULT false;

-- Add comment
COMMENT ON COLUMN "user".has_real_number IS 'TRUE if user has a real phone number for SMS, FALSE for test/dummy numbers';

-- Create index for finding users with real numbers
CREATE INDEX IF NOT EXISTS idx_user_has_real_number ON "user"(has_real_number) WHERE has_real_number = true;