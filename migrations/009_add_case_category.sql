-- Add category field to case table for emergency type classification
ALTER TABLE "case"
ADD COLUMN IF NOT EXISTS category TEXT;

-- Add coordinates to user table for location-based matching
ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

-- Add user_id to text_message for sender identification
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'text_message' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE text_message
        ADD COLUMN user_id UUID REFERENCES "user"(id);
    END IF;
END $$;

-- Create index on case category for faster filtering
CREATE INDEX IF NOT EXISTS idx_case_category ON "case"(category);

-- Create spatial index on user location for proximity queries
CREATE INDEX IF NOT EXISTS idx_user_location ON "user"(latitude, longitude);