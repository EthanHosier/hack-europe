#!/usr/bin/env python3
"""
Simple script to send SMS messages for testing.
This bypasses the emergency system and just sends a direct message.
"""

import sys
from twilio_service import send_sms, get_twilio_client
from env import TWILIO_FROM_NUMBER
import psycopg
from psycopg.rows import dict_row
from env import SUPABASE_POSTGRES_URL


def send_direct_sms(to_number: str, message: str):
    """Send a direct SMS message"""
    try:
        print(f"📱 Sending SMS to {to_number}")
        print(f"📝 Message: {message}")
        print(f"📞 From: {TWILIO_FROM_NUMBER}")

        result = send_sms(to_number, message)

        if result.status:
            print(f"✅ SMS sent successfully!")
            print(f"   Message SID: {result.message_sid}")
            print(f"   Status: {result.status}")
        else:
            print(f"❌ Failed to send SMS")
            if result.error_message:
                print(f"   Error: {result.error_message}")

        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def find_person_by_name(name: str):
    """Find a person's phone number by name"""
    with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, phone, location, role
                FROM "user"
                WHERE LOWER(name) LIKE LOWER(%s)
                ORDER BY name
                LIMIT 5
                """,
                (f"%{name}%",)
            )
            return cur.fetchall()


def main():
    print("=" * 60)
    print("DIRECT SMS SENDER")
    print("=" * 60)

    # Check command line arguments
    if len(sys.argv) > 2:
        # Usage: python send_test_sms.py <phone_or_name> <message>
        target = sys.argv[1]
        message = " ".join(sys.argv[2:])

        # Check if target is a phone number or name
        if target.startswith("+"):
            # It's a phone number
            send_direct_sms(target, message)
        else:
            # Try to find person by name
            people = find_person_by_name(target)
            if people:
                if len(people) == 1:
                    person = people[0]
                    print(f"Found: {person['name']} ({person['phone']})")
                    send_direct_sms(person['phone'], message)
                else:
                    print("Multiple people found:")
                    for p in people:
                        print(f"  - {p['name']} ({p['phone']}) - {p.get('location', 'Unknown location')}")
                    print("\nPlease be more specific or use phone number directly")
            else:
                print(f"No person found with name containing '{target}'")
        return

    # Interactive mode
    print("\n1. Send to specific phone number")
    print("2. Find person by name")
    print("3. Send to Tomas (+447519684318)")
    print("4. List all EPIPEN holders")

    choice = input("\nChoice (1-4): ").strip()

    if choice == "1":
        phone = input("Enter phone number (e.g., +46701234567): ").strip()
        message = input("Enter message: ").strip()
        send_direct_sms(phone, message)

    elif choice == "2":
        name = input("Enter person's name (or part of it): ").strip()
        people = find_person_by_name(name)

        if not people:
            print(f"No person found with name containing '{name}'")
            return

        print("\nFound:")
        for i, p in enumerate(people, 1):
            print(f"{i}. {p['name']} ({p['phone']}) - {p.get('location', 'Unknown')}")

        if len(people) == 1:
            person = people[0]
        else:
            idx = input(f"\nSelect person (1-{len(people)}): ").strip()
            try:
                person = people[int(idx) - 1]
            except:
                print("Invalid selection")
                return

        message = input(f"Enter message for {person['name']}: ").strip()
        send_direct_sms(person['phone'], message)

    elif choice == "3":
        # Quick option for Tomas
        message = input("Enter message for Tomas: ").strip()
        send_direct_sms("+447519684318", message)

    elif choice == "4":
        # List EPIPEN holders
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.name, u.phone, u.location
                    FROM "user" u
                    JOIN user_specialty us ON u.id = us.user_id
                    JOIN specialty s ON us.specialty_id = s.id
                    WHERE s.name = 'EPIPEN_HOLDER'
                    ORDER BY u.name
                    """
                )
                holders = cur.fetchall()

                print("\n💉 EPIPEN HOLDERS:")
                for h in holders:
                    print(f"  - {h['name']}: {h['phone']} ({h.get('location', 'Unknown')})")

                if holders:
                    name = input("\nEnter name to send SMS (or press Enter to cancel): ").strip()
                    if name:
                        for h in holders:
                            if name.lower() in h['name'].lower():
                                message = input(f"Message for {h['name']}: ").strip()
                                send_direct_sms(h['phone'], message)
                                break
                        else:
                            print(f"No holder found matching '{name}'")


if __name__ == "__main__":
    print("\n⚠️  Note: International SMS restrictions may apply!")
    print("Swedish numbers (+46) may not be able to send to UK numbers (+44)")
    print("You might need a different Twilio number for international SMS.\n")

    main()