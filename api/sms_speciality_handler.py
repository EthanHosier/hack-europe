"""Handler for SMS received on the speciality Twilio number (+46 76 479 02 15)."""

import json
import logging
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from fastapi.responses import Response
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from env import (
    GOOGLE_API_KEY,
    GOOGLE_MAPS_API_KEY,
    OPENAI_API_KEY,
    SUPABASE_POSTGRES_URL,
)
from twilio_app import send_sms

logger = logging.getLogger("uvicorn.error")

SUCCESS_RESPONSE = Response(
    content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
    media_type="application/xml",
    status_code=200,
)


def load_historic_speciality_messages(phone_number: str) -> list[str]:
    """
    Load all historic ethan_speciality_historic_messages for the given phone number.
    Returns text contents only, oldest first.
    """
    with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT text_content
                FROM ethan_speciality_historic_messages
                WHERE phone_from = %s
                ORDER BY created_at ASC
                """,
                (phone_number.strip(),),
            )
            return [row["text_content"] for row in cur.fetchall()]


def _persist_speciality_message(phone_from: str, text_content: str) -> None:
    """Insert one inbound message into ethan_speciality_historic_messages."""
    with psycopg.connect(SUPABASE_POSTGRES_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ethan_speciality_historic_messages (phone_from, text_content)
                VALUES (%s, %s)
                """,
                (phone_from.strip(), text_content),
            )


FIRST_MESSAGE_REPLY = (
    "Thanks for reaching out! Please reply with your name and a description of your skills and your location."
)

GEMINI_MODEL = "gemini-3-flash-preview"


def _parse_speciality_with_llm(messages: list[str]) -> tuple[dict | None, str | None]:
    """
    Use Gemini to parse name, skills (≥1), and location from the user's messages.
    Returns (parsed_dict, None) if satisfactory JSON was extracted, else (None, follow_up_message).
    parsed_dict has keys: name, skills (list[str]), location, confirmation_message (str).
    """
    if not GOOGLE_API_KEY:
        return (
            None,
            "Please send your name, at least one skill, and your location.",
        )
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        temperature=0.2,
        timeout=30,
        max_retries=2,
    )
    conversation = "\n".join(f"- {m}" for m in messages)
    prompt = f"""You are parsing SMS messages from a user who is registering their skills. Extract:
- name: full name
- skills: list of at least one skill (e.g. first aid, nursing, driving)
- location: where they are based (city/region or address)

Conversation from user (oldest first):
{conversation}

If you can extract all three (name, at least one skill, location) to a clear standard, reply with ONLY a single line of valid JSON, no other text or markdown. Include a short, friendly confirmation_message to send back (do not repeat their name, skills, or location):
{{"name": "...", "skills": ["...", ...], "location": "...", "confirmation_message": "One short friendly SMS confirming we got their info."}}

If anything is missing or too vague, reply with a single short message asking the user to provide the missing information or to expand (e.g. "Please share your name and location." or "Could you list at least one skill?"). Do not output JSON in that case."""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        text = (response.content or "").strip()
        raw = _extract_json_object(text)
        if raw is None:
            follow = text if text else "Please send your name, at least one skill, and your location."
            return (None, follow)
        parsed = _validate_parsed_speciality(raw)
        if parsed is not None:
            return (parsed, None)
        follow = text if text else "Please send your name, at least one skill, and your location."
        return (None, follow)
    except Exception:
        return (
            None,
            "Please send your name, at least one skill, and your location.",
        )


def _extract_json_object(text: str) -> str | None:
    """Extract first {...} span from text (handles nested braces)."""
    start = 0 if text.startswith("{") else text.find("{")
    if start < 0:
        return None
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start : j + 1]
    return None


def _validate_parsed_speciality(raw: str) -> dict | None:
    """Parse raw JSON and return dict if name, ≥1 skill, location present; else None. May include confirmation_message."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    name = (data.get("name") or "").strip()
    skills = data.get("skills")
    if not isinstance(skills, list):
        return None
    skills = [str(s).strip() for s in skills if str(s).strip()]
    if len(skills) < 1:
        return None
    location = (data.get("location") or "").strip()
    if not name or not location:
        return None
    confirmation = (data.get("confirmation_message") or "").strip()
    return {"name": name, "skills": skills, "location": location, "confirmation_message": confirmation or "Thanks, we've got your details!"}


def _geocode_location(location_text: str) -> tuple[float | None, float | None]:
    """Geocode a location string to (lat, lng) using Google Maps. Same pattern as elsewhere in the codebase."""
    if not location_text or not GOOGLE_MAPS_API_KEY:
        return None, None
    try:
        geocoder = GoogleV3(api_key=GOOGLE_MAPS_API_KEY)
        result = geocoder.geocode(location_text.strip())
        if result:
            return result.latitude, result.longitude
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning("speciality_geocode_error location=%s error=%s", location_text[:80], e)
    except Exception as e:
        logger.warning("speciality_geocode_error location=%s error=%s", location_text[:80], e)
    return None, None


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate 1536-dim OpenAI embeddings for each text. Returns list of embedding vectors."""
    if not OPENAI_API_KEY or not texts:
        return []
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small",
        )
        return [d.embedding for d in response.data]
    except Exception as e:
        logger.warning("speciality_embed_error error=%s", e)
        return []


def _persist_parsed_speciality(
    from_number: str,
    parsed: dict,
    latitude: float | None,
    longitude: float | None,
    skill_embeddings: list[list[float]],
) -> None:
    """Find or create user by phone; update name/location/lat/lng; insert ethan_user_speciality rows when we have embeddings."""
    name = parsed["name"]
    location = parsed["location"]
    skills = parsed["skills"]
    with psycopg.connect(SUPABASE_POSTGRES_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id FROM "user" WHERE phone = %s LIMIT 1""",
                (from_number.strip(),),
            )
            row = cur.fetchone()
            if row:
                user_id = row[0]
                cur.execute(
                    """
                    UPDATE "user"
                    SET name = %s, location = %s, latitude = %s, longitude = %s, last_location_update = %s
                    WHERE id = %s
                    """,
                    (name, location, latitude, longitude, datetime.now(), user_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO "user" (id, name, phone, role, status, location, latitude, longitude, last_location_update)
                    VALUES (gen_random_uuid(), %s, %s, 'Responder', 'Active', %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (name, from_number.strip(), location, latitude, longitude, datetime.now()),
                )
                user_id = cur.fetchone()[0]
            if len(skill_embeddings) == len(skills):
                for skill, embedding in zip(skills, skill_embeddings):
                    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    cur.execute(
                        """
                        INSERT INTO ethan_user_speciality (user_id, speciality, embedding)
                        VALUES (%s, %s, %s::vector)
                        """,
                        (user_id, skill, vec_str),
                    )
            conn.commit()


def handle_sms_speciality_number(
    from_number: str, to_number: str, body: str, message_sid: str | None
) -> Response:
    historic = load_historic_speciality_messages(from_number)
    is_first_message = len(historic) == 0

    _persist_speciality_message(from_number, body)

    if is_first_message:
        send_sms(from_number, FIRST_MESSAGE_REPLY)
        return SUCCESS_RESPONSE

    # Full conversation: historic + this message (we just persisted it)
    all_messages = historic + [body]
    parsed, follow_up = _parse_speciality_with_llm(all_messages)
    if follow_up:
        send_sms(from_number, follow_up)
        return SUCCESS_RESPONSE

    # Parsed case: geocode location, embed each skill, persist user + ethan_user_speciality, then send confirmation
    lat, lng = _geocode_location(parsed["location"])
    skill_embeddings = _embed_texts(parsed["skills"])
    _persist_parsed_speciality(from_number, parsed, lat, lng, skill_embeddings)
    send_sms(from_number, parsed["confirmation_message"])
    return SUCCESS_RESPONSE

