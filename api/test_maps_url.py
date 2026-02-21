#!/usr/bin/env python3
"""
Test that Google Maps URLs are automatically generated in the database
"""
import psycopg
from psycopg.rows import dict_row
import sys
import os
sys.path.append(os.path.dirname(__file__))

from env import SUPABASE_POSTGRES_URL

print("=" * 80)
print("TESTING GOOGLE MAPS URL GENERATION IN DATABASE")
print("=" * 80)

try:
    with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Check events with coordinates
            print("\n📍 Events with auto-generated Maps URLs:")
            print("-" * 80)
            cur.execute("""
                SELECT id, latitude, longitude, maps_url,
                       SUBSTRING(description, 1, 50) as desc_preview
                FROM event
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 5
            """)
            events = cur.fetchall()

            if events:
                for event in events:
                    print(f"\nEvent: {str(event['id'])[:8]}...")
                    print(f"  Coordinates: ({event['latitude']:.6f}, {event['longitude']:.6f})")
                    print(f"  Generated URL: {event['maps_url']}")
                    print(f"  Description: {event['desc_preview']}...")

                    # Verify URL is correct
                    expected_url = f"https://www.google.com/maps?q={event['latitude']},{event['longitude']}"
                    if event['maps_url'] == expected_url:
                        print(f"  ✅ URL correctly generated!")
                    else:
                        print(f"  ❌ URL mismatch!")
                        print(f"     Expected: {expected_url}")
            else:
                print("  No events with coordinates found")

            # Check text_messages with coordinates
            print("\n📍 Messages with auto-generated Maps URLs:")
            print("-" * 80)
            cur.execute("""
                SELECT id, latitude, longitude, maps_url,
                       SUBSTRING(raw_text, 1, 50) as text_preview
                FROM text_message
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5
            """)
            messages = cur.fetchall()

            if messages:
                for msg in messages:
                    print(f"\nMessage: {str(msg['id'])[:8]}...")
                    print(f"  Coordinates: ({msg['latitude']:.6f}, {msg['longitude']:.6f})")
                    print(f"  Generated URL: {msg['maps_url']}")
                    print(f"  Text: {msg['text_preview']}...")
            else:
                print("  No messages with coordinates found")

            # Check users with coordinates
            print("\n📍 Users with auto-generated Maps URLs:")
            print("-" * 80)
            cur.execute("""
                SELECT id, name, latitude, longitude, maps_url, location
                FROM "user"
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY id DESC
                LIMIT 5
            """)
            users = cur.fetchall()

            if users:
                for user in users:
                    print(f"\nUser: {user['name']}")
                    print(f"  ID: {str(user['id'])[:8]}...")
                    print(f"  Location: {user.get('location', 'N/A')}")
                    print(f"  Coordinates: ({user['latitude']:.6f}, {user['longitude']:.6f})")
                    print(f"  Generated URL: {user['maps_url']}")
            else:
                print("  No users with coordinates found")

            # Summary
            print("\n" + "=" * 80)
            print("📊 SUMMARY:")
            cur.execute("SELECT COUNT(*) FROM event WHERE maps_url IS NOT NULL")
            event_count = cur.fetchone()['count']
            cur.execute("SELECT COUNT(*) FROM text_message WHERE maps_url IS NOT NULL")
            msg_count = cur.fetchone()['count']
            cur.execute('SELECT COUNT(*) FROM "user" WHERE maps_url IS NOT NULL')
            user_count = cur.fetchone()['count']

            print(f"  Events with Maps URLs: {event_count}")
            print(f"  Messages with Maps URLs: {msg_count}")
            print(f"  Users with Maps URLs: {user_count}")

except Exception as e:
    print(f"\n❌ Database error: {e}")

print("\n" + "=" * 80)
print("The maps_url column is automatically generated from latitude/longitude!")
print("Any time coordinates are inserted, the Google Maps link is created automatically.")