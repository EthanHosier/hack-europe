-- RPC: similarity search over event embeddings (cosine distance).
-- Call via Supabase: supabase.rpc('search_similar_events', { query_embedding: [...], match_count: 10 })

CREATE OR REPLACE FUNCTION search_similar_events(
  query_embedding vector(1536),
  match_count int DEFAULT 10
)
RETURNS SETOF event
LANGUAGE sql
STABLE
AS $$
  SELECT *
  FROM event
  WHERE embedding IS NOT NULL
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;
