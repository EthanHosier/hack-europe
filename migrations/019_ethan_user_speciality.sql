-- ethan_user_speciality: user speciality text and its embedding for semantic matching.
-- Embedding: 1536 dimensions (OpenAI text-embedding-3-small / ada-002).
-- Idempotent: safe to run if extension/table already exist.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS ethan_user_speciality (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  speciality TEXT NOT NULL,
  embedding vector(1536)
);

CREATE INDEX IF NOT EXISTS idx_ethan_user_speciality_user_id ON ethan_user_speciality(user_id);
CREATE INDEX IF NOT EXISTS idx_ethan_user_speciality_embedding ON ethan_user_speciality
  USING hnsw (embedding vector_cosine_ops);
