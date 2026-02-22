-- RPC: closest users WITH specialties by combined geographical + semantic distance (equally weighted).
-- Inner join so only users that have at least one row in ethan_user_speciality.
-- Excludes users who are assigned to any case (in responder_assignment).
-- Call via Supabase: supabase.rpc('search_users_by_embedding_and_location', { query_embedding: [...], lat: 59.33, lng: 18.06, match_count: 10 })

CREATE OR REPLACE FUNCTION search_users_by_embedding_and_location(
  query_embedding vector(1536),
  lat double precision,
  lng double precision,
  match_count int DEFAULT 10
)
RETURNS SETOF "user"
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
        + 0.5 * (s.sem_dist / 2.0) AS combined
    FROM "user" u
    INNER JOIN user_semantic s ON s.user_id = u.id
    WHERE u.latitude IS NOT NULL AND u.longitude IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM responder_assignment ra WHERE ra.responder_id = u.id)
  )
  SELECT u.*
  FROM "user" u
  INNER JOIN scored sc ON sc.id = u.id
  ORDER BY sc.combined ASC   /* best match first (lowest combined distance) */
  LIMIT match_count;
$$;
