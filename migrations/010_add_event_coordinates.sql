-- Add coordinate columns to event table for location tracking
ALTER TABLE event
ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

-- Create spatial index for proximity queries
CREATE INDEX IF NOT EXISTS idx_event_location ON event(latitude, longitude);

-- Add comment
COMMENT ON COLUMN event.latitude IS 'Latitude coordinate of the event location';
COMMENT ON COLUMN event.longitude IS 'Longitude coordinate of the event location';