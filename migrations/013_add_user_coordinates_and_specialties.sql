-- Add coordinate columns to user table for proximity matching
ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS last_location_update TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

-- Add maps URL for users
ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS maps_url TEXT GENERATED ALWAYS AS (
    CASE
        WHEN latitude IS NOT NULL AND longitude IS NOT NULL
        THEN 'https://www.google.com/maps?q=' || latitude || ',' || longitude
        ELSE NULL
    END
) STORED;

-- Create junction table for user specialties
CREATE TABLE IF NOT EXISTS user_specialty (
    user_id UUID REFERENCES "user"(id) ON DELETE CASCADE,
    specialty_id UUID REFERENCES specialty(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, specialty_id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create spatial index for proximity queries on users
CREATE INDEX IF NOT EXISTS idx_user_location ON "user"(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_user_role ON "user"(role);
CREATE INDEX IF NOT EXISTS idx_user_status ON "user"(status);

-- Add some default specialties if they don't exist
INSERT INTO specialty (name, description) VALUES
    ('Doctor', 'Medical doctor with emergency response training'),
    ('Nurse', 'Registered nurse with emergency care experience'),
    ('EMT', 'Emergency Medical Technician'),
    ('Firefighter', 'Trained firefighter and first responder'),
    ('Police', 'Law enforcement officer'),
    ('Search & Rescue', 'Trained in search and rescue operations'),
    ('Mental Health', 'Mental health professional/counselor'),
    ('Mechanic', 'Auto mechanic who can help with vehicle issues'),
    ('Electrician', 'Licensed electrician for power issues'),
    ('Translator', 'Multi-lingual translator for communication')
ON CONFLICT DO NOTHING;

-- Add comments
COMMENT ON COLUMN "user".latitude IS 'Current latitude coordinate of the user';
COMMENT ON COLUMN "user".longitude IS 'Current longitude coordinate of the user';
COMMENT ON COLUMN "user".last_location_update IS 'When the user location was last updated';
COMMENT ON COLUMN "user".maps_url IS 'Direct Google Maps link for the user location';
COMMENT ON TABLE user_specialty IS 'Junction table linking users to their specialties/skills';