#!/usr/bin/env python3
"""
Test script specifically for the EpiPen allergy scenario.
This simulates an allergic reaction emergency and shows how the system responds.
"""

import json
import requests
from responder_notifier import find_nearby_responders, alert_nearby_help
from env import SUPABASE_POSTGRES_URL
from agent import EmergencyAgent


def test_epipen_responder_search():
    """Test finding EPIPEN holders for various locations in Northern Sweden"""

    print("=" * 60)
    print("TESTING EPIPEN RESPONDER SEARCH")
    print("=" * 60)

    test_locations = [
        {
            "name": "Gällivare Hospital",
            "lat": 67.13078211097809,
            "lon": 20.685876386471627
        },
        {
            "name": "Stora Sjöfallet National Park",
            "lat": 67.58206948569072,
            "lon": 18.100322973095093
        },
        {
            "name": "Kiruna City Center",
            "lat": 67.8557,
            "lon": 20.2253
        },
        {
            "name": "Jokkmokk",
            "lat": 66.6064,
            "lon": 19.8228
        }
    ]

    for location in test_locations:
        print(f"\n📍 Testing location: {location['name']}")
        print(f"   Coordinates: {location['lat']:.4f}, {location['lon']:.4f}")

        # Find EPIPEN holders within 100km (wider search for sparse area)
        responders = find_nearby_responders(
            SUPABASE_POSTGRES_URL,
            location["lat"],
            location["lon"],
            radius_km=100.0,
            needed_specialties=["EPIPEN_HOLDER"],
            limit=10
        )

        if responders:
            print(f"\n   Found {len(responders)} EPIPEN holders within 100km:")
            for r in responders[:5]:  # Show top 5
                print(f"   - {r['name']}: {r['distance_km']:.1f}km away")
        else:
            print("   ❌ No EPIPEN holders found within 100km")


def test_agent_allergy_response():
    """Test how the AI agent responds to allergy emergencies"""

    print("\n" + "=" * 60)
    print("TESTING AI AGENT ALLERGY RECOGNITION")
    print("=" * 60)

    agent = EmergencyAgent(SUPABASE_POSTGRES_URL)

    test_messages = [
        "Help! I'm having a severe allergic reaction to peanuts!",
        "Bee sting, throat swelling, can't breathe properly",
        "My child ate shellfish and is breaking out in hives, lips swelling",
        "Need EpiPen urgently at Stora Sjöfallet visitor center!"
    ]

    for message in test_messages:
        print(f"\n📨 Message: '{message}'")

        # Extract emergency info
        conversation = [{"role": "user", "content": message}]
        info = agent.extract_info_from_conversation(conversation)

        print(f"   Category: {info.category}")
        print(f"   Severity: {info.severity}/5")
        print(f"   Description: {info.emergency_description}")

        if info.category == "medical" and info.severity and info.severity >= 4:
            print("   ✅ Correctly identified as high-severity medical emergency")
        else:
            print("   ⚠️  Should be categorized as high-severity medical")


def simulate_emergency_scenario():
    """Simulate a complete allergic reaction emergency"""

    print("\n" + "=" * 60)
    print("SIMULATING COMPLETE ALLERGIC REACTION SCENARIO")
    print("=" * 60)

    # Emergency details
    emergency_info = {
        "emergency_description": "Severe peanut allergy reaction, anaphylactic shock, need EpiPen immediately!",
        "location": "Stora Sjöfallet National Park Visitor Center",
        "latitude": 67.58206948569072,
        "longitude": 18.100322973095093,
        "category": "medical",
        "severity": 5,
        "full_name": "Test Victim",
        "social_security_number": "000000-0000"
    }

    print("\n🚨 EMERGENCY DETAILS:")
    print(f"   Description: {emergency_info['emergency_description']}")
    print(f"   Location: {emergency_info['location']}")
    print(f"   Coordinates: {emergency_info['latitude']:.6f}, {emergency_info['longitude']:.6f}")
    print(f"   Category: {emergency_info['category']}")
    print(f"   Severity: {emergency_info['severity']}/5")

    print("\n📡 FINDING EPIPEN HOLDERS...")

    # Find nearby EPIPEN holders
    responders = find_nearby_responders(
        SUPABASE_POSTGRES_URL,
        emergency_info["latitude"],
        emergency_info["longitude"],
        radius_km=50.0,  # 50km radius for Northern Sweden
        needed_specialties=["EPIPEN_HOLDER"],
        limit=5
    )

    if responders:
        print(f"\n✅ Found {len(responders)} EPIPEN holders:")
        for r in responders:
            print(f"\n   RESPONDER: {r['name']}")
            print(f"   Distance: {r['distance_km']:.1f}km")
            print(f"   Phone: {r['phone']}")
            print(f"   Location: {r.get('location', 'Unknown')}")

            # Calculate approximate travel time (assuming 80km/h average)
            travel_time = int(r['distance_km'] / 80 * 60)
            print(f"   Est. arrival: ~{travel_time} minutes")

            # Show what SMS would be sent
            print(f"\n   SMS Preview:")
            print("   " + "-" * 40)
            print(f"   🚨 EMERGENCY ALERT")
            print(f"   Your help is needed {r['distance_km']:.1f}km away!")
            print(f"   ")
            print(f"   Situation: {emergency_info['emergency_description'][:50]}...")
            print(f"   Location: {emergency_info['location']}")
            print(f"   Maps: https://maps.google.com/?q={emergency_info['latitude']},{emergency_info['longitude']}")
            print(f"   Severity: 5/5")
            print(f"   ")
            print(f"   BRING YOUR EPIPEN!")
            print(f"   Reply YES if you can respond.")
            print("   " + "-" * 40)
    else:
        print("\n❌ No EPIPEN holders found within 50km")

    # Also check for nearest hospital
    print("\n🏥 NEAREST MEDICAL FACILITY:")
    print("   Gällivare Hospital")

    # Calculate distance to hospital
    hospital_lat = 67.13078211097809
    hospital_lon = 20.685876386471627

    from responder_notifier import calculate_distance
    hospital_distance = calculate_distance(
        emergency_info["latitude"], emergency_info["longitude"],
        hospital_lat, hospital_lon
    )

    print(f"   Distance: {hospital_distance:.1f}km")
    print(f"   Est. ambulance time: ~{int(hospital_distance / 100 * 60)} minutes")


def test_actual_sms():
    """Test sending actual SMS for allergy emergency (requires confirmation)"""

    print("\n" + "=" * 60)
    print("ACTUAL SMS TEST - ALLERGIC REACTION")
    print("=" * 60)
    print("\n⚠️  WARNING: This will send real SMS messages to EPIPEN holders!")

    confirm = input("\nSend TEST allergy alert? (type 'YES' to confirm): ")

    if confirm != "YES":
        print("Test cancelled.")
        return

    emergency_info = {
        "emergency_description": "TEST ALERT - Simulated allergic reaction for system testing",
        "location": "TEST - Stora Sjöfallet National Park",
        "latitude": 67.58206948569072,
        "longitude": 18.100322973095093,
        "category": "medical",
        "severity": 5
    }

    result = alert_nearby_help(
        SUPABASE_POSTGRES_URL,
        emergency_info,
        case_id="TEST-EPIPEN-001",
        radius_km=50.0,
        max_responders=2  # Limit to 2 for testing
    )

    print("\n📊 NOTIFICATION RESULTS:")
    print(f"   EPIPEN holders found: {result['responders_found']}")
    print(f"   SMS sent successfully: {result['notifications_sent']}")
    print(f"   SMS failed: {result['notifications_failed']}")

    if result['responders']:
        print("\n   Notified responders:")
        for r in result['responders']:
            print(f"   - {r['name']} ({r['distance_km']:.1f}km away)")


def main():
    print("=" * 60)
    print("EPIPEN ALLERGY SCENARIO TEST SUITE")
    print("=" * 60)
    print("\nWhat would you like to test?")
    print("1. Search for EPIPEN holders at various locations")
    print("2. Test AI agent allergy recognition")
    print("3. Simulate complete emergency scenario (dry run)")
    print("4. Send actual test SMS to EPIPEN holders")
    print("5. Run all tests (except actual SMS)")

    choice = input("\nEnter choice (1-5): ").strip()

    if choice == "1":
        test_epipen_responder_search()
    elif choice == "2":
        test_agent_allergy_response()
    elif choice == "3":
        simulate_emergency_scenario()
    elif choice == "4":
        test_actual_sms()
    elif choice == "5":
        test_epipen_responder_search()
        test_agent_allergy_response()
        simulate_emergency_scenario()
        print("\n" + "=" * 60)
        print("To send actual SMS alerts, run option 4 separately")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()