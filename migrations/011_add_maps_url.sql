-- Add Google Maps URL columns to tables with coordinates

-- Add to event table
ALTER TABLE event
ADD COLUMN IF NOT EXISTS maps_url TEXT GENERATED ALWAYS AS (
    CASE
        WHEN latitude IS NOT NULL AND longitude IS NOT NULL
        THEN 'https://www.google.com/maps?q=' || latitude || ',' || longitude
        ELSE NULL
    END
) STORED;

-- Add to text_message table
ALTER TABLE text_message
ADD COLUMN IF NOT EXISTS maps_url TEXT GENERATED ALWAYS AS (
    CASE
        WHEN latitude IS NOT NULL AND longitude IS NOT NULL
        THEN 'https://www.google.com/maps?q=' || latitude || ',' || longitude
        ELSE NULL
    END
) STORED;

-- Add to user table
ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS maps_url TEXT GENERATED ALWAYS AS (
    CASE
        WHEN latitude IS NOT NULL AND longitude IS NOT NULL
        THEN 'https://www.google.com/maps?q=' || latitude || ',' || longitude
        ELSE NULL
    END
) STORED;

-- Add comments
COMMENT ON COLUMN event.maps_url IS 'Direct Google Maps link for the event location';
COMMENT ON COLUMN text_message.maps_url IS 'Direct Google Maps link for the message origin location';
COMMENT ON COLUMN "user".maps_url IS 'Direct Google Maps link for the user location';