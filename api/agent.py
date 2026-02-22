"""
Emergency Response AI Agent using LangChain and Gemini
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import psycopg
from psycopg.rows import dict_row
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel
from geopy.geocoders import GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from env import GOOGLE_API_KEY, GOOGLE_MAPS_API_KEY


class EmergencyInfo(BaseModel):
    """Extracted emergency information"""

    full_name: Optional[str] = None
    social_security_number: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    emergency_description: Optional[str] = None
    category: Optional[str] = None  # fuel, medical, shelter, etc.
    severity: Optional[int] = 3  # 1-5 scale
    stress_level: Optional[str] = None  # Low, Medium, High


class EmergencyAgent:
    def __init__(self, supabase_url: str):
        self.supabase_url = supabase_url
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview",
            temperature=0.7,
            # max_tokens=None,
            timeout=None,
            max_retries=2,
        )
        self.geocoder = GoogleV3(api_key=GOOGLE_MAPS_API_KEY)

        self.system_prompt = """You are an emergency response AI assistant. Your job is to gather critical information from people in emergency situations.

You need to collect the following information:
1. Full name
2. Social security number (for identification)
3. Current location (as specific as possible)
4. Description of the emergency/problem

Be compassionate but efficient. Ask for remaining information if not provided. Once you have all required information, confirm it with the person.

When categorizing emergencies, use these categories:
- fuel: Out of fuel, gas, vehicle fuel issues
- medical: Injuries, illness, medical emergencies, allergic reactions, anaphylaxis
- shelter: Need for shelter, stuck in dangerous weather
- food_water: Need for food or water
- rescue: Trapped, lost, need extraction
- other: Anything else

Rate severity from 1-5:
- 5: Life-threatening, immediate danger (anaphylaxis, heart attack, severe bleeding)
- 4: Urgent, serious risk (severe allergic reaction, difficulty breathing)
- 3: Moderate urgency
- 2: Low urgency
- 1: Minor issue

IMPORTANT: For any allergic reaction or mention of EpiPen, categorize as "medical" with severity 4-5

Remember: Be professional, calm, and reassuring. People are in distress."""

    def geocode_location(
        self, location_text: str
    ) -> Tuple[Optional[float], Optional[float]]:
        """Geocode a location description to get latitude and longitude"""
        if not location_text:
            print(f"DEBUG geocode_location: No location text provided")
            return None, None

        print(f"DEBUG geocode_location: Attempting to geocode '{location_text}'")

        # Fallback coordinates for known demo locations
        DEMO_LOCATIONS = {
            "stf vakkotavare": (67.58170, 18.10040),
            "vakkotavare": (67.58170, 18.10040),
            "stf vakkotavare hut": (67.58170, 18.10040),
            "stockholm": (59.3293, 18.0686),
            "gothenburg": (57.7089, 11.9746),
            "göteborg": (57.7089, 11.9746),
            "malmö": (55.6049, 13.0038),
            "uppsala": (59.8586, 17.6389),
        }

        # Check for known demo locations first (case-insensitive)
        location_lower = location_text.lower()
        for known_location, coords in DEMO_LOCATIONS.items():
            if known_location in location_lower:
                print(f"DEMO MODE: Using hardcoded coordinates for '{location_text}': {coords[0]}, {coords[1]}")
                return coords

        try:
            if not GOOGLE_MAPS_API_KEY:
                print(f"WARNING: GOOGLE_MAPS_API_KEY is not set! Using fallback demo coordinates.")
                # Default to Stockholm for demo if no specific location match
                return 59.3293, 18.0686

            location = self.geocoder.geocode(location_text)
            if location:
                print(
                    f"SUCCESS: Geocoded '{location_text}' to: {location.latitude}, {location.longitude}"
                )
                return location.latitude, location.longitude
            else:
                print(f"WARNING: Geocoding returned no results for '{location_text}'")
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"ERROR: Geocoding service error for '{location_text}': {e}")
        except Exception as e:
            print(f"ERROR: Unexpected geocoding error for '{location_text}': {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

        # Fallback to Stockholm coordinates for demo
        print(f"FALLBACK: Using default Stockholm coordinates for demo")
        return 59.3293, 18.0686

    def extract_info_from_conversation(self, messages: List[Dict]) -> EmergencyInfo:
        """Extract structured information from the conversation"""
        # Create a prompt to extract information
        extraction_prompt = f"""Based on the conversation below, extract the following information:
        - Full name
        - Social security number
        - Location
        - Emergency description
        - Category (fuel/medical/shelter/food_water/rescue/other) - use "medical" for any allergic reactions
        - Severity (1-5) - use 4-5 for allergic reactions requiring EpiPen

        Conversation:
        {json.dumps(messages, indent=2)}

        Return as JSON with keys: full_name, social_security_number, location, emergency_description, category, severity
        If any information is not available, use null for that field."""

        response = self.llm.invoke(
            [
                SystemMessage(
                    content="You are an information extraction assistant. Extract structured data from conversations."
                ),
                HumanMessage(content=extraction_prompt),
            ]
        )

        try:
            # Handle both string and list response formats from Gemini
            if isinstance(response.content, list):
                # Extract text from content blocks
                content = "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in response.content
                ).strip()
            else:
                content = str(response.content).strip()

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            data = json.loads(content.strip())
            print(f"DEBUG: Extracted data from conversation: {json.dumps(data, indent=2)}")
            info = EmergencyInfo(**data)

            # Geocode the location if provided
            if info.location:
                print(f"DEBUG: Location found in extracted info: '{info.location}'")
                lat, lng = self.geocode_location(info.location)
                info.latitude = lat
                info.longitude = lng
                print(f"DEBUG: After geocoding - lat={info.latitude}, lon={info.longitude}")
            else:
                print(f"DEBUG: No location found in extracted info")

            return info
        except Exception as e:
            # If parsing fails, log the error and return empty info
            print(f"ERROR extracting emergency info: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return EmergencyInfo()

    def should_create_case(self, info: EmergencyInfo) -> bool:
        """Check if we have enough information to create a case"""
        return all(
            [
                info.full_name,
                info.social_security_number,
                info.location,
                info.emergency_description,
            ]
        )

    def create_case(self, info: EmergencyInfo, user_id: str, conn) -> str:
        """Create an emergency case in the database"""
        with conn.cursor() as cur:
            case_id = str(uuid.uuid4())
            now = datetime.utcnow()

            # First, ensure user exists (create if not)
            cur.execute('SELECT id FROM "user" WHERE id = %s', (user_id,))
            if not cur.fetchone():
                # Create user with info we have including coordinates
                cur.execute(
                    """
                    INSERT INTO "user" (id, name, phone, role, status, location, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        user_id,
                        info.full_name or "Unknown",
                        info.social_security_number or "Unknown",
                        "Victim",
                        "Active",
                        info.location,
                        info.latitude,
                        info.longitude,
                    ),
                )

            # Determine category and severity
            category = info.category or "other"
            severity = info.severity or 3
            title = f"{category.replace('_', ' ').title()} Emergency"

            # Create the case
            cur.execute(
                """
                INSERT INTO "case" (id, title, summary, severity, status, category, stress_level, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    case_id,
                    title,
                    info.emergency_description[:200],
                    severity,
                    "Open",
                    category,
                    info.stress_level,
                    now,
                    now,
                ),
            )

            # Create initial event
            event_id = str(uuid.uuid4())
            coords_text = (
                f"\nCoordinates: {info.latitude:.6f}, {info.longitude:.6f}"
                if info.latitude and info.longitude
                else ""
            )
            event_description = f"{info.emergency_description} {info.location}"

            cur.execute(
                """
                INSERT INTO event (id, case_id, timestamp, description, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    case_id,
                    now,
                    event_description,
                    info.latitude,
                    info.longitude,
                ),
            )

            # Store initial message with coordinates
            message_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO text_message (id, source, target, raw_text, user_id, latitude, longitude, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    message_id,
                    "SMS",
                    "emergency",
                    event_description,
                    user_id,
                    info.latitude,
                    info.longitude,
                    now,
                ),
            )

            conn.commit()
            return case_id

    def process_message(
        self, message: str, conversation_history: List[Dict], user_id: str, db_url: str
    ) -> Tuple[str, Optional[str], Optional[EmergencyInfo]]:
        """Process a message and return response, case_id if created, and extracted info"""
        # Build message history for the LLM
        messages = [SystemMessage(content=self.system_prompt)]

        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        # Add the new message
        messages.append(HumanMessage(content=message))

        # Get response from LLM
        response = self.llm.invoke(messages)
        # Handle both string and list response formats from Gemini
        if isinstance(response.content, list):
            # Extract text from content blocks
            response_text = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in response.content
            )
        else:
            response_text = str(response.content)

        # Extract information from the conversation
        full_conversation = conversation_history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": response_text},
        ]

        info = self.extract_info_from_conversation(full_conversation)

        # Check if we should create a case
        case_id = None
        responder_notification = None
        if self.should_create_case(info):
            try:
                with psycopg.connect(db_url, row_factory=dict_row) as conn:
                    case_id = self.create_case(info, user_id, conn)

                    # Add confirmation to response
                    response_text += (
                        f"\n\n✅ Emergency case created! Case ID: {case_id[:8]}...\n"
                    )
                    response_text += (
                        f"Category: {info.category}, Severity: {info.severity}/5\n"
                    )
                    if info.latitude and info.longitude:
                        response_text += f"📍 Location coordinates: {info.latitude:.6f}, {info.longitude:.6f}\n"

                    # Alert nearby responders for high-severity emergencies
                    print(f"DEBUG: Checking if should alert responders - severity={info.severity}, lat={info.latitude}, lon={info.longitude}")

                    if (
                        info.severity
                        and info.severity >= 3
                        and info.latitude
                        and info.longitude
                    ):
                        print(f"DEBUG: Conditions met! Attempting to alert responders...")
                        try:
                            from responder_notifier import alert_nearby_help

                            # Convert EmergencyInfo to dict for the notifier
                            emergency_dict = {
                                "emergency_description": info.emergency_description,
                                "location": info.location,
                                "latitude": info.latitude,
                                "longitude": info.longitude,
                                "category": info.category,
                                "severity": info.severity,
                            }

                            print(f"DEBUG: Emergency info - category={info.category}, desc={info.emergency_description[:50] if info.emergency_description else 'None'}")

                            # DEMO MODE: Use very large radius
                            radius_km = 500.0  # 500km to cover all of Northern Sweden for demo
                            print(f"DEBUG: DEMO MODE - Searching for responders within {radius_km}km...")

                            # Alert responders
                            notification_result = alert_nearby_help(
                                db_url,
                                emergency_dict,
                                case_id,
                                radius_km=radius_km,
                                max_responders=10,  # Allow more responders for demo
                            )

                            print(f"DEBUG: Notification result: {notification_result}")

                            if notification_result["notifications_sent"] > 0:
                                response_text += f"\n🚨 {notification_result['notifications_sent']} nearby responders have been alerted!"
                                responder_notification = notification_result
                            elif notification_result["responders_found"] > 0:
                                response_text += f"\n⚠️ Found {notification_result['responders_found']} responders but couldn't send SMS (check Twilio/phone numbers)"
                            else:
                                response_text += f"\n⚠️ No responders found within {radius_km}km. Expand search area or add more responders."

                        except Exception as e:
                            import traceback
                            print(f"ERROR alerting responders: {e}")
                            print(f"Full traceback: {traceback.format_exc()}")
                            response_text += f"\n⚠️ Error alerting responders (check logs)"
                            # Don't fail the whole process if responder notification fails
                    else:
                        print(f"DEBUG: Not alerting responders - conditions not met")

                    response_text += "\nHelp is being coordinated. Stay calm and safe."
            except Exception as e:
                print(f"Error creating case: {e}")
                response_text += "\n\n⚠️ There was an issue creating your emergency case. Please try again."

        return response_text, case_id, info
