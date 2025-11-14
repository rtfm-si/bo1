#!/usr/bin/env python3
"""Seed personas from personas.json into PostgreSQL database."""

import json
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Add parent directory to path to import bo1 modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()


def main() -> None:
    """Seed personas into database."""
    # Load personas from JSON
    personas_file = Path(__file__).parent.parent / "bo1" / "data" / "personas.json"
    with open(personas_file) as f:
        personas = json.load(f)

    print(f"Loaded {len(personas)} personas from {personas_file}")

    # Connect to database
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    try:
        # Clear existing personas
        cursor.execute("DELETE FROM personas")
        print("Cleared existing personas")

        # Insert personas
        for persona in personas:
            cursor.execute(
                """
                INSERT INTO personas (code, name, expertise, system_prompt)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    persona["code"],
                    persona["name"],
                    persona["description"],  # "description" in JSON, "expertise" in DB
                    persona["system_prompt"],
                ),
            )

        conn.commit()
        print(f"✅ Successfully seeded {len(personas)} personas")

        # Verify
        cursor.execute("SELECT COUNT(*) FROM personas")
        count = cursor.fetchone()[0]
        print(f"Verification: {count} personas in database")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error seeding personas: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
