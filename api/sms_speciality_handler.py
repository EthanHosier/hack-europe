"""Handler for SMS received on the speciality Twilio number (+46 76 479 02 15)."""

from fastapi.responses import Response

SUCCESS_RESPONSE = Response(
    content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
    media_type="application/xml",
    status_code=200,
)


def handle_sms_speciality_number(
    from_number: str, to_number: str, body: str, message_sid: str | None
) -> Response:
    return SUCCESS_RESPONSE
