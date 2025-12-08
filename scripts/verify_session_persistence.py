#!/usr/bin/env python3
"""Verification script for PostgreSQL session persistence.

This script tests that:
1. Sessions can be saved to PostgreSQL
2. Sessions can be retrieved from PostgreSQL
3. Session status updates work correctly
4. List sessions queries work correctly
"""

import os
import sys
from datetime import UTC, datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bo1.state.repositories import session_repository


def test_session_persistence() -> None:
    """Test session persistence functionality."""
    print("=" * 80)
    print("Testing PostgreSQL Session Persistence")
    print("=" * 80)

    # Test 1: Save a new session
    print("\n[TEST 1] Saving new session to PostgreSQL...")
    test_session_id = f"bo1_test_{datetime.now(UTC).timestamp()}"
    test_user_id = "test_user_123"

    try:
        result = session_repository.create(
            session_id=test_session_id,
            user_id=test_user_id,
            problem_statement="Test problem: How to verify PostgreSQL persistence?",
            problem_context={"test": True, "priority": "high"},
            status="created",
        )
        print(f"✅ Session saved: {result['id']}")
        print(f"   Status: {result['status']}")
        print(f"   Created at: {result['created_at']}")
    except Exception as e:
        print(f"❌ FAILED to save session: {e}")
        return False

    # Test 2: Retrieve the session
    print("\n[TEST 2] Retrieving session from PostgreSQL...")
    try:
        session = session_repository.get(test_session_id)
        if session:
            print(f"✅ Session retrieved: {session['id']}")
            print(f"   Problem: {session['problem_statement'][:50]}...")
            print(f"   Context: {session['problem_context']}")
        else:
            print("❌ FAILED: Session not found")
            return False
    except Exception as e:
        print(f"❌ FAILED to retrieve session: {e}")
        return False

    # Test 3: Update session status
    print("\n[TEST 3] Updating session status...")
    try:
        updated = session_repository.update_status(
            session_id=test_session_id,
            status="running",
            phase="decomposition",
            round_number=1,
        )
        if updated:
            print("✅ Session status updated")
            # Verify the update
            session = session_repository.get(test_session_id)
            if session:
                print(f"   New status: {session['status']}")
                print(f"   Phase: {session['phase']}")
                print(f"   Round: {session['round_number']}")
        else:
            print("❌ FAILED: Session not updated")
            return False
    except Exception as e:
        print(f"❌ FAILED to update session: {e}")
        return False

    # Test 4: List user sessions
    print("\n[TEST 4] Listing user sessions...")
    try:
        sessions = session_repository.list_by_user(user_id=test_user_id, limit=10)
        print(f"✅ Found {len(sessions)} sessions for user {test_user_id}")
        for s in sessions:
            print(f"   - {s['id']}: {s['status']} (created: {s['created_at']})")
    except Exception as e:
        print(f"❌ FAILED to list sessions: {e}")
        return False

    # Test 5: Update to completed status with synthesis
    print("\n[TEST 5] Updating session to completed with synthesis...")
    try:
        updated = session_repository.update_status(
            session_id=test_session_id,
            status="completed",
            total_cost=0.42,
            synthesis_text="<synthesis>Test synthesis text</synthesis>",
        )
        if updated:
            print("✅ Session marked as completed")
            # Verify the update
            session = session_repository.get(test_session_id)
            if session:
                print(f"   Status: {session['status']}")
                print(f"   Total cost: ${session['total_cost']}")
                print(f"   Has synthesis: {bool(session['synthesis_text'])}")
        else:
            print("❌ FAILED: Session not updated to completed")
            return False
    except Exception as e:
        print(f"❌ FAILED to update session to completed: {e}")
        return False

    # Test 6: Filter sessions by status
    print("\n[TEST 6] Filtering sessions by status...")
    try:
        completed_sessions = session_repository.list_by_user(
            user_id=test_user_id, limit=10, status_filter="completed"
        )
        print(f"✅ Found {len(completed_sessions)} completed sessions")
        for s in completed_sessions:
            print(f"   - {s['id']}: ${s.get('total_cost', 0)}")
    except Exception as e:
        print(f"❌ FAILED to filter sessions: {e}")
        return False

    print("\n" + "=" * 80)
    print("✅ All tests passed! Session persistence is working correctly.")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        success = test_session_persistence()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Verification script failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
