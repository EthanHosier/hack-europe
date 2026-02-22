"""Twilio SMS: send messages, client, signature validation."""

from dataclasses import dataclass
from typing import Mapping

from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from env import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER


class TwilioConfigError(RuntimeError):
    """Raised when required Twilio environment variables are missing."""


@dataclass
class SentSmsResult:
    message_sid: str
    status: str | None
    to_number: str
    from_number: str
    error_code: int | None
    error_message: str | None


def _require_twilio_credentials() -> tuple[str, str, str]:
    if not TWILIO_ACCOUNT_SID:
        raise TwilioConfigError("TWILIO_ACCOUNT_SID is required for SMS operations")
    if not TWILIO_AUTH_TOKEN:
        raise TwilioConfigError("TWILIO_AUTH_TOKEN is required for SMS operations")
    if not TWILIO_FROM_NUMBER:
        raise TwilioConfigError("TWILIO_FROM_NUMBER is required for SMS operations")
    return TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER


def get_twilio_client() -> tuple[Client, str]:
    account_sid, auth_token, from_number = _require_twilio_credentials()
    return Client(account_sid, auth_token), from_number


def validate_twilio_signature(
    request_url: str, form_data: Mapping[str, str], signature: str | None
) -> bool:
    if not TWILIO_AUTH_TOKEN:
        return True
    if not signature:
        return False
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    return validator.validate(request_url, dict(form_data), signature)


def send_sms(to_number: str, body: str) -> SentSmsResult:
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"DEBUG send_sms: Attempting to send SMS to {to_number}, body length: {len(body)}")

    client, from_number = get_twilio_client()
    try:
        message = client.messages.create(to=to_number, from_=from_number, body=body)
        logger.info(f"DEBUG send_sms: Successfully created message sid={message.sid}, status={message.status}")
    except TwilioRestException as e:
        logger.error(f"DEBUG send_sms: TwilioRestException - {e}")
        raise

    result = SentSmsResult(
        message_sid=message.sid,
        status=message.status,
        to_number=message.to,
        from_number=message.from_,
        error_code=message.error_code,
        error_message=message.error_message,
    )

    logger.info(f"DEBUG send_sms: Returning result with status={result.status}")
    return result
