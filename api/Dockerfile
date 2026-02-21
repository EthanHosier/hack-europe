# Build and run the FastAPI app for ECS Fargate.
# Expects PORT env (default 8000); SUPABASE_*, TWILIO_* etc. injected by ECS at runtime.
# Build from repo root: docker build --platform linux/amd64 -f api/Dockerfile -t <image> api/

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (build context is api/)
COPY . .

# No .env in image; ECS supplies env vars
EXPOSE 8000

CMD ["sh", "-c", "uvicorn index:app --host 0.0.0.0 --port ${PORT:-8000}"]
