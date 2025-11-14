#!/usr/bin/env python3
"""Redis cleanup job - removes expired data and orphaned keys.

This script should be run as a cron job (daily at 3am recommended).
It performs belt-and-suspenders cleanup even though Redis TTL handles most cases.

Usage:
    python scripts/redis_cleanup.py

Cron: 0 3 * * * cd /path/to/bo1 && python scripts/redis_cleanup.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import redis
from dotenv import load_dotenv

# Add parent directory to path to import bo1 modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()


def main() -> None:
    """Run Redis cleanup job."""
    print(f"[{datetime.now().isoformat()}] Starting Redis cleanup job...")

    # Connect to Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url)

    try:
        # Test connection
        r.ping()
        print("[OK] Connected to Redis")
    except redis.ConnectionError as e:
        print(f"[ERROR] Failed to connect to Redis: {e}")
        sys.exit(1)

    stats = {
        "sessions_checked": 0,
        "sessions_expired": 0,
        "checkpoints_checked": 0,
        "checkpoints_orphaned": 0,
        "cache_keys_checked": 0,
        "cache_keys_expired": 0,
        "ratelimit_keys_cleaned": 0,
    }

    # -------------------------------------------------------------------------
    # 1. Clean up sessions without TTL (shouldn't happen, but belt-and-suspenders)
    # -------------------------------------------------------------------------
    print("\n[1/4] Checking session keys...")
    for key in r.scan_iter("session:*"):
        stats["sessions_checked"] += 1
        ttl = r.ttl(key)

        if ttl == -1:  # No expiration set (error condition)
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            print(f"  [WARNING] Session {key_str} has no TTL, setting to 7 days")
            r.expire(key, 604800)  # 7 days
            stats["sessions_expired"] += 1

    print(f"  [OK] Checked {stats['sessions_checked']} sessions, fixed {stats['sessions_expired']}")

    # -------------------------------------------------------------------------
    # 2. Clean up orphaned checkpoints (session deleted but checkpoints remain)
    # -------------------------------------------------------------------------
    print("\n[2/4] Checking for orphaned checkpoints...")
    for key in r.scan_iter("checkpoint:*"):
        stats["checkpoints_checked"] += 1
        # Extract session_id from checkpoint:session_id:step
        key_str = key.decode("utf-8") if isinstance(key, bytes) else key
        parts = key_str.split(":")
        if len(parts) >= 2:
            session_id = parts[1]
            session_key = f"session:{session_id}"

            # Check if parent session exists
            if not r.exists(session_key):
                print(f"  [CLEANUP] Deleting orphaned checkpoint: {key_str}")
                r.delete(key)
                stats["checkpoints_orphaned"] += 1

    print(
        f"  [OK] Checked {stats['checkpoints_checked']} checkpoints, deleted {stats['checkpoints_orphaned']} orphans"
    )

    # -------------------------------------------------------------------------
    # 3. Clean up cache keys without TTL
    # -------------------------------------------------------------------------
    print("\n[3/4] Checking cache keys...")
    for key in r.scan_iter("cache:*"):
        stats["cache_keys_checked"] += 1
        ttl = r.ttl(key)

        if ttl == -1:  # No expiration set
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            print(f"  [WARNING] Cache key {key_str} has no TTL, setting to 30 days")
            r.expire(key, 2592000)  # 30 days
            stats["cache_keys_expired"] += 1

    print(
        f"  [OK] Checked {stats['cache_keys_checked']} cache keys, fixed {stats['cache_keys_expired']}"
    )

    # -------------------------------------------------------------------------
    # 4. Clean up stale rate limit keys (older than 1 day)
    # -------------------------------------------------------------------------
    print("\n[4/4] Checking rate limit keys...")
    for key in r.scan_iter("ratelimit:*"):
        ttl = r.ttl(key)

        # Rate limit keys should have short TTLs (60s to 86400s)
        # If TTL is -1 or >86400, delete it (stale)
        if ttl == -1 or ttl > 86400:
            r.delete(key)
            stats["ratelimit_keys_cleaned"] += 1

    print(f"  [OK] Cleaned up {stats['ratelimit_keys_cleaned']} stale rate limit keys")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Cleanup Summary:")
    print("=" * 60)
    print(f"Sessions checked:          {stats['sessions_checked']}")
    print(f"Sessions fixed (no TTL):   {stats['sessions_expired']}")
    print(f"Checkpoints checked:       {stats['checkpoints_checked']}")
    print(f"Orphaned checkpoints:      {stats['checkpoints_orphaned']}")
    print(f"Cache keys checked:        {stats['cache_keys_checked']}")
    print(f"Cache keys fixed:          {stats['cache_keys_expired']}")
    print(f"Rate limit keys cleaned:   {stats['ratelimit_keys_cleaned']}")
    print("=" * 60)

    # Check Redis memory usage
    info = r.info("memory")
    used_memory_mb = info["used_memory"] / (1024 * 1024)
    max_memory_mb = info.get("maxmemory", 0) / (1024 * 1024)

    print(f"\nRedis Memory Usage: {used_memory_mb:.2f} MB", end="")
    if max_memory_mb > 0:
        usage_pct = (used_memory_mb / max_memory_mb) * 100
        print(f" / {max_memory_mb:.2f} MB ({usage_pct:.1f}%)")

        if usage_pct > 80:
            print("[WARNING] Redis memory usage >80%! Consider increasing maxmemory.")
    else:
        print(" (no maxmemory limit set)")

    print(f"\n[OK] Redis cleanup completed at {datetime.now().isoformat()}\n")


if __name__ == "__main__":
    main()
