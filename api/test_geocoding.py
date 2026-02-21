#!/usr/bin/env python3
"""
Test geocoding functionality
"""
import requests
import json

# Test locations with different levels of specificity
test_messages = [
    {
        "message": "I'm John Smith, SSN 123-45-6789, I'm at 1600 Amphitheatre Parkway, Mountain View, CA, my car broke down",
        "expected_location": "Mountain View, CA (Google HQ)"
    },
    {
        "message": "My name is Jane Doe, SSN 987-65-4321, at Pike Place Market in Seattle, I'm injured",
        "expected_location": "Pike Place Market, Seattle"
    },
    {
        "message": "Bob Johnson, SSN 456-78-9012, Highway 95 near mile marker 42 outside Las Vegas, out of fuel",
        "expected_location": "Highway 95 near Las Vegas"
    },
    {
        "message": "Alice Williams, SSN 111-22-3333, Times Square New York, there's been an accident",
        "expected_location": "Times Square, NYC"
    }
]

print("=" * 80)
print("TESTING GEOCODING FUNCTIONALITY")
print("=" * 80)

for i, test in enumerate(test_messages, 1):
    print(f"\n📍 Test {i}: {test['expected_location']}")
    print("-" * 40)

    response = requests.post(
        "http://localhost:8000/chat",
        json={
            "message": test["message"],
            "conversation_history": [],
            "user_id": f"test-geocoding-{i}"
        }
    )

    if response.ok:
        data = response.json()

        print(f"Message: {test['message'][:60]}...")

        if data.get('extracted_info'):
            info = data['extracted_info']
            print(f"Extracted location: {info.get('location')}")

            if info.get('latitude') and info.get('longitude'):
                print(f"✅ Coordinates: {info['latitude']:.6f}, {info['longitude']:.6f}")

                # Show Google Maps link
                maps_url = f"https://www.google.com/maps?q={info['latitude']},{info['longitude']}"
                print(f"📍 View on map: {maps_url}")
            else:
                print("❌ No coordinates extracted")

        if data.get('case_id'):
            print(f"✅ Case created: {data['case_id'][:8]}...")
    else:
        print(f"❌ Request failed: {response.status_code}")

print("\n" + "=" * 80)
print("To view all created cases with coordinates:")
print("python3 /Users/elundberg/fritid/hack-europe/api/view_database.py")