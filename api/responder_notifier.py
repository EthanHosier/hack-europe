"""
Responder notification system for alerting nearby helpers in emergencies.
"""

import math
from typing import List, Dict, Tuple, Optional
import psycopg
from psycopg.rows import dict_row
from twilio_service import send_sms
import logging

logger = logging.getLogger(__name__)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates in kilometers using Haversine formula.
    """
    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return distance


def find_nearby_responders(
    db_url: str,
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    needed_specialties: Optional[List[str]] = None,
    limit: int = 30,
    only_real_numbers: bool = True,
) -> List[Dict]:
    """
    Find active responders within a given radius of the emergency location.

    Args:
        db_url: Database connection string
        latitude: Emergency location latitude
        longitude: Emergency location longitude
        radius_km: Search radius in kilometers (default 5km)
        needed_specialties: Optional list of required specialties (e.g., ["Doctor", "EMT"])
        limit: Maximum number of responders to return

    Returns:
        List of responder dictionaries with contact info and distance
    """
    responders = []

    try:
        with psycopg.connect(db_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Base query for active responders with location
                query = """
                    SELECT DISTINCT
                        u.id::text as id,
                        u.name,
                        u.phone,
                        u.location,
                        u.latitude,
                        u.longitude,
                        u.last_location_update,
                        u.has_real_number,
                        array_agg(s.name) as specialties
                    FROM "user" u
                    LEFT JOIN user_specialty us ON u.id = us.user_id
                    LEFT JOIN specialty s ON us.specialty_id = s.id
                    WHERE u.role = 'Responder'
                    AND u.status = 'Active'
                    AND u.latitude IS NOT NULL
                    AND u.longitude IS NOT NULL
                    AND u.phone IS NOT NULL
                """

                # Add filter for real phone numbers if requested
                params = []
                if only_real_numbers:
                    query += " AND u.has_real_number = true"

                # Add specialty filter if needed
                if needed_specialties:
                    query += """
                    AND EXISTS (
                        SELECT 1 FROM user_specialty us2
                        JOIN specialty s2 ON us2.specialty_id = s2.id
                        WHERE us2.user_id = u.id
                        AND s2.name = ANY(%s)
                    )
                    """
                    params.append(needed_specialties)

                query += """
                    GROUP BY u.id::text, u.name, u.phone, u.location, u.latitude, u.longitude, u.last_location_update, u.has_real_number
                """

                cur.execute(query, params)
                potential_responders = cur.fetchall()

                # Calculate distances and filter by radius
                for responder in potential_responders:
                    if responder["latitude"] and responder["longitude"]:
                        distance = calculate_distance(
                            latitude,
                            longitude,
                            responder["latitude"],
                            responder["longitude"],
                        )

                        if distance <= radius_km:
                            responder["distance_km"] = round(distance, 2)
                            responders.append(responder)

                # Sort by distance and limit
                responders.sort(key=lambda x: x["distance_km"])
                responders = responders[:limit]

    except Exception as e:
        logger.error(f"Error finding nearby responders: {e}")

    return responders


def notify_responders(
    responders: List[Dict], emergency_info: Dict, case_id: Optional[str] = None, db_url: Optional[str] = None
) -> Tuple[int, int]:
    """
    Send SMS notifications to responders about an emergency.

    Args:
        responders: List of responder dictionaries with phone numbers
        emergency_info: Emergency details (location, type, severity, etc.)
        case_id: Optional case ID for tracking

    Returns:
        Tuple of (successful_notifications, failed_notifications)
    """
    successful = 0
    failed = 0

    for responder in responders:
        try:
            # Construct the SMS message
            message = f"🚨 EMERGENCY ALERT\n\n"
            message += f"Your help is needed {responder['distance_km']}km away!\n\n"

            if emergency_info.get("emergency_description"):
                message += (
                    f"Situation: {emergency_info['emergency_description'][:100]}\n"
                )

            if emergency_info.get("location"):
                message += f"Location: {emergency_info['location']}\n"

            if emergency_info.get("latitude") and emergency_info.get("longitude"):
                maps_url = f"https://www.google.com/maps?q={emergency_info['latitude']},{emergency_info['longitude']}"
                message += f"Maps: {maps_url}\n"

            if emergency_info.get("category"):
                message += f"Type: {emergency_info['category']}\n"

            if emergency_info.get("severity"):
                message += f"Severity: {emergency_info['severity']}/5\n"

            if case_id:
                message += f"\nCase ID: {case_id[:8]}\n"

            message += "\nReply YES if you can respond."

            # Send the SMS
            result = send_sms(responder["phone"], message)

            if result.status:
                successful += 1
                logger.info(
                    f"Notified responder {responder['name']} at {responder['phone']}"
                )

                # Track assignment in database if case_id and db_url provided
                if case_id and db_url:
                    try:
                        import uuid
                        from datetime import datetime
                        with psycopg.connect(db_url, row_factory=dict_row) as conn:
                            with conn.cursor() as cur:
                                cur.execute(
                                    """
                                    INSERT INTO responder_assignment
                                    (case_id, responder_id, status, distance_km, notified_at)
                                    VALUES (%s, %s, %s, %s, %s)
                                    ON CONFLICT (case_id, responder_id) DO UPDATE
                                    SET status = 'notified', notified_at = %s
                                    """,
                                    (
                                        case_id,
                                        responder["id"],
                                        "notified",
                                        responder.get("distance_km"),
                                        datetime.now(),
                                        datetime.now()
                                    )
                                )
                                conn.commit()
                                logger.info(f"Tracked assignment for responder {responder['id']} to case {case_id}")
                    except Exception as e:
                        logger.error(f"Failed to track assignment: {e}")
            else:
                failed += 1
                logger.error(
                    f"Failed to notify {responder['name']}: {result.error_message}"
                )

        except Exception as e:
            failed += 1
            logger.error(f"Error notifying responder {responder['name']}: {e}")

    return successful, failed


def alert_nearby_help(
    db_url: str,
    emergency_info: Dict,
    case_id: Optional[str] = None,
    radius_km: float = 5.0,
    max_responders: int = 3,
) -> Dict:
    """
    Main function to find and alert nearby responders based on emergency type.

    Args:
        db_url: Database connection string
        emergency_info: Emergency details including location, type, etc.
        case_id: Optional case ID
        radius_km: Search radius (default 5km)
        max_responders: Maximum number of responders to notify

    Returns:
        Dictionary with notification results
    """
    result = {
        "responders_found": 0,
        "notifications_sent": 0,
        "notifications_failed": 0,
        "responders": [],
    }

    # Check if we have location coordinates
    if not emergency_info.get("latitude") or not emergency_info.get("longitude"):
        logger.warning(
            "No coordinates available for emergency, cannot find nearby responders"
        )
        return result

    # Determine needed specialties based on emergency category
    category = emergency_info.get("category", "").lower()
    emergency_desc = emergency_info.get("emergency_description", "").lower()
    needed_specialties = None

    # Check for allergy/epipen emergency first
    if any(word in emergency_desc for word in ["allerg", "anaphyl", "epipen", "bee sting", "peanut", "shellfish"]):
        needed_specialties = ["EPIPEN_HOLDER", "Doctor", "EMT"]
    elif "medical" in category or "injury" in category or "health" in category:
        needed_specialties = ["Doctor", "Nurse", "EMT"]
    elif "fire" in category:
        needed_specialties = ["Firefighter"]
    elif "crime" in category or "violence" in category:
        needed_specialties = ["Police"]
    elif "mental" in category or "suicide" in category:
        needed_specialties = ["Mental Health", "Doctor"]
    elif "rescue" in category or "trapped" in category:
        needed_specialties = ["Search & Rescue", "Firefighter"]

    # Find nearby responders (only those with real phone numbers)
    responders = find_nearby_responders(
        db_url,
        emergency_info["latitude"],
        emergency_info["longitude"],
        radius_km,
        needed_specialties,
        max_responders,
        only_real_numbers=True,  # Only notify responders with real SMS-capable numbers
    )

    result["responders_found"] = len(responders)
    result["responders"] = [
        {
            "name": r["name"],
            "distance_km": r["distance_km"],
            "specialties": r.get("specialties", []),
        }
        for r in responders
    ]

    # Send notifications if responders found
    if responders:
        successful, failed = notify_responders(responders, emergency_info, case_id, db_url)
        result["notifications_sent"] = successful
        result["notifications_failed"] = failed

        logger.info(f"Alerted {successful} responders, {failed} failed")

    return result
