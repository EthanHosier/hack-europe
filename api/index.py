"""
HackEurope API: health, SMS/voice webhooks, messages.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Header, HTTPException, Query, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from twilio.base.exceptions import TwilioRestException

from env import SUPABASE_POSTGRES_URL, VOICE_STREAM_WS_URL
from workflow_bridge import build_inbound_event, handle_inbound_message
from db import persist_event, persist_text_message
from twilio_app import (
    TwilioConfigError,
    build_connect_stream_twiml,
    build_say_hangup_twiml,
    handle_voice_media_stream,
    send_sms,
)
from agent import EmergencyAgent, EmergencyInfo

app = FastAPI(title="HackEurope API")
webhook_logger = logging.getLogger("uvicorn.error")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Response models ---


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


# --- Health & debug ---


# Emergency Response Models
class UserRegister(BaseModel):
    name: str
    phone: str
    role: Literal["Victim", "Responder", "Admin"]
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class UserResponse(BaseModel):
    id: str
    name: str
    phone: str
    role: str
    status: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class MessageCreate(BaseModel):
    text: str
    case_id: Optional[str] = None
    is_emergency: bool = False


class MessageResponse(BaseModel):
    id: str
    text: str
    case_id: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    created_at: datetime
    is_emergency: bool = False


class EmergencyRequest(BaseModel):
    message: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CaseResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    severity: int
    status: str
    category: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    maps_url: Optional[str] = None


class RespondToCaseRequest(BaseModel):
    message: Optional[str] = "I can help with this emergency"


# AI Chat Models
class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    case_id: Optional[str] = None
    extracted_info: Optional[Dict] = None


# Resource Models
class ResourceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    maps_url: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[str] = None
    distance_km: Optional[float] = None


class LiveEventResponse(BaseModel):
    event_id: str
    case_id: str
    description: str
    latitude: float
    longitude: float
    timestamp: datetime
    case_severity: int
    case_status: str
    case_category: Optional[str] = None
    case_title: Optional[str] = None


# Emergency categorization patterns
EMERGENCY_PATTERNS = {
    "fuel": [
        "out of fuel",
        "gas",
        "petrol",
        "diesel",
        "empty tank",
        "stranded",
        "car stuck",
    ],
    "medical": [
        "injured",
        "hurt",
        "sick",
        "bleeding",
        "heart",
        "breathing",
        "pain",
        "emergency",
    ],
    "shelter": [
        "cold",
        "freezing",
        "shelter",
        "homeless",
        "nowhere to go",
        "stuck",
        "stranded",
    ],
    "food_water": ["hungry", "thirsty", "food", "water", "starving", "dehydrated"],
    "rescue": [
        "trapped",
        "stuck",
        "help me",
        "save",
        "emergency",
        "lost",
        "can't get out",
    ],
}


def categorize_emergency(text: str) -> Tuple[str, int]:
    """Categorize emergency message and determine severity."""
    text_lower = text.lower()

    # Check for category keywords
    category = "other"
    for cat, keywords in EMERGENCY_PATTERNS.items():
        if any(kw in text_lower for kw in keywords):
            category = cat
            break

    # Estimate severity (1-5 scale)
    severity = 3  # default medium
    if any(
        word in text_lower
        for word in ["urgent", "critical", "dying", "immediate", "emergency"]
    ):
        severity = 5
    elif any(word in text_lower for word in ["help", "please", "need", "quickly"]):
        severity = 4
    elif any(word in text_lower for word in ["minor", "small", "little"]):
        severity = 2

    return category, severity


@app.get("/", response_model=RootResponse)
def read_root() -> RootResponse:
    return RootResponse(Python="on Vercel", message="Hello from FastAPI!")


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/debug/routes")
def debug_routes() -> dict[str, list[str]]:
    """Registered routes (path -> methods). Remove in production if desired."""
    routes: dict[str, list[str]] = {}
    for r in app.routes:
        path = getattr(r, "path", None)
        if not path or path == "/debug/routes":
            continue
        methods = getattr(r, "methods", None)
        if methods is not None:
            routes[path] = sorted(methods) if isinstance(methods, set) else list(methods)
        else:
            routes[path] = ["WS"]
    return routes


@app.get("/db/health", response_model=DbHealthResponse)
def db_health() -> DbHealthResponse:
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return DbHealthResponse(connected=True)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# --- Twilio SMS webhook ---


@app.post("/twilio/webhooks/sms")
async def twilio_sms_webhook(request: Request) -> Response:
    payload: dict[str, str] = {}
    try:
        form = await request.form()
        payload = {k: str(v) for k, v in form.items()}
        webhook_logger.info(
            "twilio_sms_inbound_received method=%s url=%s payload=%s",
            request.method,
            str(request.url),
            json.dumps(payload, ensure_ascii=False),
        )

        from_number = payload.get("From", "").strip()
        to_number = payload.get("To", "").strip()
        body = payload.get("Body", "").strip()
        message_sid = payload.get("MessageSid")

        if not from_number or not to_number or not body:
            webhook_logger.warning("twilio_sms_inbound_missing_fields payload=%s", json.dumps(payload, ensure_ascii=False))
            raise HTTPException(status_code=400, detail="Missing Twilio message fields")

        message_row_id = persist_text_message(
            target=from_number,
            raw_text=body,
            direction="Inbound",
            provider_message_sid=message_sid,
            delivery_status="received",
        )
        webhook_logger.info(
            "twilio_sms_inbound_persisted message_row_id=%s message_sid=%s from=%s to=%s",
            message_row_id,
            message_sid,
            from_number,
            to_number,
        )

        # Get conversation history for this phone number
        conversation_history = []
        try:
            with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT raw_text, direction, created_at
                        FROM text_message
                        WHERE target = %s
                        AND created_at < (SELECT created_at FROM text_message WHERE id = %s)
                        ORDER BY created_at DESC
                        LIMIT 10
                        """,
                        (from_number, message_row_id),
                    )
                    messages = cur.fetchall()
                    for msg in reversed(messages):
                        if msg["direction"] == "Inbound":
                            conversation_history.append({"role": "user", "content": msg["raw_text"]})
                        else:
                            conversation_history.append({"role": "assistant", "content": msg["raw_text"]})
        except Exception as e:
            webhook_logger.error("Failed to get conversation history: %s", e)

        # Process message through the AI agent
        try:
            agent = EmergencyAgent(SUPABASE_POSTGRES_URL)
            user_id = str(uuid.uuid4())
            response_text, case_id, info = agent.process_message(
                body, conversation_history, user_id, SUPABASE_POSTGRES_URL
            )
        except Exception as e:
            webhook_logger.exception("agent.process_message failed: %s", e)
            response_text = "Sorry, we're unable to process your message right now."

        # Limit SMS response to 1600 characters (SMS limit)
        if len(response_text) > 1600:
            response_text = response_text[:1597] + "..."

        # Send SMS response
        try:
            sms_result = send_sms(from_number, response_text)
            persist_text_message(
                target=from_number,
                raw_text=response_text,
                direction="Outbound",
                provider_message_sid=sms_result.message_sid,
                delivery_status=sms_result.status,
            )
            webhook_logger.info(
                "twilio_sms_response_sent message_sid=%s to_number=%s response_length=%s",
                sms_result.message_sid,
                from_number,
                len(response_text),
            )
        except Exception as e:
            webhook_logger.error("Failed to send SMS response: %s", e)
            try:
                persist_text_message(
                    target=from_number,
                    raw_text=response_text,
                    direction="Outbound",
                    provider_message_sid=None,
                    delivery_status="failed",
                )
            except Exception:
                pass

        # Log case creation if applicable
        if case_id:
            persist_event(
                case_id=case_id,
                description=f"SMS Emergency: {body[:200]}",
                text_message_id=message_row_id,
            )
            webhook_logger.info("twilio_sms_case_created case_id=%s from_number=%s", case_id, from_number)

        webhook_logger.info("twilio_sms_inbound_processed message_sid=%s", message_sid)
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
            status_code=200,
        )
    except HTTPException:
        raise
    except Exception:
        webhook_logger.exception("twilio_sms_inbound_failed payload=%s", json.dumps(payload, ensure_ascii=False))
        raise


# --- Twilio voice webhook & Media Stream WebSocket ---


@app.post("/twilio/webhooks/voice")
async def twilio_voice_webhook(request: Request) -> Response:
    """Answer call with TwiML: connect to Media Stream (if VOICE_STREAM_WS_URL set) or say and hang up."""
    payload: dict[str, str] = {}
    try:
        form = await request.form()
        payload = {k: str(v) for k, v in form.items()}
        call_sid = payload.get("CallSid", "").strip()
        from_number = payload.get("From", "").strip()
        to_number = payload.get("To", "").strip()

        webhook_logger.info("twilio_voice_inbound call_sid=%s from=%s to=%s", call_sid, from_number, to_number)

        if VOICE_STREAM_WS_URL:
            twiml = build_connect_stream_twiml(
                ws_url=VOICE_STREAM_WS_URL,
                call_sid=call_sid,
                from_number=from_number,
                to_number=to_number,
            )
            webhook_logger.info("twilio_voice_connect_stream call_sid=%s ws_url=%s", call_sid, VOICE_STREAM_WS_URL)
        else:
            twiml = build_say_hangup_twiml("The voice service is not configured. Goodbye.")
            webhook_logger.warning("twilio_voice_no_ws_url call_sid=%s returning say_hangup", call_sid)

        return Response(content=twiml, media_type="application/xml", status_code=200)
    except Exception:
        webhook_logger.exception("twilio_voice_webhook_failed payload=%s", json.dumps(payload, ensure_ascii=False))
        raise


@app.websocket("/ws/voice")
async def twilio_voice_websocket(websocket: WebSocket) -> None:
    """Twilio bidirectional Media Stream (audio in/out)."""
    await handle_voice_media_stream(websocket)


# --- Messages API ---


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
                description=f"Outbound SMS to {result.to_number}: {payload.body}",
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


# User Management Endpoints
@app.post("/users/register", response_model=UserResponse)
async def register_user(user: UserRegister) -> UserResponse:
    """Register a new user in the system."""
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                user_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO "user" (id, name, phone, role, status, location, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        user_id,
                        user.name,
                        user.phone,
                        user.role,
                        "Safe",
                        user.location,
                        user.latitude,
                        user.longitude,
                    ),
                )
                result = cur.fetchone()
                conn.commit()
                # Convert UUID to string
                result["id"] = str(result["id"])
                return UserResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/me", response_model=UserResponse)
async def get_current_user(user_id: str = Header(alias="X-User-Id")) -> UserResponse:
    """Get current user information."""
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM "user" WHERE id = %s', (user_id,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="User not found")
                # Convert UUID to string
                result["id"] = str(result["id"])
                return UserResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Emergency Request Endpoint
@app.post("/emergency", response_model=CaseResponse)
async def create_emergency(
    request: EmergencyRequest, user_id: str = Header(alias="X-User-Id")
) -> CaseResponse:
    """Create an emergency case from a request."""
    try:
        # Categorize the emergency
        category, severity = categorize_emergency(request.message)

        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                case_id = str(uuid.uuid4())
                now = datetime.utcnow()

                # Create the case with title
                title = f"{category.replace('_', ' ').title()} Emergency"
                cur.execute(
                    """
                    INSERT INTO "case" (id, title, summary, severity, status, category, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        case_id,
                        title,
                        request.message[:200],
                        severity,
                        "Open",
                        category,
                        now,
                        now,
                    ),
                )
                case_result = cur.fetchone()
                # Convert UUID to string
                case_result["id"] = str(case_result["id"])

                # Store the initial message
                message_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO text_message (id, source, target, raw_text, user_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (message_id, "SMS", "emergency", request.message, user_id, now),
                )

                # Create an event log entry
                event_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO event (id, case_id, timestamp, description)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        event_id,
                        case_id,
                        now,
                        f"Emergency case created: {category} - Severity {severity}",
                    ),
                )

                conn.commit()
                return CaseResponse(**case_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Messages Endpoints
@app.get("/messages/{case_id}", response_model=List[MessageResponse])
async def get_case_messages(case_id: str) -> List[MessageResponse]:
    """Get all messages for a specific case."""
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        e.id,
                        e.description as text,
                        e.case_id,
                        e.timestamp as created_at,
                        tm.user_id,
                        u.name as user_name
                    FROM event e
                    LEFT JOIN text_message tm ON tm.id = e.text_message_id
                    LEFT JOIN "user" u ON u.id = tm.user_id
                    WHERE e.case_id = %s
                    ORDER BY e.timestamp ASC
                    """,
                    (case_id,),
                )
                results = cur.fetchall()
                # Convert UUIDs to strings and prepare response
                messages = []
                for r in results:
                    r["id"] = str(r["id"])
                    if r.get("case_id"):
                        r["case_id"] = str(r["case_id"])
                    if r.get("user_id"):
                        r["user_id"] = str(r["user_id"])
                    messages.append(MessageResponse(**{**r, "is_emergency": False}))
                return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/messages", response_model=MessageResponse)
async def send_message(
    message: MessageCreate, user_id: str = Header(alias="X-User-Id")
) -> MessageResponse:
    """Send a message in a case conversation."""
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                message_id = str(uuid.uuid4())
                now = datetime.utcnow()

                # Store the message
                cur.execute(
                    """
                    INSERT INTO text_message (id, source, target, raw_text, user_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (message_id, "SMS", "chat", message.text, user_id, now),
                )
                msg_result = cur.fetchone()

                # If it's an emergency message, create a new case
                if message.is_emergency:
                    category, severity = categorize_emergency(message.text)
                    case_id = str(uuid.uuid4())
                    title = f"{category.replace('_', ' ').title()} Emergency"
                    cur.execute(
                        """
                        INSERT INTO "case" (id, title, summary, severity, status, category, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            case_id,
                            title,
                            message.text[:200],
                            severity,
                            "Open",
                            category,
                            now,
                            now,
                        ),
                    )
                    message.case_id = case_id

                # Log the event if associated with a case
                if message.case_id:
                    event_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO event (id, case_id, timestamp, description, text_message_id)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (event_id, message.case_id, now, message.text, message_id),
                    )

                # Get user name
                cur.execute('SELECT name FROM "user" WHERE id = %s', (user_id,))
                user = cur.fetchone()

                conn.commit()
                return MessageResponse(
                    id=message_id,
                    text=message.text,
                    case_id=message.case_id,
                    user_id=user_id,
                    user_name=user["name"] if user else None,
                    created_at=now,
                    is_emergency=message.is_emergency,
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Case Management Endpoints
@app.get("/cases", response_model=List[CaseResponse])
async def get_cases(
    role: Optional[str] = Query(None), user_id: str = Header(alias="X-User-Id")
) -> List[CaseResponse]:
    """Get cases based on user role."""
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                if role == "Responder":
                    # Show all open cases for responders with maps URL from latest event
                    cur.execute(
                        """
                        SELECT c.*, e.maps_url
                        FROM "case" c
                        LEFT JOIN LATERAL (
                            SELECT maps_url
                            FROM event
                            WHERE case_id = c.id AND maps_url IS NOT NULL
                            ORDER BY timestamp DESC
                            LIMIT 1
                        ) e ON TRUE
                        WHERE c.status IN ('Open', 'In Progress')
                        ORDER BY c.severity DESC, c.created_at DESC
                        """
                    )
                elif role == "Victim":
                    # Show cases created by or assigned to this user
                    cur.execute(
                        """
                        SELECT DISTINCT c.* FROM "case" c
                        LEFT JOIN case_assigned_helpers cah ON c.id = cah.case_id
                        WHERE cah.user_id = %s OR c.id IN (
                            SELECT case_id FROM event e
                            JOIN text_message tm ON e.text_message_id = tm.id
                            WHERE tm.user_id = %s
                        )
                        ORDER BY c.created_at DESC
                        """,
                        (user_id, user_id),
                    )
                else:
                    # Admin or default - show all cases
                    cur.execute(
                        """
                        SELECT * FROM "case"
                        ORDER BY created_at DESC
                        """
                    )

                results = cur.fetchall()
                # Convert UUIDs to strings
                for r in results:
                    r["id"] = str(r["id"])
                return [CaseResponse(**r) for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events/live", response_model=List[LiveEventResponse])
async def get_live_events(limit: int = Query(200, ge=1, le=500)) -> List[LiveEventResponse]:
    """Get latest geolocated events enriched with case status/severity."""
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        e.id AS event_id,
                        e.case_id,
                        e.description,
                        e.latitude,
                        e.longitude,
                        e.timestamp,
                        c.severity AS case_severity,
                        c.status AS case_status,
                        c.category AS case_category,
                        c.title AS case_title
                    FROM event e
                    JOIN "case" c ON c.id = e.case_id
                    WHERE e.latitude IS NOT NULL AND e.longitude IS NOT NULL
                    ORDER BY e.timestamp DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                results = cur.fetchall()

                for row in results:
                    row["event_id"] = str(row["event_id"])
                    row["case_id"] = str(row["case_id"])

                return [LiveEventResponse(**row) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cases/{case_id}/respond", response_model=Dict)
async def respond_to_case(
    case_id: str,
    request: RespondToCaseRequest,
    user_id: str = Header(alias="X-User-Id"),
) -> Dict:
    """Helper responds to a case to offer assistance."""
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                # Add user as a candidate helper
                cur.execute(
                    """
                    INSERT INTO case_candidates (case_id, user_id)
                    VALUES (%s, %s)
                    ON CONFLICT (case_id, user_id) DO NOTHING
                    """,
                    (case_id, user_id),
                )

                # Update case status if it's still open
                cur.execute(
                    """
                    UPDATE "case"
                    SET status = 'In Progress', updated_at = %s
                    WHERE id = %s AND status = 'Open'
                    """,
                    (datetime.utcnow(), case_id),
                )

                # Create an event log entry
                event_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO event (id, case_id, timestamp, description)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        event_id,
                        case_id,
                        datetime.utcnow(),
                        f"Helper responded: {request.message}",
                    ),
                )

                conn.commit()
                return {"success": True, "message": "Successfully responded to case"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Debug endpoint to view all data
@app.get("/debug/all")
async def get_all_data() -> Dict:
    """Get all cases, events, and messages for debugging."""
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Get all cases
                cur.execute('SELECT * FROM "case" ORDER BY created_at DESC')
                cases = cur.fetchall()

                # Convert UUIDs to strings in cases
                for case in cases:
                    case["id"] = str(case["id"])

                # Get all events including coordinates and maps URL
                cur.execute(
                    "SELECT id, case_id, timestamp, description, latitude, longitude, maps_url, text_message_id FROM event ORDER BY timestamp DESC LIMIT 50"
                )
                events = cur.fetchall()

                # Convert UUIDs to strings in events
                for event in events:
                    event["id"] = str(event["id"])
                    if event.get("case_id"):
                        event["case_id"] = str(event["case_id"])
                    if event.get("text_message_id"):
                        event["text_message_id"] = str(event["text_message_id"])

                # Get all text messages with coordinates and maps URL
                cur.execute(
                    "SELECT id, source, target, raw_text, user_id, latitude, longitude, maps_url, created_at FROM text_message ORDER BY created_at DESC LIMIT 50"
                )
                messages = cur.fetchall()

                # Convert UUIDs to strings in messages
                for msg in messages:
                    msg["id"] = str(msg["id"])
                    if msg.get("user_id"):
                        msg["user_id"] = str(msg["user_id"])

                return {
                    "cases": cases,
                    "events": events,
                    "text_messages": messages,
                    "stats": {
                        "total_cases": len(cases),
                        "open_cases": len([c for c in cases if c["status"] == "Open"]),
                        "total_events": len(events),
                        "total_messages": len(messages),
                    },
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# AI Chat Endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest) -> ChatResponse:
    """Chat with the emergency response AI agent."""
    try:
        # Initialize the agent
        agent = EmergencyAgent(SUPABASE_POSTGRES_URL)

        # Process the message
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]
        user_id = request.user_id or str(uuid.uuid4())

        response_text, case_id, info = agent.process_message(
            request.message, conversation_history, user_id, SUPABASE_POSTGRES_URL
        )

        # Convert info to dict if it exists
        extracted_info = info.dict() if info else None

        return ChatResponse(
            response=response_text, case_id=case_id, extracted_info=extracted_info
        )
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Resource Endpoints
@app.get("/resources", response_model=List[ResourceResponse])
async def get_resources(
    resource_type: Optional[str] = Query(
        None, description="Filter by type (hospital, shelter, supply, etc.)"
    ),
    status: Optional[str] = Query(
        None, description="Filter by status (Available, Full, etc.)"
    ),
    lat: Optional[float] = Query(None, description="Latitude for proximity search"),
    lng: Optional[float] = Query(None, description="Longitude for proximity search"),
    max_distance_km: Optional[float] = Query(
        None, description="Maximum distance in km"
    ),
) -> List[ResourceResponse]:
    """Get resources, optionally filtered by type, status, and proximity."""
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Build query based on filters
                query = """
                    SELECT
                        id, name, description, location,
                        latitude, longitude, maps_url,
                        capacity, status
                """

                # Add distance calculation if coordinates provided
                if lat is not None and lng is not None:
                    query += f""",
                        SQRT(POWER(latitude - {lat}, 2) + POWER(longitude - {lng}, 2)) * 111 as distance_km
                    """
                else:
                    query += ", NULL as distance_km"

                query += " FROM resource WHERE 1=1"

                # Add type filter
                if resource_type:
                    query += f" AND LOWER(name) LIKE '%{resource_type.lower()}%'"

                if status:
                    query += f" AND status = '{status}'"

                # Add distance filter if specified
                if lat is not None and lng is not None and max_distance_km:
                    query += f" AND SQRT(POWER(latitude - {lat}, 2) + POWER(longitude - {lng}, 2)) * 111 <= {max_distance_km}"

                # Order by distance if coordinates provided, otherwise by name
                if lat is not None and lng is not None:
                    query += " ORDER BY distance_km NULLS LAST, name"
                else:
                    query += " ORDER BY name"

                cur.execute(query)
                results = cur.fetchall()

                # Convert UUIDs to strings
                for r in results:
                    r["id"] = str(r["id"])

                return [ResourceResponse(**r) for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resources/nearest", response_model=Optional[ResourceResponse])
async def get_nearest_resource(
    lat: float = Query(..., description="Latitude of emergency"),
    lng: float = Query(..., description="Longitude of emergency"),
    resource_type: Optional[str] = Query(
        None, description="Type of resource needed (hospital, shelter, etc.)"
    ),
) -> Optional[ResourceResponse]:
    """Find the nearest resource to an emergency location."""
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT
                        id, name, description, location,
                        latitude, longitude, maps_url,
                        capacity, status,
                        SQRT(POWER(latitude - %s, 2) + POWER(longitude - %s, 2)) * 111 as distance_km
                    FROM resource
                    WHERE status = 'Available'
                """

                params = [lat, lng]

                if resource_type:
                    query += f" AND LOWER(name) LIKE '%%{resource_type.lower()}%%'"

                query += " ORDER BY distance_km NULLS LAST LIMIT 1"

                cur.execute(query, params)
                result = cur.fetchone()

                if result:
                    result["id"] = str(result["id"])
                    return ResourceResponse(**result)

                return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
