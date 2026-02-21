from datetime import UTC, datetime
import json
from typing import Any
from urllib import error, request

from pydantic import BaseModel
from env import WORKFLOW_WEBHOOK_URL


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
    # Use WORKFLOW_WEBHOOK_URL as a base URL and route SMS events to /sms.
    target_url = f"{WORKFLOW_WEBHOOK_URL.rstrip('/')}/sms"
    payload = event.model_dump()

    req = request.Request(
        target_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
    except error.URLError as exc:
        return {
            "status": "accepted",
            "workflow": "pending_ai_agent",
            "source": event.source,
            "provider_message_sid": event.provider_message_sid,
            "forwarded_to": target_url,
            "forward_status": "failed",
            "forward_error": str(exc),
        }

    return {
        "status": "accepted",
        "workflow": "pending_ai_agent",
        "source": event.source,
        "provider_message_sid": event.provider_message_sid,
        "forwarded_to": target_url,
        "forward_status": status_code,
    }
