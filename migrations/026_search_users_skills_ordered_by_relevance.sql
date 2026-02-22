-- RPC: order each user's skills by relevance to the query (semantic distance to query_embedding).

DROP FUNCTION IF EXISTS search_users_by_embedding_and_location(vector(1536), double precision, double precision, integer, uuid);

CREATE OR REPLACE FUNCTION search_users_by_embedding_and_location(
  query_embedding vector(1536),
  lat double precision,
  lng double precision,
  match_count int DEFAULT 10,
  p_case_id UUID DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  name VARCHAR(255),
  phone VARCHAR(64),
  role user_role,
  status user_status,
  location VARCHAR(255),
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  last_location_update TIMESTAMPTZ,
  created_at TIMESTAMPTZ,
  maps_url TEXT,
  notified_for_case boolean,
  skills TEXT[],
  distance_km DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
  WITH user_semantic AS (
    SELECT e.user_id, MIN(e.embedding <=> query_embedding) AS sem_dist
    FROM ethan_user_speciality e
    WHERE e.embedding IS NOT NULL
    GROUP BY e.user_id
  ),
  scored AS (
    SELECT
      u.id,
      0.5 * (SQRT(POWER(u.latitude - lat, 2) + POWER(u.longitude - lng, 2)) * 111.0 / 100.0)
        + 0.5 * (s.sem_dist / 2.0) AS combined,
      SQRT(POWER(u.latitude - lat, 2) + POWER(u.longitude - lng, 2)) * 111.0 AS distance_km
    FROM "user" u
    INNER JOIN user_semantic s ON s.user_id = u.id
    WHERE u.latitude IS NOT NULL AND u.longitude IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM responder_assignment ra WHERE ra.responder_id = u.id AND ra.status = 'accepted')
  )
  SELECT
    u.id,
    u.name,
    u.phone,
    u.role,
    u.status,
    u.location,
    u.latitude,
    u.longitude,
    u.last_location_update,
    u.created_at,
    u.maps_url,
    (p_case_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM responder_assignment ra
      WHERE ra.responder_id = u.id AND ra.case_id = p_case_id
    )) AS notified_for_case,
    (SELECT array_agg(e.speciality ORDER BY (e.embedding <=> query_embedding) NULLS LAST)
     FROM ethan_user_speciality e WHERE e.user_id = u.id) AS skills,
    sc.distance_km
  FROM "user" u
  INNER JOIN scored sc ON sc.id = u.id
  ORDER BY sc.combined ASC
  LIMIT match_count;
$$;
