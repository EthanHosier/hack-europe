#!/usr/bin/env python3
"""
Seed the database with test responders/helpers who can be contacted in emergencies.
"""

import psycopg
from psycopg.rows import dict_row
from env import SUPABASE_POSTGRES_URL
from datetime import datetime
import uuid


def seed_responders():
    """Add test responders to the database"""

    responders = [
        {
            "name": "Dr. Sarah Johnson",
            "phone": "+46701234567",  # Test number
            "role": "Responder",
            "status": "Active",
            "location": "Stockholm Central",
            "latitude": 59.3326,
            "longitude": 18.0649,
            "specialties": ["Doctor", "EMT"],
            "has_real_number": False
        },
        {
            "name": "Erik Andersson",
            "phone": "+46702345678",  # Test number
            "role": "Responder",
            "status": "Active",
            "location": "Östermalm",
            "latitude": 59.3389,
            "longitude": 18.0803,
            "specialties": ["Nurse", "Mental Health"],
            "has_real_number": False
        },
        {
            "name": "Maria Lindberg",
            "phone": "+46703456789",  # Test number
            "role": "Responder",
            "status": "Active",
            "location": "Södermalm",
            "latitude": 59.3203,
            "longitude": 18.0660,
            "specialties": ["Firefighter", "Search & Rescue"],
            "has_real_number": False
        },
        {
            "name": "Johan Svensson",
            "phone": "+46704567890",  # Test number
            "role": "Responder",
            "status": "Active",
            "location": "Gamla Stan",
            "latitude": 59.3252,
            "longitude": 18.0711,
            "specialties": ["Police", "Translator"],
            "has_real_number": False
        },
        {
            "name": "Anna Bergström",
            "phone": "+46705678901",  # Test number
            "role": "Responder",
            "status": "Active",
            "location": "Vasastan",
            "latitude": 59.3456,
            "longitude": 18.0524,
            "specialties": ["EMT", "Nurse"],
            "has_real_number": False
        }
    ]

    with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Get specialty IDs
            cur.execute("SELECT id, name FROM specialty")
            specialties = {s["name"]: s["id"] for s in cur.fetchall()}

            for responder in responders:
                # Check if user already exists
                cur.execute(
                    'SELECT id FROM "user" WHERE phone = %s',
                    (responder["phone"],)
                )
                existing = cur.fetchone()

                if existing:
                    user_id = existing["id"]
                    # Update existing user
                    cur.execute(
                        """
                        UPDATE "user"
                        SET name = %s, role = %s, status = %s, location = %s,
                            latitude = %s, longitude = %s, last_location_update = %s,
                            has_real_number = %s
                        WHERE id = %s
                        """,
                        (
                            responder["name"],
                            responder["role"],
                            responder["status"],
                            responder["location"],
                            responder["latitude"],
                            responder["longitude"],
                            datetime.now(),
                            responder.get("has_real_number", False),
                            user_id
                        )
                    )
                    print(f"Updated responder: {responder['name']} (real_number={responder.get('has_real_number', False)})")
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
                            responder["role"],
                            responder["status"],
                            responder["location"],
                            responder["latitude"],
                            responder["longitude"],
                            datetime.now(),
                            responder.get("has_real_number", False)
                        )
                    )
                    print(f"Added responder: {responder['name']} (real_number={responder.get('has_real_number', False)})")

                # Clear existing specialties
                cur.execute(
                    "DELETE FROM user_specialty WHERE user_id = %s",
                    (user_id,)
                )

                # Add user specialties
                for specialty_name in responder["specialties"]:
                    if specialty_name in specialties:
                        cur.execute(
                            """
                            INSERT INTO user_specialty (user_id, specialty_id)
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING
                            """,
                            (user_id, specialties[specialty_name])
                        )
                        print(f"  - Added specialty: {specialty_name}")

            conn.commit()
            print("\n✅ Responders seeded successfully!")

            # Show summary
            cur.execute(
                """
                SELECT COUNT(*) as count
                FROM "user"
                WHERE role = 'Responder' AND status = 'Active'
                """
            )
            count = cur.fetchone()["count"]
            print(f"\nTotal active responders: {count}")


if __name__ == "__main__":
    seed_responders()