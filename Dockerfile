# Build and run the FastAPI app for ECS Fargate.
# Expects PORT env (default 8000); SUPABASE_* are injected by ECS at runtime.
# Build with: docker build --platform linux/amd64 ... (required for ECS on Apple Silicon).

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY api/ ./api/

# Run from api/ so "from env import ..." in index.py resolves to api/env.py
WORKDIR /app/api

# No .env in image; ECS supplies SUPABASE_POSTGRES_URL, SUPABASE_URL, PORT
EXPOSE 8000

CMD ["sh", "-c", "uvicorn index:app --host 0.0.0.0 --port ${PORT:-8000}"]
