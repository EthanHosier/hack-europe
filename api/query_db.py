#!/usr/bin/env python3
"""
Direct SQL queries to view database content
"""
import psycopg
from psycopg.rows import dict_row
from datetime import datetime
import os
import sys
sys.path.append(os.path.dirname(__file__))

from env import SUPABASE_POSTGRES_URL

def format_datetime(dt):
    """Format datetime for display"""
    if dt:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return "N/A"

print("=" * 80)
print("DIRECT DATABASE QUERY")
print("=" * 80)

try:
    with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Count records
            cur.execute('SELECT COUNT(*) as count FROM "case"')
            case_count = cur.fetchone()['count']

            cur.execute('SELECT COUNT(*) as count FROM event')
            event_count = cur.fetchone()['count']

            cur.execute('SELECT COUNT(*) as count FROM text_message')
            msg_count = cur.fetchone()['count']

            print(f"\n📊 Total Records:")
            print(f"  Cases: {case_count}")
            print(f"  Events: {event_count}")
            print(f"  Messages: {msg_count}")

            # Show recent cases
            print("\n🚨 Recent Emergency Cases:")
            print("-" * 80)
            cur.execute("""
                SELECT id, title, category, severity, status, summary, created_at
                FROM "case"
                ORDER BY created_at DESC
                LIMIT 5
            """)
            cases = cur.fetchall()

            if cases:
                for case in cases:
                    print(f"\nCase: {str(case['id'])[:8]}...")
                    print(f"  Title: {case['title']}")
                    print(f"  Category: {case['category']} | Severity: {case['severity']}/5 | Status: {case['status']}")
                    print(f"  Summary: {case['summary'][:100]}..." if case['summary'] else "  Summary: N/A")
                    print(f"  Created: {format_datetime(case['created_at'])}")
            else:
                print("  No cases found")

            # Show recent events with case info
            print("\n📝 Recent Events (with Case Info):")
            print("-" * 80)
            cur.execute("""
                SELECT e.id, e.case_id, e.timestamp, e.description, e.latitude, e.longitude, e.maps_url,
                       c.title as case_title, c.category
                FROM event e
                LEFT JOIN "case" c ON e.case_id = c.id
                ORDER BY e.timestamp DESC
                LIMIT 10
            """)
            events = cur.fetchall()

            if events:
                for event in events:
                    print(f"\nEvent: {str(event['id'])[:8]}...")
                    if event['case_id']:
                        print(f"  Case: {event['case_title']} ({event['category']})")
                    print(f"  Time: {format_datetime(event['timestamp'])}")
                    if event.get('maps_url'):
                        print(f"  📍 Location: {event['latitude']:.6f}, {event['longitude']:.6f}")
                        print(f"  📍 Map: {event['maps_url']}")
                    desc = event['description'] or "N/A"
                    if len(desc) > 150:
                        desc = desc[:150] + "..."
                    print(f"  Description: {desc}")
            else:
                print("  No events found")

except Exception as e:
    print(f"\n❌ Database connection error: {e}")
    print("\nMake sure the backend is running and database is accessible")