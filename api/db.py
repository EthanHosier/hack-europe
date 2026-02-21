"""Database persistence helpers."""

import psycopg

from env import SUPABASE_POSTGRES_URL


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
                    ("SMS", target, raw_text, direction, provider_message_sid, delivery_status),
                )
                inserted_id = cur.fetchone()[0]
            except psycopg.errors.UndefinedColumn:
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
