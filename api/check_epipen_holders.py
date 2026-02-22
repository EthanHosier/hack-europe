#!/usr/bin/env python3
"""
Check what EPIPEN holders are in the database
"""

import psycopg
from psycopg.rows import dict_row
from env import SUPABASE_POSTGRES_URL

def check_epipen_holders():
    """Check EPIPEN holders in database"""

    with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Check if EPIPEN_HOLDER specialty exists
            cur.execute("SELECT * FROM specialty WHERE name = 'EPIPEN_HOLDER'")
            specialty = cur.fetchone()

            if not specialty:
                print("❌ EPIPEN_HOLDER specialty does not exist!")
                return

            print(f"✅ EPIPEN_HOLDER specialty exists with ID: {specialty['id']}")

            # Check users with EPIPEN_HOLDER specialty
            cur.execute("""
                SELECT u.*, array_agg(s.name) as specialties
                FROM "user" u
                JOIN user_specialty us ON u.id = us.user_id
                JOIN specialty s ON us.specialty_id = s.id
                WHERE s.name = 'EPIPEN_HOLDER'
                GROUP BY u.id
            """)

            holders = cur.fetchall()

            print(f"\n📋 Found {len(holders)} EPIPEN holders:")
            for h in holders:
                print(f"\n  Name: {h['name']}")
                print(f"  Phone: {h['phone']}")
                print(f"  Location: {h.get('location', 'Unknown')}")
                print(f"  Lat/Lon: {h.get('latitude', 'None')}, {h.get('longitude', 'None')}")
                print(f"  Has Real Number: {h.get('has_real_number', False)}")
                print(f"  Status: {h['status']}")
                print(f"  Role: {h['role']}")
                print(f"  Specialties: {', '.join(h['specialties'])}")

            # Check all active responders
            print("\n\n📋 All active responders:")
            cur.execute("""
                SELECT u.name, u.phone, u.has_real_number, u.latitude, u.longitude,
                       array_agg(s.name) as specialties
                FROM "user" u
                LEFT JOIN user_specialty us ON u.id = us.user_id
                LEFT JOIN specialty s ON us.specialty_id = s.id
                WHERE u.role = 'Responder' AND u.status = 'Active'
                GROUP BY u.id
            """)

            all_responders = cur.fetchall()
            for r in all_responders:
                print(f"\n  {r['name']}: {r['phone']}")
                print(f"    Real number: {r.get('has_real_number', False)}")
                print(f"    Location: {r.get('latitude', 'None')}, {r.get('longitude', 'None')}")
                print(f"    Specialties: {', '.join(r['specialties']) if r['specialties'][0] else 'None'}")

if __name__ == "__main__":
    check_epipen_holders()