#!/usr/bin/env python3
"""
View all resources in the database (field hospitals, shelters, etc.)
"""
import psycopg
from psycopg.rows import dict_row
from datetime import datetime
import os
import sys
sys.path.append(os.path.dirname(__file__))

from env import SUPABASE_POSTGRES_URL

def format_datetime(dt):
    """Format datetime for display"""
    if dt:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return "N/A"

def main():
    print("=" * 80)
    print("EMERGENCY RESOURCES DATABASE")
    print("=" * 80)

    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Get all resources
                cur.execute("""
                    SELECT *
                    FROM resource
                    ORDER BY created_at DESC, name
                """)
                resources = cur.fetchall()

                if not resources:
                    print("\n❌ No resources found in database")
                    print("Run seed_field_hospitals.py to add field hospitals")
                    return

                # Group by type
                field_hospitals = [r for r in resources if 'hospital' in r['name'].lower() or 'medical' in r['name'].lower()]
                other_resources = [r for r in resources if r not in field_hospitals]

                # Display field hospitals
                if field_hospitals:
                    print("\n🏥 FIELD HOSPITALS & MEDICAL FACILITIES")
                    print("-" * 80)

                    for hospital in field_hospitals:
                        print(f"\n📍 {hospital['name']}")
                        print(f"   ID: {str(hospital['id'])[:8]}...")
                        print(f"   Location: {hospital['location']}")

                        if hospital.get('latitude') and hospital.get('longitude'):
                            print(f"   Coordinates: {hospital['latitude']:.6f}, {hospital['longitude']:.6f}")

                        if hospital.get('maps_url'):
                            print(f"   🗺️  Map: {hospital['maps_url']}")

                        if hospital.get('capacity'):
                            print(f"   Capacity: {hospital['capacity']} beds")

                        if hospital.get('status'):
                            status_emoji = "✅" if hospital['status'] == "Available" else "⚠️"
                            print(f"   Status: {status_emoji} {hospital['status']}")

                        # Show first line of description if available
                        if hospital.get('description'):
                            first_line = hospital['description'].split('\n')[0]
                            if len(first_line) > 80:
                                first_line = first_line[:80] + "..."
                            print(f"   Info: {first_line}")

                        print(f"   Added: {format_datetime(hospital.get('created_at'))}")

                # Display other resources
                if other_resources:
                    print("\n📦 OTHER RESOURCES")
                    print("-" * 80)

                    for resource in other_resources:
                        print(f"\n• {resource['name']}")
                        print(f"  ID: {str(resource['id'])[:8]}...")
                        print(f"  Location: {resource['location']}")

                        if resource.get('maps_url'):
                            print(f"  🗺️  Map: {resource['maps_url']}")

                        if resource.get('description'):
                            # Show first 100 chars of description
                            desc_preview = resource['description'][:100]
                            if len(resource['description']) > 100:
                                desc_preview += "..."
                            print(f"  Description: {desc_preview}")

                # Summary statistics
                print("\n" + "=" * 80)
                print("📊 RESOURCE SUMMARY")
                print("-" * 40)

                # Count resources by status
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'Available' THEN 1 END) as available,
                        COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as with_location,
                        SUM(capacity) as total_capacity
                    FROM resource
                """)
                stats = cur.fetchone()

                print(f"Total resources: {stats['total']}")
                print(f"Available: {stats['available']}")
                print(f"With GPS coordinates: {stats['with_location']}")

                if stats['total_capacity']:
                    print(f"Total bed capacity: {stats['total_capacity']}")

                # Count resources by type
                cur.execute("""
                    SELECT COUNT(*) as medical_count
                    FROM resource
                    WHERE LOWER(name) LIKE '%hospital%'
                       OR LOWER(name) LIKE '%medical%'
                """)
                medical_count = cur.fetchone()['medical_count']

                if medical_count > 0:
                    print(f"🏥 Medical facilities: {medical_count}")

                # Show nearest resource to a sample location
                if stats['with_location'] > 0:
                    print("\n🎯 SAMPLE PROXIMITY CHECK")
                    print("-" * 40)
                    # Example: Find resources near Houston (29.7604, -95.3698)
                    houston_lat, houston_lng = 29.7604, -95.3698

                    cur.execute("""
                        SELECT name, location,
                               latitude, longitude,
                               SQRT(POWER(latitude - %s, 2) + POWER(longitude - %s, 2)) * 111 as approx_km
                        FROM resource
                        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                        ORDER BY approx_km
                        LIMIT 3
                    """, (houston_lat, houston_lng))

                    nearest = cur.fetchall()
                    if nearest:
                        print(f"Resources nearest to Houston, TX:")
                        for r in nearest:
                            print(f"  • {r['name']}")
                            print(f"    ~{r['approx_km']:.1f} km away")

    except Exception as e:
        print(f"\n❌ Database error: {e}")
        print("Make sure the backend is running and database is accessible")

if __name__ == "__main__":
    main()