from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from twilio.base.exceptions import TwilioRestException

from env import SUPABASE_POSTGRES_URL
from twilio_service import TwilioConfigError, send_sms, validate_twilio_signature
from workflow_bridge import build_inbound_event, handle_inbound_message

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


class SendSmsRequest(BaseModel):
    to: str
    body: str
    context: dict[str, Any] | None = None


class SendSmsResponse(BaseModel):
    success: bool
    message_sid: str | None = None
    status: str | None = None
    to: str
    from_number: str | None = None
    error: str | None = None
    workflow: str | None = None
    persistence_error: str | None = None


def persist_text_message(
    *,
    target: str,
    raw_text: str,
    direction: str,
    provider_message_sid: str | None = None,
    delivery_status: str | None = None,
) -> str:
    with psycopg.connect(SUPABASE_POSTGRES_URL) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO text_message (
                        source, target, raw_text, direction, provider_message_sid, delivery_status
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        "SMS",
                        target,
                        raw_text,
                        direction,
                        provider_message_sid,
                        delivery_status,
                    ),
                )
                inserted_id = cur.fetchone()[0]
            except psycopg.errors.UndefinedColumn:
                # Backward compatibility if migrations were not applied yet.
                cur.execute(
                    """
                    INSERT INTO text_message (source, target, raw_text)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    ("SMS", target, raw_text),
                )
                inserted_id = cur.fetchone()[0]
    return str(inserted_id)


def persist_event(
    *,
    case_id: str,
    description: str,
    text_message_id: str | None = None,
) -> None:
    with psycopg.connect(SUPABASE_POSTGRES_URL) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO event (case_id, description, text_message_id)
                    VALUES (%s, %s, %s)
                    """,
                    (case_id, description, text_message_id),
                )
            except psycopg.errors.UndefinedColumn:
                cur.execute(
                    """
                    INSERT INTO event (case_id, description)
                    VALUES (%s, %s)
                    """,
                    (case_id, description),
                )


@app.get("/", response_model=RootResponse)
def read_root() -> RootResponse:
    return RootResponse(Python="on Vercel", message="Hello from FastAPI!")


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


@app.post("/twilio/webhooks/sms")
async def twilio_sms_webhook(request: Request) -> Response:
    form = await request.form()
    payload = {k: str(v) for k, v in form.items()}

    signature = request.headers.get("X-Twilio-Signature")
    if not validate_twilio_signature(str(request.url), payload, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    from_number = payload.get("From", "").strip()
    to_number = payload.get("To", "").strip()
    body = payload.get("Body", "").strip()
    message_sid = payload.get("MessageSid")

    if not from_number or not to_number or not body:
        raise HTTPException(status_code=400, detail="Missing Twilio message fields")

    message_row_id = persist_text_message(
        target=from_number,
        raw_text=body,
        direction="Inbound",
        provider_message_sid=message_sid,
        delivery_status="received",
    )

    inbound_event = build_inbound_event(
        from_number=from_number,
        to_number=to_number,
        body=body,
        provider_message_sid=message_sid,
        raw_payload=payload,
    )
    handle_inbound_message(inbound_event)

    case_id = payload.get("CaseId")
    if case_id:
        persist_event(
            case_id=case_id,
            description=f"Inbound SMS received from {from_number}: {body}",
            text_message_id=message_row_id,
        )

    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
        status_code=200,
    )


@app.post("/messages/send", response_model=SendSmsResponse)
def send_message(payload: SendSmsRequest) -> SendSmsResponse:
    try:
        result = send_sms(payload.to, payload.body)
    except TwilioConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except TwilioRestException as e:
        raise HTTPException(status_code=502, detail=f"Twilio send failed: {e.msg}")

    persistence_error: str | None = None
    try:
        message_row_id = persist_text_message(
            target=result.to_number,
            raw_text=payload.body,
            direction="Outbound",
            provider_message_sid=result.message_sid,
            delivery_status=result.status,
        )
        case_id = payload.context.get("case_id") if payload.context else None
        if case_id:
            persist_event(
                case_id=case_id,
                description=f"Outbound SMS sent to {result.to_number}: {payload.body}",
                text_message_id=message_row_id,
            )
    except Exception as e:
        persistence_error = str(e)

    return SendSmsResponse(
        success=True,
        message_sid=result.message_sid,
        status=result.status,
        to=result.to_number,
        from_number=result.from_number,
        workflow="queued_for_delivery",
        persistence_error=persistence_error,
    )
