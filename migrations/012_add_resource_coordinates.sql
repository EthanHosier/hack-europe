-- Add coordinate columns and maps URL to resource table

-- Add latitude and longitude
ALTER TABLE resource
ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

-- Add auto-generated Google Maps URL
ALTER TABLE resource
ADD COLUMN IF NOT EXISTS maps_url TEXT GENERATED ALWAYS AS (
    CASE
        WHEN latitude IS NOT NULL AND longitude IS NOT NULL
        THEN 'https://www.google.com/maps?q=' || latitude || ',' || longitude
        ELSE NULL
    END
) STORED;

-- Add status column for tracking if resource is available
ALTER TABLE resource
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Available';

-- Add capacity info
ALTER TABLE resource
ADD COLUMN IF NOT EXISTS capacity INTEGER;

-- Add created_at timestamp
ALTER TABLE resource
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

-- Create spatial index for proximity queries
CREATE INDEX IF NOT EXISTS idx_resource_location ON resource(latitude, longitude);

-- Add comments
COMMENT ON COLUMN resource.latitude IS 'Latitude coordinate of the resource location';
COMMENT ON COLUMN resource.longitude IS 'Longitude coordinate of the resource location';
COMMENT ON COLUMN resource.maps_url IS 'Direct Google Maps link for the resource location';
COMMENT ON COLUMN resource.status IS 'Current status: Available, Full, Closed, Emergency Only';
COMMENT ON COLUMN resource.capacity IS 'Maximum capacity (e.g., beds for field hospital)';