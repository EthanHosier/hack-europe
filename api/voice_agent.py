"""
Phone call emergency agent: collects the same info as the SMS agent, one item at a time,
with a reassuring tone. Uses Gemini. Returns response text for TTS and signals when to end the call.
"""

import json
import logging
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from env import GOOGLE_API_KEY, GOOGLE_MAPS_API_KEY
from agent import EmergencyInfo

logger = logging.getLogger("uvicorn.error")

VOICE_SYSTEM_PROMPT = """You are an emergency response assistant on a live phone call. The caller may be stressed or scared. Your job is to collect the same information as the text-based emergency service, but one piece at a time, in a calm and reassuring way.

Collect these four items (in any order, one or two per turn):
1. Full name
2. Social security number (for identification)
3. Current location (as specific as possible – address, landmark, or area)
4. Description of the emergency – what happened and what they need

Guidelines:
- Be warm, calm, and reassuring. If the caller sounds stressed or upset, acknowledge it and reassure them that help is being coordinated.
- Ask for ONE thing at a time (or at most two). Keep your replies SHORT and natural for speech – a few sentences only. Avoid long paragraphs.
- If they give you more than one piece of information, acknowledge it and ask for the next missing piece.
- Use the same categories and severity as the text service: categories are fuel, medical, shelter, food_water, rescue, other. Severity 1–5 (5 = life-threatening).
- When you have all four (full name, SSN, location, emergency description), thank them, confirm that help is on the way, and say a brief closing such as: "That's everything I need. Help is being coordinated. You can hang up when you're ready. Stay safe."
- Do not repeat back long lists. Keep every response concise and easy to say aloud.

Output format: First write your spoken reply (what the caller hears). Then on a new line write exactly:
VOICE_EXTRACTION: {"full_name": null or "string", "social_security_number": null or "string", "location": null or "string", "emergency_description": null or "string", "category": null or "fuel|medical|shelter|food_water|rescue|other", "severity": 1-5}
Use null for any field not yet provided by the caller. The JSON must be valid and on one line after VOICE_EXTRACTION:."""


# Fast model for low-latency voice; we only send text (transcript + history), no audio.
VOICE_AGENT_MODEL = "gemini-3-flash-preview"


class VoiceAgent:
    def __init__(self) -> None:
        self.llm = ChatGoogleGenerativeAI(
            model=VOICE_AGENT_MODEL,
            temperature=0.6,
            timeout=60,
            max_retries=2,
        )
        self.geocoder = GoogleV3(api_key=GOOGLE_MAPS_API_KEY)

    def _geocode(self, location_text: str) -> tuple[float | None, float | None]:
        if not location_text:
            return None, None
        try:
            location = self.geocoder.geocode(location_text)
            if location:
                logger.debug(
                    "voice_agent_geocode_ok location=%s lat=%.6f lng=%.6f",
                    location_text[:80],
                    location.latitude,
                    location.longitude,
                )
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning("voice_agent_geocode_error location=%s error=%s", location_text, e)
        except Exception as e:
            logger.warning("voice_agent_geocode_error location=%s error=%s", location_text, e)
        return None, None

    def _parse_reply_and_extraction(self, raw: str) -> tuple[str, EmergencyInfo]:
        """Split LLM output into reply text (for TTS) and extraction JSON. Returns (reply, info)."""
        marker = "VOICE_EXTRACTION:"
        idx = raw.find(marker)
        if idx == -1:
            return raw.strip(), EmergencyInfo()
        reply = raw[:idx].strip()
        json_str = raw[idx + len(marker) :].strip()
        for prefix in ("```json", "```"):
            if json_str.startswith(prefix):
                json_str = json_str[len(prefix) :].lstrip()
        if json_str.endswith("```"):
            json_str = json_str[:-3].strip()
        try:
            data = json.loads(json_str)
            info = EmergencyInfo(**data)
            if info.location:
                lat, lng = self._geocode(info.location)
                info.latitude = lat
                info.longitude = lng
            return reply, info
        except Exception as e:
            logger.warning("voice_agent_parse_extraction error=%s", e)
            return reply, EmergencyInfo()

    def _has_all_required(self, info: EmergencyInfo) -> bool:
        return bool(
            info.full_name
            and info.social_security_number
            and info.location
            and info.emergency_description
        )

    def process_utterance(
        self, transcript: str, conversation_history: list[dict[str, str]]
    ) -> tuple[str, EmergencyInfo, bool]:
        """
        One LLM call per turn: returns reply (for TTS), extracted info, and whether to end the call.
        """
        messages: list[SystemMessage | HumanMessage | AIMessage] = [
            SystemMessage(content=VOICE_SYSTEM_PROMPT)
        ]
        for m in conversation_history:
            if m.get("role") == "user":
                messages.append(HumanMessage(content=m.get("content", "")))
            elif m.get("role") == "assistant":
                messages.append(AIMessage(content=m.get("content", "")))
        messages.append(HumanMessage(content=transcript))

        logger.info(
            "voice_agent_utterance transcript_len=%s history_turns=%s",
            len(transcript),
            len(conversation_history),
        )
        t0 = time.perf_counter()
        response = self.llm.invoke(messages)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info("voice_agent_llm_ms ms=%.0f", elapsed_ms)

        if isinstance(response.content, list):
            raw = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in response.content
            )
        else:
            raw = str(response.content)

        reply_text, info = self._parse_reply_and_extraction(raw)
        should_end_call = self._has_all_required(info)
        logger.info(
            "voice_agent_response reply_len=%s should_end_call=%s has_name=%s has_ssn=%s has_location=%s has_description=%s",
            len(reply_text),
            should_end_call,
            bool(info.full_name),
            bool(info.social_security_number),
            bool(info.location),
            bool(info.emergency_description),
        )
        return reply_text, info, should_end_call
