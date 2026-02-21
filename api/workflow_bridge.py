from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel


class InboundWorkflowEvent(BaseModel):
    source: str = "SMS"
    from_number: str
    to_number: str
    body: str
    provider_message_sid: str | None = None
    received_at: str
    raw_payload: dict[str, Any]


def build_inbound_event(
    from_number: str,
    to_number: str,
    body: str,
    provider_message_sid: str | None,
    raw_payload: dict[str, Any],
) -> InboundWorkflowEvent:
    return InboundWorkflowEvent(
        from_number=from_number,
        to_number=to_number,
        body=body,
        provider_message_sid=provider_message_sid,
        received_at=datetime.now(UTC).isoformat(),
        raw_payload=raw_payload,
    )


def handle_inbound_message(event: InboundWorkflowEvent) -> dict[str, Any]:
    # Placeholder contract for the AI teammate. Keep this payload stable.
    return {
        "status": "accepted",
        "workflow": "pending_ai_agent",
        "source": event.source,
        "provider_message_sid": event.provider_message_sid,
    }
