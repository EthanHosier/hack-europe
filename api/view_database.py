#!/usr/bin/env python3
"""
View all cases, events, and messages in the database
"""
import requests
import json
from datetime import datetime

def format_datetime(dt_str):
    """Format datetime string for display"""
    if dt_str:
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return dt_str
    return "N/A"

print("=" * 80)
print("EMERGENCY RESPONSE DATABASE VIEWER")
print("=" * 80)

# Get all data
response = requests.get("http://localhost:8000/debug/all")

if response.ok:
    data = response.json()

    # Show statistics
    print("\n📊 STATISTICS:")
    print("-" * 40)
    for key, value in data['stats'].items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    # Show cases
    print("\n🚨 EMERGENCY CASES:")
    print("-" * 40)
    if data['cases']:
        for case in data['cases']:
            print(f"\nCase ID: {case['id'][:8]}...")
            print(f"Title: {case.get('title', 'N/A')}")
            print(f"Category: {case.get('category', 'N/A')}")
            print(f"Severity: {case.get('severity', 'N/A')}/5")
            print(f"Status: {case.get('status', 'N/A')}")
            print(f"Summary: {case.get('summary', 'N/A')}")
            print(f"Created: {format_datetime(case.get('created_at'))}")
            print("-" * 40)
    else:
        print("No cases found")

    # Show recent events
    print("\n📝 RECENT EVENTS (Last 10):")
    print("-" * 40)
    if data['events']:
        for event in data['events'][:10]:
            print(f"\nEvent ID: {event['id'][:8]}...")
            print(f"Case ID: {event.get('case_id', 'N/A')[:8] if event.get('case_id') else 'N/A'}...")
            print(f"Time: {format_datetime(event.get('timestamp'))}")
            if event.get('maps_url'):
                print(f"📍 Location: {event.get('latitude', 0):.6f}, {event.get('longitude', 0):.6f}")
                print(f"📍 Map: {event['maps_url']}")
            print(f"Description: {event.get('description', 'N/A')[:100]}...")
            print("-" * 40)
    else:
        print("No events found")

    # Show recent messages
    print("\n💬 RECENT MESSAGES (Last 10):")
    print("-" * 40)
    if data['text_messages']:
        for msg in data['text_messages'][:10]:
            print(f"\nMessage ID: {msg['id'][:8]}...")
            print(f"Source: {msg.get('source', 'N/A')}")
            print(f"Target: {msg.get('target', 'N/A')}")
            if msg.get('maps_url'):
                print(f"📍 Coordinates: {msg.get('latitude', 0):.6f}, {msg.get('longitude', 0):.6f}")
                print(f"📍 Map: {msg['maps_url']}")
            print(f"Text: {msg.get('raw_text', 'N/A')[:100]}...")
            print(f"Created: {format_datetime(msg.get('created_at'))}")
            print("-" * 40)
    else:
        print("No messages found")

else:
    print(f"❌ Failed to get data: {response.status_code}")
    print(response.text)