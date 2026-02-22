#!/usr/bin/env python3
"""
Test script for Tom's allergic reaction scenario at STF Vakkotavare.
This simulates the complete emergency flow.
"""

import time
import requests
from datetime import datetime


def simulate_tom_emergency():
    """Simulate Tom's allergic reaction emergency"""

    print("=" * 60)
    print("TOM'S ALLERGIC REACTION SCENARIO")
    print("=" * 60)
    print("\n📍 Location: STF Vakkotavare trail cabin, Northern Sweden")
    print("🥜 Situation: Tom ate a Snickers bar (contains peanuts)")
    print("⚠️  Tom has SEVERE peanut allergy\n")

    # Tom's initial emergency message
    tom_message = """Help! I'm Tom, I just ate a Snickers bar and I'm having a severe
allergic reaction! I'm at STF Vakkotavare trail cabin. My throat is swelling,
can't breathe properly, need EpiPen urgently! I don't have one with me!
Social security number: 900101-1234"""

    print("📱 Tom's SMS to emergency system:")
    print("-" * 40)
    print(tom_message)
    print("-" * 40)

    print("\n⏳ Simulating SMS processing...")
    time.sleep(2)

    # Expected AI response
    print("\n🤖 AI Agent Response to Tom:")
    print("-" * 40)
    ai_response = """I understand you're having a severe allergic reaction at STF Vakkotavare
trail cabin. This is a critical emergency.

✅ Emergency case created! Case ID: abc12345...
Category: medical, Severity: 5/5
📍 Location coordinates: 67.5817, 18.1004

🚨 2 nearby responders with EpiPens have been alerted!
- Hanyu Wang (1.0km away) - EPIPEN_HOLDER
- Tomas (1.1km away) - EPIPEN_HOLDER

Help is being coordinated. Stay calm and safe.
Try to remain still and keep your airway open.
If symptoms worsen, call 112 immediately."""
    print(ai_response)
    print("-" * 40)

    print("\n📨 SMS sent to EPIPEN holders...")
    time.sleep(1)

    # Responder notification
    print("\n📱 SMS to Tomas (+447519684318):")
    print("-" * 40)
    tomas_alert = """🚨 EMERGENCY ALERT

Your help is needed 1.1km away!

Situation: Severe allergic reaction to peanuts, need EpiPen urgently!
Location: STF Vakkotavare trail cabin
Maps: https://www.google.com/maps?q=67.5817,18.1004
Type: medical
Severity: 5/5

BRING YOUR EPIPEN!
Reply YES if you can respond.

Case ID: abc12345"""
    print(tomas_alert)
    print("-" * 40)

    print("\n⏳ Waiting for responder confirmation...")
    time.sleep(2)

    # Tomas responds
    print("\n💬 Tomas replies: 'YES'")
    print("\n🤖 System response to Tomas:")
    print("-" * 40)
    tomas_confirmation = """✅ Thank you Tomas!

Your response has been confirmed.

📋 Case: Medical Emergency
📝 Details: Severe allergic reaction to peanuts at STF Vakkotavare...
📍 Distance: 1.1km

⚡ Please proceed to the location safely.
The victim has been notified that help is on the way.

Reply 'ARRIVED' when you reach the scene."""
    print(tomas_confirmation)
    print("-" * 40)

    print("\n📱 Update sent to Tom:")
    print("-" * 40)
    tom_update = """Good news! Tomas (EPIPEN_HOLDER) has confirmed and is on the way!
Estimated arrival: ~5-10 minutes
Please stay calm and keep your airway clear."""
    print(tom_update)
    print("-" * 40)

    print("\n⏳ Simulating travel time...")
    time.sleep(3)

    # Tomas arrives
    print("\n💬 Tomas replies: 'ARRIVED'")
    print("\n🤖 System response to Tomas:")
    print("-" * 40)
    arrival_confirmation = """✅ Arrival confirmed, Tomas!

You are now marked as ON SCENE.

⚕️ Please provide emergency assistance as needed.
📱 Keep this line open for updates.

Thank you for your rapid response!"""
    print(arrival_confirmation)
    print("-" * 40)

    print("\n📱 Final update to Tom:")
    print("-" * 40)
    tom_final = """🎉 HELP HAS ARRIVED!
Tomas is now at your location with an EpiPen.
Emergency assistance is being provided."""
    print(tom_final)
    print("-" * 40)

    print("\n" + "=" * 60)
    print("SCENARIO COMPLETE")
    print("=" * 60)
    print("\n✅ Emergency handled successfully!")
    print("⏱️  Total response time: ~8 minutes")
    print("💉 EpiPen delivered by community responder")
    print("🏥 No hospital needed - crisis averted through P2P help")


def show_system_flow():
    """Show the technical flow of the system"""

    print("\n" + "=" * 60)
    print("TECHNICAL SYSTEM FLOW")
    print("=" * 60)

    flow = """
1. Tom sends SMS → Twilio number (+46764790215)

2. Webhook receives at /twilio/webhooks/sms
   - Stores message in database
   - Processes through AI agent (Gemini)

3. AI Agent:
   - Identifies: Allergic reaction, severity 5
   - Geocodes: STF Vakkotavare → 67.5817, 18.1004
   - Creates emergency case in database

4. Responder Notifier:
   - Searches for EPIPEN_HOLDERS within 5km
   - Finds: Hanyu (1.0km), Tomas (1.1km)
   - Sends SMS alerts via Twilio
   - Creates responder_assignment records

5. Tomas receives SMS and replies "YES"

6. Webhook recognizes responder confirmation:
   - Checks: Is sender a registered responder? ✓
   - Updates: responder_assignment status → 'confirmed'
   - Sends: Confirmation to Tomas (NOT treated as new emergency)

7. Tomas arrives and replies "ARRIVED"

8. System updates:
   - responder_assignment status → 'arrived'
   - Logs event in case history
   - Notifies all parties

Key Fix: Responders replying "YES" are NOT treated as needing help themselves!
"""
    print(flow)


def main():
    print("Tom's Allergic Reaction Scenario Test")
    print("=" * 60)
    print("\n1. Run scenario simulation")
    print("2. Show technical system flow")
    print("3. Both")

    choice = input("\nChoice (1-3): ").strip()

    if choice == "1":
        simulate_tom_emergency()
    elif choice == "2":
        show_system_flow()
    elif choice == "3":
        simulate_tom_emergency()
        show_system_flow()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()