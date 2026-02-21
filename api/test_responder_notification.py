#!/usr/bin/env python3
"""
Test script for the responder notification system.
This demonstrates finding and notifying nearby responders.
"""

import sys
from responder_notifier import find_nearby_responders, alert_nearby_help
from env import SUPABASE_POSTGRES_URL


def test_find_responders():
    """Test finding nearby responders"""

    # Test location: Near Stockholm Central (where we have responders)
    test_latitude = 59.3300  # Slightly south of Stockholm Central
    test_longitude = 18.0650

    print("=" * 60)
    print("TESTING RESPONDER FINDER")
    print("=" * 60)
    print(f"\nSearching for responders near: {test_latitude}, {test_longitude}")
    print("(Near Stockholm Central Station)")

    # Find all responders within 5km
    print("\n1. Finding ALL responders within 5km...")
    responders = find_nearby_responders(
        SUPABASE_POSTGRES_URL,
        test_latitude,
        test_longitude,
        radius_km=5.0
    )

    if responders:
        print(f"\n✅ Found {len(responders)} responders:")
        for r in responders:
            specialties = ", ".join(r.get("specialties", [])) if r.get("specialties") else "None"
            print(f"  - {r['name']} ({r['distance_km']}km away)")
            print(f"    Phone: {r['phone']}")
            print(f"    Specialties: {specialties}")
    else:
        print("❌ No responders found")

    # Find medical responders
    print("\n2. Finding MEDICAL responders within 5km...")
    medical_responders = find_nearby_responders(
        SUPABASE_POSTGRES_URL,
        test_latitude,
        test_longitude,
        radius_km=5.0,
        needed_specialties=["Doctor", "Nurse", "EMT"],
        limit=3
    )

    if medical_responders:
        print(f"\n✅ Found {len(medical_responders)} medical responders:")
        for r in medical_responders:
            specialties = ", ".join(r.get("specialties", [])) if r.get("specialties") else "None"
            print(f"  - {r['name']} ({r['distance_km']}km away)")
            print(f"    Specialties: {specialties}")
    else:
        print("❌ No medical responders found")


def test_alert_system():
    """Test the full alert system (without actually sending SMS)"""

    print("\n" + "=" * 60)
    print("TESTING ALERT SYSTEM (DRY RUN)")
    print("=" * 60)

    # Simulate an emergency
    emergency_info = {
        "emergency_description": "Person collapsed, not breathing, needs immediate medical attention",
        "location": "Stockholm Central Station, Main Hall",
        "latitude": 59.3300,
        "longitude": 18.0650,
        "category": "medical",
        "severity": 5
    }

    print("\nEmergency Details:")
    print(f"  Description: {emergency_info['emergency_description']}")
    print(f"  Location: {emergency_info['location']}")
    print(f"  Category: {emergency_info['category']}")
    print(f"  Severity: {emergency_info['severity']}/5")
    print(f"  Coordinates: {emergency_info['latitude']}, {emergency_info['longitude']}")

    print("\nFinding and alerting nearby responders...")

    # NOTE: This is a dry run - we're not actually sending SMS
    # To actually send SMS, you'd call alert_nearby_help()

    responders = find_nearby_responders(
        SUPABASE_POSTGRES_URL,
        emergency_info["latitude"],
        emergency_info["longitude"],
        radius_km=5.0,
        needed_specialties=["Doctor", "Nurse", "EMT"],
        limit=3
    )

    if responders:
        print(f"\n✅ Would notify {len(responders)} responders:")
        for r in responders:
            print(f"\n  Responder: {r['name']}")
            print(f"  Distance: {r['distance_km']}km")
            print(f"  Phone: {r['phone']}")
            print(f"  Message preview:")
            print(f"    🚨 EMERGENCY ALERT")
            print(f"    Your help is needed {r['distance_km']}km away!")
            print(f"    Situation: {emergency_info['emergency_description'][:50]}...")
            print(f"    Location: {emergency_info['location']}")
    else:
        print("\n❌ No responders found to notify")


def test_actual_notification():
    """Test with actual SMS sending (requires confirmation)"""

    print("\n" + "=" * 60)
    print("ACTUAL SMS NOTIFICATION TEST")
    print("=" * 60)
    print("\n⚠️  WARNING: This will send real SMS messages!")

    confirm = input("\nDo you want to send a TEST alert to responders? (type 'YES' to confirm): ")

    if confirm != "YES":
        print("Test cancelled.")
        return

    # Test emergency
    emergency_info = {
        "emergency_description": "TEST ALERT - This is a test of the emergency system",
        "location": "TEST LOCATION - Stockholm Central",
        "latitude": 59.3300,
        "longitude": 18.0650,
        "category": "test",
        "severity": 1
    }

    result = alert_nearby_help(
        SUPABASE_POSTGRES_URL,
        emergency_info,
        case_id="TEST123",
        radius_km=5.0,
        max_responders=1  # Only notify 1 responder for testing
    )

    print("\nNotification Results:")
    print(f"  Responders found: {result['responders_found']}")
    print(f"  SMS sent successfully: {result['notifications_sent']}")
    print(f"  SMS failed: {result['notifications_failed']}")

    if result['responders']:
        print("\nNotified responders:")
        for r in result['responders']:
            print(f"  - {r['name']} ({r['distance_km']}km away)")


if __name__ == "__main__":
    print("Responder Notification System Test")
    print("=" * 60)
    print("\nWhat would you like to test?")
    print("1. Find nearby responders")
    print("2. Test alert system (dry run - no SMS)")
    print("3. Send actual test SMS (requires confirmation)")
    print("4. Run all tests")

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == "1":
        test_find_responders()
    elif choice == "2":
        test_alert_system()
    elif choice == "3":
        test_actual_notification()
    elif choice == "4":
        test_find_responders()
        test_alert_system()
        print("\n" + "=" * 60)
        print("To test actual SMS sending, run option 3 separately")
    else:
        print("Invalid choice")