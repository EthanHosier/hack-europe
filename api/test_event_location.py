#!/usr/bin/env python3
"""
Test that events are properly storing location coordinates
"""
import requests
import json
import time

print("=" * 80)
print("TESTING EVENT LOCATION STORAGE")
print("=" * 80)

# Create a test emergency with specific location
test_message = "My name is Test User, SSN 999-88-7777, I'm at Space Needle Seattle Washington, elevator is stuck with people inside"

print("\n📍 Sending emergency with location: Space Needle Seattle")
print("-" * 40)

response = requests.post(
    "http://localhost:8000/chat",
    json={
        "message": test_message,
        "conversation_history": [],
        "user_id": f"test-event-location-{int(time.time())}"
    }
)

if response.ok:
    data = response.json()
    print(f"\n✅ Response received")

    if data.get('extracted_info'):
        info = data['extracted_info']
        print(f"\nExtracted Information:")
        print(f"  Location: {info.get('location')}")
        print(f"  Latitude: {info.get('latitude')}")
        print(f"  Longitude: {info.get('longitude')}")
        print(f"  Category: {info.get('category')}")
        print(f"  Severity: {info.get('severity')}")

    if data.get('case_id'):
        case_id = data['case_id']
        print(f"\n✅ Case created: {case_id[:8]}...")

        # Now check the database to verify event has coordinates
        print("\n" + "=" * 40)
        print("Checking database for event coordinates...")

        time.sleep(1)  # Give database time to commit

        # Get all data to check
        db_response = requests.get("http://localhost:8000/debug/all")

        if db_response.ok:
            db_data = db_response.json()

            # Find the event for this case
            events_for_case = [e for e in db_data['events'] if e.get('case_id') == case_id]

            if events_for_case:
                event = events_for_case[0]
                print(f"\n✅ Found event for case {case_id[:8]}:")
                print(f"  Event ID: {event['id'][:8]}...")

                if event.get('latitude') and event.get('longitude'):
                    print(f"  ✅ Coordinates stored in event table:")
                    print(f"     Latitude: {event['latitude']:.6f}")
                    print(f"     Longitude: {event['longitude']:.6f}")
                    print(f"  📍 View on map: https://www.google.com/maps?q={event['latitude']},{event['longitude']}")
                else:
                    print(f"  ❌ No coordinates in event table!")

                print(f"\n  Event description preview:")
                print(f"  {event.get('description')[:200]}...")
            else:
                print(f"❌ No events found for case {case_id[:8]}")
        else:
            print(f"❌ Could not fetch database data")
    else:
        print("❌ No case was created")
else:
    print(f"❌ Request failed: {response.status_code}")

print("\n" + "=" * 80)
print("To view all events with coordinates:")
print("python3 /Users/elundberg/fritid/hack-europe/api/view_database.py")