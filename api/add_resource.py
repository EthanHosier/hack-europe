#!/usr/bin/env python3
"""
Interactive script to add a single resource to the database
"""
import uuid
import psycopg
from psycopg.rows import dict_row
from geopy.geocoders import GoogleV3
from datetime import datetime
import os
import sys
sys.path.append(os.path.dirname(__file__))

from env import SUPABASE_POSTGRES_URL

# Get API key from environment
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def geocode_location(geocoder, location_text):
    """Geocode a location to get coordinates"""
    if not geocoder:
        return None, None

    try:
        location = geocoder.geocode(location_text)
        if location:
            return location.latitude, location.longitude
        else:
            print(f"  ⚠️  Could not geocode: {location_text}")
            return None, None
    except Exception as e:
        print(f"  ❌ Geocoding error: {e}")
        return None, None

def main():
    print("=" * 80)
    print("ADD EMERGENCY RESOURCE - Interactive")
    print("=" * 80)
    print("\nThis tool helps you add a new emergency resource to the database.\n")

    # Collect resource information
    print("📝 Enter resource details:\n")

    name = input("Resource name (e.g., 'Field Hospital Alpha'): ").strip()
    if not name:
        print("❌ Name is required")
        return

    location = input("Location (e.g., 'Houston Convention Center, Texas'): ").strip()
    if not location:
        print("❌ Location is required")
        return

    print("\nDescription (press Enter twice when done):")
    description_lines = []
    while True:
        line = input()
        if line:
            description_lines.append(line)
        elif description_lines:  # Empty line after some content
            break
    description = '\n'.join(description_lines)

    capacity_str = input("\nCapacity (number, or press Enter to skip): ").strip()
    capacity = None
    if capacity_str:
        try:
            capacity = int(capacity_str)
        except ValueError:
            print("⚠️  Invalid capacity, skipping")

    print("\nStatus options: Available, Full, Closed, Emergency Only")
    status = input("Status (default: Available): ").strip() or "Available"

    # Confirm details
    print("\n" + "=" * 40)
    print("📋 RESOURCE SUMMARY:")
    print(f"Name: {name}")
    print(f"Location: {location}")
    if description:
        print(f"Description: {description[:100]}..." if len(description) > 100 else f"Description: {description}")
    if capacity:
        print(f"Capacity: {capacity}")
    print(f"Status: {status}")
    print("=" * 40)

    confirm = input("\nAdd this resource to the database? (y/n): ")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return

    # Initialize geocoder
    geocoder = GoogleV3(api_key=GOOGLE_MAPS_API_KEY) if GOOGLE_MAPS_API_KEY else None

    # Geocode location
    print("\n🌍 Geocoding location...")
    lat, lng = geocode_location(geocoder, location)
    if lat and lng:
        print(f"   📍 Found coordinates: {lat:.6f}, {lng:.6f}")
    else:
        print("   ⚠️  No coordinates available (geocoding failed or API key missing)")

    # Add to database
    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                resource_id = str(uuid.uuid4())

                print("\n💾 Adding to database...")
                cur.execute(
                    """
                    INSERT INTO resource (
                        id, name, description, location,
                        latitude, longitude, capacity, status, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, maps_url
                    """,
                    (
                        resource_id,
                        name,
                        description,
                        location,
                        lat,
                        lng,
                        capacity,
                        status,
                        datetime.utcnow()
                    )
                )

                result = cur.fetchone()
                print(f"✅ Resource created with ID: {result['id'][:8]}...")

                if result.get('maps_url'):
                    print(f"🗺️  Map: {result['maps_url']}")

                # Log event
                event_id = str(uuid.uuid4())
                event_desc = f"Resource added: {name} at {location}"
                if capacity:
                    event_desc += f" (capacity: {capacity})"

                cur.execute(
                    """
                    INSERT INTO event (id, timestamp, description, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (event_id, datetime.utcnow(), event_desc, lat, lng)
                )

                conn.commit()
                print("\n✅ Successfully added resource to database!")

                # Ask if they want to add another
                another = input("\nWould you like to add another resource? (y/n): ")
                if another.lower() == 'y':
                    print("\n" + "=" * 80 + "\n")
                    main()  # Recursive call
                else:
                    print("\n💡 Tip: Run 'python3 view_resources.py' to see all resources")

    except Exception as e:
        print(f"\n❌ Database error: {e}")
        print("Make sure the database is accessible")

if __name__ == "__main__":
    main()