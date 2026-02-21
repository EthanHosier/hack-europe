#!/usr/bin/env python3
"""
Seed the database with emergency resources (field hospitals, shelters, supply depots, etc.)
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

# Sample resources to seed - you can modify these as needed
SAMPLE_RESOURCES = [
    {
        "name": "Emergency Field Hospital Alpha",
        "location": "Riverside Park, Houston, Texas",
        "description": """Temporary emergency medical facility with comprehensive care capabilities:
- 50 beds with emergency equipment
- Surgery and ICU capabilities
- Emergency pharmacy and blood bank
- X-ray and diagnostic equipment
- Helicopter landing zone nearby
- 24/7 medical staff rotation""",
        "capacity": 50,
        "status": "Available"
    },
    {
        "name": "Red Cross Emergency Shelter",
        "location": "Phoenix Convention Center, Phoenix, Arizona",
        "description": """Large-scale emergency shelter for disaster evacuees:
- 500 person capacity
- Climate controlled environment
- Hot meals and clean water
- Basic medical station
- Children's safe area
- Pet accommodation available
- Charging stations for devices""",
        "capacity": 500,
        "status": "Available"
    },
    {
        "name": "FEMA Supply Distribution Center",
        "location": "Denver Coliseum, Colorado",
        "description": """Emergency supply distribution hub:
- Food and water supplies (7-day supply for 1000 people)
- Medical supplies and first aid kits
- Emergency blankets and clothing
- Generators and fuel
- Communication equipment
- Search and rescue gear
- Distribution trucks available""",
        "capacity": 1000,
        "status": "Available"
    },
    {
        "name": "Mobile Medical Unit - Delta Team",
        "location": "Baton Rouge, Louisiana",
        "description": """Mobile emergency response unit:
- 20 bed mobile clinic
- Emergency surgery capability
- Laboratory and pharmacy
- Water purification system
- Satellite communications
- Can deploy within 2 hours
- Self-sufficient for 72 hours""",
        "capacity": 20,
        "status": "Available"
    },
    {
        "name": "National Guard Emergency Command Post",
        "location": "Austin Convention Center, Texas",
        "description": """Emergency coordination and command center:
- Crisis management headquarters
- Communications hub with satellite uplink
- Emergency broadcast capability
- Resource coordination center
- Helicopter landing facilities
- 100 personnel capacity
- Backup power for 14 days""",
        "capacity": 100,
        "status": "Available"
    },
    {
        "name": "Emergency Water Treatment Facility",
        "location": "Lake Mead Marina, Nevada",
        "description": """Portable water treatment and distribution:
- 50,000 gallons/day purification capacity
- Mobile distribution trucks (10 units)
- Water quality testing lab
- Emergency bottled water reserves
- Can serve 10,000 people daily""",
        "capacity": 10000,
        "status": "Available"
    },
    {
        "name": "Disaster Relief Food Bank",
        "location": "Salt Lake City Fairgrounds, Utah",
        "description": """Emergency food storage and distribution:
- Non-perishable food for 5,000 people/week
- Infant formula and baby supplies
- Special dietary needs section
- Refrigerated storage available
- Loading docks for distribution
- Volunteer coordination center""",
        "capacity": 5000,
        "status": "Available"
    },
    {
        "name": "Emergency Communications Center",
        "location": "Portland Expo Center, Oregon",
        "description": """Disaster communications hub:
- HAM radio operation center
- Satellite phone bank (50 units)
- Internet via satellite
- Emergency broadcast studio
- Public information center
- Missing persons registry
- Multi-language support""",
        "capacity": 200,
        "status": "Available"
    }
]

def geocode_location(geocoder, location_text):
    """Geocode a location to get coordinates"""
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
    print("EMERGENCY RESOURCE DATABASE SEEDER")
    print("=" * 80)
    print("\nThis script will add emergency resources to the database.")
    print("You can modify SAMPLE_RESOURCES in this script to add different resources.\n")

    # Initialize geocoder
    geocoder = GoogleV3(api_key=GOOGLE_MAPS_API_KEY) if GOOGLE_MAPS_API_KEY else None

    if not geocoder:
        print("⚠️  Warning: No Google Maps API key found. Coordinates will not be available.")
        print("    Set GOOGLE_MAPS_API_KEY in your .env file for geocoding support.\n")

    try:
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Check existing resources
                cur.execute("SELECT COUNT(*) as count FROM resource")
                existing = cur.fetchone()['count']

                if existing > 0:
                    print(f"📊 Current status: {existing} resources already in database.")
                    response = input("\nDo you want to add more resources? (y/n): ")
                    if response.lower() != 'y':
                        print("Aborting seed operation.")
                        return

                print(f"\n🚀 Adding {len(SAMPLE_RESOURCES)} resources to database...\n")

                added_count = 0
                for i, resource in enumerate(SAMPLE_RESOURCES, 1):
                    print(f"{i}. Adding: {resource['name']}")
                    print(f"   Location: {resource['location']}")

                    # Geocode the location if geocoder available
                    lat, lng = None, None
                    if geocoder:
                        lat, lng = geocode_location(geocoder, resource['location'])
                        if lat and lng:
                            print(f"   📍 Coordinates: {lat:.6f}, {lng:.6f}")

                    # Insert into database
                    resource_id = str(uuid.uuid4())
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
                            resource['name'],
                            resource['description'],
                            resource['location'],
                            lat,
                            lng,
                            resource.get('capacity'),
                            resource.get('status', 'Available'),
                            datetime.utcnow()
                        )
                    )

                    result = cur.fetchone()
                    print(f"   ✅ Created with ID: {result['id'][:8]}...")

                    if result.get('maps_url'):
                        print(f"   🗺️  Map: {result['maps_url']}")

                    # Log event
                    event_id = str(uuid.uuid4())
                    event_desc = f"Resource added: {resource['name']} at {resource['location']}"

                    if resource.get('capacity'):
                        event_desc += f" (capacity: {resource['capacity']})"

                    cur.execute(
                        """
                        INSERT INTO event (id, timestamp, description, latitude, longitude)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (event_id, datetime.utcnow(), event_desc, lat, lng)
                    )

                    added_count += 1
                    print()

                conn.commit()
                print("=" * 80)
                print(f"✅ Successfully added {added_count} resources to the database!")

                # Show summary
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as with_coords,
                        COUNT(CASE WHEN status = 'Available' THEN 1 END) as available,
                        SUM(capacity) as total_capacity
                    FROM resource
                """)
                summary = cur.fetchone()

                print(f"\n📊 Database Summary:")
                print(f"   Total resources: {summary['total']}")
                print(f"   Available: {summary['available']}")
                print(f"   With GPS coordinates: {summary['with_coords']}")
                if summary['total_capacity']:
                    print(f"   Total capacity: {summary['total_capacity']:,}")

                # Group by type
                cur.execute("""
                    SELECT
                        CASE
                            WHEN LOWER(name) LIKE '%hospital%' OR LOWER(name) LIKE '%medical%' THEN 'Medical'
                            WHEN LOWER(name) LIKE '%shelter%' THEN 'Shelter'
                            WHEN LOWER(name) LIKE '%supply%' OR LOWER(name) LIKE '%food%' OR LOWER(name) LIKE '%water%' THEN 'Supplies'
                            WHEN LOWER(name) LIKE '%command%' OR LOWER(name) LIKE '%communication%' THEN 'Command/Comms'
                            ELSE 'Other'
                        END as type,
                        COUNT(*) as count
                    FROM resource
                    GROUP BY type
                    ORDER BY count DESC
                """)

                types = cur.fetchall()
                if types:
                    print(f"\n📈 Resources by Type:")
                    for t in types:
                        print(f"   {t['type']}: {t['count']}")

                print("\n💡 Tip: Run 'python3 view_resources.py' to see all resources")
                print("   Or use the API endpoint: GET /resources")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure the database is accessible and migrations are applied")

if __name__ == "__main__":
    main()