-- Event (Log): "Black Box" for AI semantic search and auditing.
-- Embedding: 1536 dimensions (OpenAI text-embedding-3-small / ada-002).
-- Idempotent: safe to run if extension/table already exist.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS event (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
  "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now(),
  description TEXT NOT NULL,
  embedding vector(1536)
);

CREATE INDEX IF NOT EXISTS idx_event_case_id ON event(case_id);
CREATE INDEX IF NOT EXISTS idx_event_timestamp ON event("timestamp");
-- Optional: HNSW index for fast approximate nearest-neighbor search on embeddings
CREATE INDEX IF NOT EXISTS idx_event_embedding ON event
  USING hnsw (embedding vector_cosine_ops);
