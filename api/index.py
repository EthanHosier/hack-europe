import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from env import SUPABASE_POSTGRES_URL

app = FastAPI(title="HackEurope API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RootResponse(BaseModel):
    Python: str
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str


class DbHealthResponse(BaseModel):
    connected: bool


@app.get("/", response_model=RootResponse)
def read_root() -> RootResponse:
    return RootResponse(Python="on Vercel", message="Hello from FastAPI")


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/db/health", response_model=DbHealthResponse)
def db_health() -> DbHealthResponse:
    """Check connection to the database."""
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return DbHealthResponse(connected=True)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
