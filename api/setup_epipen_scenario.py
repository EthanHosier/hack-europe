#!/usr/bin/env python3
"""
Setup script for epipen allergy emergency scenario in Gällivare, Sweden.
This creates:
- Gällivare hospital as a resource
- 4 responders with EPIPEN_HOLDER trait at specific locations
- 10 random people near the emergency location
"""

import psycopg
from psycopg.rows import dict_row
from env import SUPABASE_POSTGRES_URL
from datetime import datetime
import uuid
import random
import math


def add_epipen_specialty():
    """Add EPIPEN_HOLDER as a specialty if it doesn't exist"""
    with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO specialty (name, description)
                VALUES ('EPIPEN_HOLDER', 'Person carrying an EpiPen for emergency allergic reactions')
                ON CONFLICT DO NOTHING
                RETURNING id
                """
            )
            result = cur.fetchone()
            if result:
                print("✅ Added EPIPEN_HOLDER specialty")
                return result["id"]
            else:
                # Already exists, fetch it
                cur.execute("SELECT id FROM specialty WHERE name = 'EPIPEN_HOLDER'")
                return cur.fetchone()["id"]


def add_gallivare_hospital():
    """Add Gällivare hospital as a resource"""
    with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Check if already exists
            cur.execute(
                "SELECT id FROM resource WHERE name = %s", ("Gällivare Hospital",)
            )
            existing = cur.fetchone()

            if existing:
                # Update existing
                cur.execute(
                    """
                    UPDATE resource
                    SET description = %s, location = %s, latitude = %s, longitude = %s,
                        status = %s, capacity = %s
                    WHERE id = %s
                    """,
                    (
                        "Main hospital in Gällivare, Northern Sweden. Emergency department, ICU, and allergy treatment available.",
                        "Lasarettsvägen 1, 982 32 Gällivare, Sweden",
                        67.13078211097809,
                        20.685876386471627,
                        "Available",
                        150,
                        existing["id"],
                    ),
                )
                print(f"✅ Updated Gällivare Hospital")
            else:
                # Insert new
                cur.execute(
                    """
                    INSERT INTO resource (name, description, location, latitude, longitude, status, capacity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        "Gällivare Hospital",
                        "Main hospital in Gällivare, Northern Sweden. Emergency department, ICU, and allergy treatment available.",
                        "Lasarettsvägen 1, 982 32 Gällivare, Sweden",
                        67.13078211097809,
                        20.685876386471627,
                        "Available",
                        150,
                    ),
                )
                print("✅ Added Gällivare Hospital")

            conn.commit()


def add_epipen_responders(epipen_specialty_id):
    """Add the 4 responders with EPIPEN_HOLDER trait"""
    responders = [
        {
            "name": "Jonathan",
            "phone": "+46701111111",  # Test phone number
            "latitude": 66.59406948212037,
            "longitude": 19.835238730963756,
            "location": "Near Jokkmokk, Sweden",
            "has_real_number": False,  # Test/dummy number
        },
        {
            "name": "Julius",
            "phone": "+46702222222",  # Test phone number
            "latitude": 66.47210735120946,
            "longitude": 19.65147711306981,
            "location": "Near Vuollerim, Sweden",
            "has_real_number": False,  # Test/dummy number
        },
        {
            "name": "Hanyu",
            "phone": "+46761695198",  # Real phone number
            "latitude": 67.592271572682,
            "longitude": 18.10550500960355,
            "location": "Near Stora Sjöfallet, Sweden",
            "has_real_number": True,  # Real SMS-capable number
        },
        {
            "name": "Yukie",
            "phone": "+46767097416",  # Real phone number
            "latitude": 67.59801366670555,
            "longitude": 18.02546752650639,
            "location": "Near Ritsem, Sweden",
            "has_real_number": True,  # Real SMS-capable number
        },
    ]

    with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for responder in responders:
                # Check if user exists
                cur.execute(
                    'SELECT id FROM "user" WHERE name = %s', (responder["name"],)
                )
                existing = cur.fetchone()

                if existing:
                    user_id = existing["id"]
                    # Update existing user
                    cur.execute(
                        """
                        UPDATE "user"
                        SET phone = %s, role = %s, status = %s, location = %s,
                            latitude = %s, longitude = %s, last_location_update = %s,
                            has_real_number = %s
                        WHERE id = %s
                        """,
                        (
                            responder["phone"],
                            "Responder",
                            "Active",
                            responder["location"],
                            responder["latitude"],
                            responder["longitude"],
                            datetime.now(),
                            responder.get("has_real_number", False),
                            user_id,
                        ),
                    )
                    print(f"✅ Updated responder: {responder['name']} (real_number={responder.get('has_real_number', False)})")
                else:
                    # Insert new user
                    user_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO "user" (id, name, phone, role, status, location, latitude, longitude, last_location_update, has_real_number)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            responder["name"],
                            responder["phone"],
                            "Responder",
                            "Active",
                            responder["location"],
                            responder["latitude"],
                            responder["longitude"],
                            datetime.now(),
                            responder.get("has_real_number", False),
                        ),
                    )
                    print(f"✅ Added responder: {responder['name']} (real_number={responder.get('has_real_number', False)})")

                # Add EPIPEN_HOLDER specialty
                cur.execute(
                    """
                    INSERT INTO user_specialty (user_id, specialty_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (user_id, epipen_specialty_id),
                )

                # Calculate distance from emergency location
                emergency_lat = 67.83938120422421
                emergency_lon = 20.202353143851322
                distance = calculate_distance(
                    responder["latitude"],
                    responder["longitude"],
                    emergency_lat,
                    emergency_lon,
                )
                print(f"  📍 Distance from emergency: {distance:.1f}km")

            conn.commit()


def add_nearby_people():
    """Add 10 random people near the specified location"""
    # Location near Stora Sjöfallet National Park
    center_lat = 67.58206948569072
    center_lon = 18.100322973095093

    # Swedish first and last names for realistic data
    first_names = [
        "Erik",
        "Anna",
        "Lars",
        "Maria",
        "Sven",
        "Karin",
        "Nils",
        "Ingrid",
        "Olof",
        "Astrid",
    ]
    last_names = [
        "Lindqvist",
        "Nilsson",
        "Johansson",
        "Bergström",
        "Lundgren",
        "Hedberg",
        "Eklund",
        "Nordström",
        "Wikström",
        "Sandberg",
    ]

    with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for i in range(10):
                # Generate random position within ~500m of center
                # ~0.005 degrees is roughly 500m at this latitude
                lat_offset = random.uniform(-0.005, 0.005)
                lon_offset = random.uniform(-0.005, 0.005)

                latitude = center_lat + lat_offset
                longitude = center_lon + lon_offset

                name = f"{first_names[i]} {last_names[i]}"
                # Generate unique test phone numbers with timestamp to avoid conflicts
                import time
                phone = f"+4670{int(time.time()) % 1000000:06d}{i:01d}"

                # Just regular people in the area, not responders or victims
                role = "Victim"  # Default role for regular people
                status = "Safe"  # All are safe, just in the area

                # Check if person with this name already exists
                cur.execute(
                    'SELECT id FROM "user" WHERE name = %s',
                    (name,)
                )
                existing = cur.fetchone()

                if not existing:
                    user_id = str(uuid.uuid4())
                    try:
                        cur.execute(
                            """
                            INSERT INTO "user" (id, name, phone, role, status, location, latitude, longitude, last_location_update, has_real_number)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                user_id,
                                name,
                                phone,
                                role,
                                status,
                                "Near Stora Sjöfallet National Park",
                                latitude,
                                longitude,
                                datetime.now(),
                                False,  # Test/dummy phone numbers for random people
                            ),
                        )
                    except Exception as e:
                        print(f"⚠️  Skipping {name}: {e}")
                        continue

                    distance = calculate_distance(
                        center_lat, center_lon, latitude, longitude
                    )
                    print(
                        f"👤 Added person: {name} ({distance*1000:.0f}m from location center)"
                    )
                else:
                    print(f"⚠️  Person {name} already exists, skipping")

            conn.commit()


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers"""
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


def show_scenario_summary():
    """Display a summary of the scenario setup"""
    print("\n" + "=" * 60)
    print("EPIPEN SCENARIO SUMMARY")
    print("=" * 60)

    with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Count EPIPEN holders
            cur.execute(
                """
                SELECT COUNT(DISTINCT u.id) as count
                FROM "user" u
                JOIN user_specialty us ON u.id = us.user_id
                JOIN specialty s ON us.specialty_id = s.id
                WHERE s.name = 'EPIPEN_HOLDER'
                AND u.status = 'Active'
                """
            )
            epipen_count = cur.fetchone()["count"]

            # Get hospital info
            cur.execute(
                "SELECT name, location, latitude, longitude FROM resource WHERE name = 'Gällivare Hospital'"
            )
            hospital = cur.fetchone()

            # Emergency location
            emergency_lat = 67.83938120422421
            emergency_lon = 20.202353143851322

            print(f"\n📍 Emergency Location: {emergency_lat:.6f}, {emergency_lon:.6f}")
            print("   (Near Gällivare Ski Resort)")

            if hospital:
                hospital_distance = calculate_distance(
                    emergency_lat,
                    emergency_lon,
                    hospital["latitude"],
                    hospital["longitude"],
                )
                print(f"\n🏥 Hospital: {hospital['name']}")
                print(f"   Distance from emergency: {hospital_distance:.1f}km")

            print(f"\n💉 EPIPEN HOLDERS: {epipen_count}")

            # List EPIPEN holders with distances
            cur.execute(
                """
                SELECT u.name, u.latitude, u.longitude, u.location
                FROM "user" u
                JOIN user_specialty us ON u.id = us.user_id
                JOIN specialty s ON us.specialty_id = s.id
                WHERE s.name = 'EPIPEN_HOLDER'
                AND u.status = 'Active'
                ORDER BY u.name
                """
            )
            holders = cur.fetchall()

            for holder in holders:
                if holder["latitude"] and holder["longitude"]:
                    distance = calculate_distance(
                        emergency_lat,
                        emergency_lon,
                        holder["latitude"],
                        holder["longitude"],
                    )
                    print(f"   - {holder['name']}: {distance:.1f}km away")

            # Count people near the park
            cur.execute(
                """
                SELECT COUNT(*) as total
                FROM "user"
                WHERE location = 'Near Stora Sjöfallet National Park'
                """
            )
            people = cur.fetchone()

            print(f"\n👥 People near Stora Sjöfallet National Park: {people['total']}")
            print("   (Regular people in the area, not involved in emergency)")

    print("\n" + "=" * 60)
    print("SCENARIO READY FOR TESTING")
    print("=" * 60)
    print("\nTo test:")
    print("1. Send SMS: 'Emergency! Severe allergic reaction, need EpiPen urgently!'")
    print("   Include location for best results: 'at [location name]'")
    print("2. The system should find and alert the 4 EPIPEN holders")
    print("3. Gällivare Hospital is available as a resource")
    print("\nEpiPen holders are distributed across Northern Sweden:")
    print("- 2 near Stora Sjöfallet/Ritsem (Hanyu, Hanxuan)")
    print("- 2 near Jokkmokk/Vuollerim (Jonathan, Julius)")


def main():
    print("=" * 60)
    print("SETTING UP EPIPEN ALLERGY SCENARIO")
    print("=" * 60)

    # Step 1: Add EPIPEN_HOLDER specialty
    print("\n1. Adding EPIPEN_HOLDER specialty...")
    epipen_specialty_id = add_epipen_specialty()

    # Step 2: Add Gällivare Hospital
    # print("\n2. Adding Gällivare Hospital...")
    add_gallivare_hospital()

    # Step 3: Add EPIPEN responders
    print("\n3. Adding EPIPEN responders...")
    add_epipen_responders(epipen_specialty_id)

    # Step 4: Add people near emergency location
    print("\n4. Adding people near emergency location...")
    add_nearby_people()

    # Step 5: Show summary
    show_scenario_summary()


if __name__ == "__main__":
    main()
