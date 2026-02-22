#!/usr/bin/env python3
"""
Clear all data from the Supabase database tables.
WARNING: This will permanently delete all data!

Usage:
    python clear_database.py        # Interactive mode with confirmation
    python clear_database.py --force # Skip confirmation (use with caution)
"""

import sys
import psycopg
from psycopg.rows import dict_row
from env import SUPABASE_POSTGRES_URL
from datetime import datetime


def clear_all_tables(conn):
    """Clear all tables in the correct order to respect foreign key constraints"""

    with conn.cursor() as cur:
        # Get counts before deletion
        cur.execute("SELECT COUNT(*) as count FROM text_message")
        text_message_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM event")
        event_count = cur.fetchone()["count"]

        cur.execute('SELECT COUNT(*) as count FROM "case"')
        case_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM resource")
        resource_count = cur.fetchone()["count"]

        cur.execute('SELECT COUNT(*) as count FROM "user"')
        user_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM user_specialty")
        user_specialty_count = cur.fetchone()["count"]

        cur.execute("SELECT COUNT(*) as count FROM responder_assignment")
        responder_assignment_count = cur.fetchone()["count"]

        print(f"\nCurrent data in database:")
        print(f"  - Users: {user_count}")
        print(f"  - Cases: {case_count}")
        print(f"  - Events: {event_count}")
        print(f"  - Text messages: {text_message_count}")
        print(f"  - Resources: {resource_count}")
        print(f"  - User specialties: {user_specialty_count}")
        print(f"  - Responder assignments: {responder_assignment_count}")

        total_count = (
            case_count
            + event_count
            + text_message_count
            + resource_count
            + user_count
            + user_specialty_count
            + responder_assignment_count
        )

        if total_count == 0:
            print("\n✅ Database is already empty!")
            return False

        print("\nDeleting data in order...")

        # Delete in order of dependencies (children first, then parents)

        # 1. Delete responder assignments (depends on case and user)
        cur.execute("DELETE FROM responder_assignment")
        print(f"  ✓ Deleted {cur.rowcount} responder assignments")

        # 2. Delete events (depends on case)
        cur.execute("DELETE FROM event")
        print(f"  ✓ Deleted {cur.rowcount} events")

        # 3. Delete text messages
        cur.execute("DELETE FROM text_message")
        print(f"  ✓ Deleted {cur.rowcount} text messages")

        # 4. Delete cases
        cur.execute('DELETE FROM "case"')
        print(f"  ✓ Deleted {cur.rowcount} cases")

        # 5. Delete user specialties (depends on user and specialty)
        cur.execute("DELETE FROM user_specialty")
        print(f"  ✓ Deleted {cur.rowcount} user specialties")

        # 6. Delete users
        cur.execute('DELETE FROM "user"')
        print(f"  ✓ Deleted {cur.rowcount} users")

        # 7. Delete resources (independent)
        cur.execute("DELETE FROM resource")
        # cur.execute("DELETE FROM specialty")
        print(f"  ✓ Deleted {cur.rowcount} resources")

        # Commit the transaction
        conn.commit()

        print("\n✅ All data cleared successfully!")
        return True


def main():
    """Main function with confirmation prompt"""

    print("=" * 50)
    print("DATABASE CLEAR UTILITY")
    print("=" * 50)
    print("\n⚠️  WARNING: This will permanently delete ALL data from your database!")
    print("This includes: cases, events, text messages, and resources.")

    # Check for --force flag
    force = "--force" in sys.argv

    if not force:
        print(
            "\nDatabase URL:",
            (
                SUPABASE_POSTGRES_URL.split("@")[1].split("/")[0]
                if "@" in SUPABASE_POSTGRES_URL
                else "Unknown"
            ),
        )
        confirmation = input(
            "\nAre you sure you want to continue? Type 'YES' to confirm: "
        )

        if confirmation != "YES":
            print("\n❌ Operation cancelled. No data was deleted.")
            sys.exit(0)
    else:
        print("\n--force flag detected, skipping confirmation...")

    try:
        print("\nConnecting to database...")
        with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
            cleared = clear_all_tables(conn)

            if cleared:
                print(f"\nDatabase cleared at: {datetime.now().isoformat()}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def verify_empty(conn):
    """Verify that all tables are empty"""
    with conn.cursor() as cur:
        tables = [
            "text_message",
            "event",
            '"case"',
            "resource",
            '"user"',
            "user_specialty",
            "responder_assignment",
        ]
        all_empty = True

        print("\nVerifying tables are empty:")
        for table in tables:
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cur.fetchone()["count"]
            status = "✓ Empty" if count == 0 else f"✗ {count} records"
            print(f"  - {table.replace('"', '')}: {status}")
            if count > 0:
                all_empty = False

        return all_empty


if __name__ == "__main__":
    # Add help flag
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    # Add a verify-only mode
    if "--verify" in sys.argv:
        print("Checking if database is empty...")
        try:
            with psycopg.connect(SUPABASE_POSTGRES_URL, row_factory=dict_row) as conn:
                is_empty = verify_empty(conn)
                if is_empty:
                    print("\n✅ Database is empty")
                else:
                    print("\n⚠️  Database contains data")
                sys.exit(0 if is_empty else 1)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)

    main()
