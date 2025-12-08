"""Check waitlist entries in the database."""

from bo1.state.database import db_session


def check_waitlist() -> None:
    """Query and display waitlist entries."""
    try:
        with db_session() as conn:
            with conn.cursor() as cursor:
                # Get total count
                cursor.execute("SELECT COUNT(*) as count FROM waitlist")
                result = cursor.fetchone()
                total_count = result["count"] if result else 0

                print("\n=== Waitlist Summary ===")
                print(f"Total entries: {total_count}")

                # Get count by status
                cursor.execute(
                    """
                    SELECT status, COUNT(*) as count
                    FROM waitlist
                    GROUP BY status
                    ORDER BY COUNT(*) DESC
                    """
                )
                status_counts = cursor.fetchall()

                print("\nBy status:")
                for row in status_counts:
                    print(f"  {row['status']}: {row['count']}")

                # Get recent entries (last 10)
                cursor.execute(
                    """
                    SELECT email, status, source, created_at
                    FROM waitlist
                    ORDER BY created_at DESC
                    LIMIT 10
                    """
                )
                recent = cursor.fetchall()

                if recent:
                    print(f"\nRecent entries (last {len(recent)}):")
                    for row in recent:
                        source_str = f" from {row['source']}" if row["source"] else ""
                        print(
                            f"  - {row['email']} ({row['status']}){source_str} - {row['created_at']}"
                        )
                else:
                    print("\nNo entries found.")

    except Exception as e:
        print(f"Error querying waitlist: {e}")
        raise


if __name__ == "__main__":
    check_waitlist()
