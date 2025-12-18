"""Tests for SSE session resume functionality.

Validates:
- Event ID format (session_id:sequence)
- Last-Event-ID parsing
- Missed event replay on reconnection
- Deduplication between replay and live events
"""

import json

from backend.api.events import (
    gap_detected_event,
    make_event_id,
    parse_event_id,
)


class TestEventIdFormat:
    """Test event ID creation and formatting."""

    def test_make_event_id_format(self):
        """Event ID has correct format."""
        event_id = make_event_id("bo1_abc123", 42)
        assert event_id == "bo1_abc123:42"

    def test_make_event_id_first_sequence(self):
        """First event has sequence 1."""
        event_id = make_event_id("bo1_session", 1)
        assert event_id == "bo1_session:1"

    def test_make_event_id_large_sequence(self):
        """Large sequence numbers work."""
        event_id = make_event_id("bo1_session", 99999)
        assert event_id == "bo1_session:99999"


class TestLastEventIdParsing:
    """Test Last-Event-ID header parsing."""

    def test_parse_valid_event_id(self):
        """Parse valid event ID."""
        result = parse_event_id("bo1_abc123:42")
        assert result == ("bo1_abc123", 42)

    def test_parse_event_id_sequence_1(self):
        """Parse event ID with sequence 1."""
        result = parse_event_id("session_id:1")
        assert result == ("session_id", 1)

    def test_parse_event_id_with_underscores(self):
        """Session IDs with underscores parse correctly."""
        result = parse_event_id("bo1_my_session_123:456")
        assert result == ("bo1_my_session_123", 456)

    def test_parse_empty_string(self):
        """Empty string returns None."""
        result = parse_event_id("")
        assert result is None

    def test_parse_none(self):
        """None returns None."""
        result = parse_event_id(None)  # type: ignore
        assert result is None

    def test_parse_no_colon(self):
        """String without colon returns None."""
        result = parse_event_id("no_colon_here")
        assert result is None

    def test_parse_invalid_sequence(self):
        """Non-numeric sequence returns None."""
        result = parse_event_id("session:abc")
        assert result is None

    def test_parse_empty_sequence(self):
        """Empty sequence returns None."""
        result = parse_event_id("session:")
        assert result is None

    def test_parse_negative_sequence(self):
        """Negative sequence is parsed (validation happens elsewhere)."""
        result = parse_event_id("session:-5")
        assert result == ("session", -5)


class TestReplayLogic:
    """Test event replay filtering logic."""

    def test_filter_events_after_sequence(self):
        """Events after resume sequence are included."""
        events = [
            {"sequence": 1, "event_type": "a"},
            {"sequence": 2, "event_type": "b"},
            {"sequence": 3, "event_type": "c"},
            {"sequence": 4, "event_type": "d"},
            {"sequence": 5, "event_type": "e"},
        ]
        resume_from = 2

        replay_events = [e for e in events if e.get("sequence", 0) > resume_from]

        assert len(replay_events) == 3
        assert replay_events[0]["sequence"] == 3
        assert replay_events[1]["sequence"] == 4
        assert replay_events[2]["sequence"] == 5

    def test_filter_events_resume_from_zero(self):
        """Resume from 0 includes all events."""
        events = [
            {"sequence": 1, "event_type": "a"},
            {"sequence": 2, "event_type": "b"},
        ]
        resume_from = 0

        replay_events = [e for e in events if e.get("sequence", 0) > resume_from]

        assert len(replay_events) == 2

    def test_filter_events_resume_past_end(self):
        """Resume past last event returns empty."""
        events = [
            {"sequence": 1, "event_type": "a"},
            {"sequence": 2, "event_type": "b"},
        ]
        resume_from = 10

        replay_events = [e for e in events if e.get("sequence", 0) > resume_from]

        assert len(replay_events) == 0


class TestDeduplication:
    """Test deduplication between replay and live events."""

    def test_dedupe_seen_sequences(self):
        """Sequences in seen_sequences are skipped."""
        seen_sequences = {3, 4, 5}
        live_events = [
            {"sequence": 4, "event_type": "duplicate"},
            {"sequence": 6, "event_type": "new"},
            {"sequence": 7, "event_type": "new"},
        ]

        new_events = [e for e in live_events if e.get("sequence", 0) not in seen_sequences]

        assert len(new_events) == 2
        assert new_events[0]["sequence"] == 6
        assert new_events[1]["sequence"] == 7

    def test_dedupe_empty_seen(self):
        """Empty seen_sequences passes all events."""
        seen_sequences: set[int] = set()
        live_events = [
            {"sequence": 1, "event_type": "a"},
            {"sequence": 2, "event_type": "b"},
        ]

        new_events = [e for e in live_events if e.get("sequence", 0) not in seen_sequences]

        assert len(new_events) == 2


class TestEventIdInjection:
    """Test SSE event ID injection into output."""

    def test_inject_event_id_into_sse(self):
        """Event ID is prepended to SSE output."""
        event_id = "bo1_abc123:42"
        sse_event = "event: test\ndata: {}\n\n"

        with_id = f"id: {event_id}\n{sse_event}"

        assert with_id.startswith("id: bo1_abc123:42")
        assert "event: test" in with_id
        assert with_id.endswith("\n\n")

    def test_sse_format_with_id(self):
        """Full SSE format with ID is valid."""
        event_id = "session:1"
        sse = f"id: {event_id}\nevent: node_start\ndata: {{}}\n\n"

        lines = sse.strip().split("\n")
        assert lines[0] == "id: session:1"
        assert lines[1] == "event: node_start"
        assert lines[2].startswith("data:")


class TestSequenceTracking:
    """Test sequence counter behavior."""

    def test_sequence_counter_increments(self):
        """Sequence counters increment per session."""
        counters: dict[str, int] = {}

        def get_next(session_id: str) -> int:
            if session_id not in counters:
                counters[session_id] = 0
            counters[session_id] += 1
            return counters[session_id]

        assert get_next("session_a") == 1
        assert get_next("session_a") == 2
        assert get_next("session_b") == 1
        assert get_next("session_a") == 3

    def test_sequence_isolated_per_session(self):
        """Different sessions have independent counters."""
        counters: dict[str, int] = {"session_a": 10, "session_b": 5}

        counters["session_a"] += 1
        counters["session_b"] += 1

        assert counters["session_a"] == 11
        assert counters["session_b"] == 6


class TestGapDetection:
    """Test SSE sequence gap detection for reconnection."""

    def test_detect_gap_at_start(self):
        """Gap detected when first replayed event > expected sequence."""
        resume_from_sequence = 5
        expected_seq = resume_from_sequence + 1  # 6

        replayed_events = [
            {"sequence": 10, "event_type": "a"},
            {"sequence": 11, "event_type": "b"},
        ]

        first_seq = replayed_events[0].get("sequence", 0)
        has_gap = first_seq > expected_seq
        missed_count = first_seq - expected_seq if has_gap else 0

        assert has_gap is True
        assert missed_count == 4  # 6, 7, 8, 9 missing

    def test_no_gap_contiguous_sequence(self):
        """No gap when sequences are contiguous."""
        resume_from_sequence = 5
        expected_seq = resume_from_sequence + 1  # 6

        replayed_events = [
            {"sequence": 6, "event_type": "a"},
            {"sequence": 7, "event_type": "b"},
        ]

        first_seq = replayed_events[0].get("sequence", 0)
        has_gap = first_seq > expected_seq

        assert has_gap is False

    def test_detect_internal_gap(self):
        """Detect gaps within the replayed event sequence."""
        replayed_events = [
            {"sequence": 6, "event_type": "a"},
            {"sequence": 7, "event_type": "b"},
            {"sequence": 10, "event_type": "c"},  # Gap: 8, 9 missing
            {"sequence": 11, "event_type": "d"},
        ]

        internal_gaps = []
        prev_seq = replayed_events[0].get("sequence", 0)

        for event in replayed_events[1:]:
            curr_seq = event.get("sequence", 0)
            if curr_seq > prev_seq + 1:
                gap_size = curr_seq - prev_seq - 1
                internal_gaps.append((prev_seq, curr_seq, gap_size))
            prev_seq = curr_seq

        assert len(internal_gaps) == 1
        assert internal_gaps[0] == (7, 10, 2)  # Gap of 2 after seq 7

    def test_no_internal_gaps(self):
        """No internal gaps when sequences are consecutive."""
        replayed_events = [
            {"sequence": 1, "event_type": "a"},
            {"sequence": 2, "event_type": "b"},
            {"sequence": 3, "event_type": "c"},
        ]

        internal_gaps = []
        prev_seq = replayed_events[0].get("sequence", 0)

        for event in replayed_events[1:]:
            curr_seq = event.get("sequence", 0)
            if curr_seq > prev_seq + 1:
                internal_gaps.append((prev_seq, curr_seq))
            prev_seq = curr_seq

        assert len(internal_gaps) == 0

    def test_empty_replay_no_gap(self):
        """No gap detection for empty replay list."""
        replayed_events: list = []
        resume_from_sequence = 5

        # With no events, can't detect a gap
        has_gap = False
        if replayed_events:
            first_seq = replayed_events[0].get("sequence", 0)
            has_gap = first_seq > resume_from_sequence + 1

        assert has_gap is False


class TestGapDetectedEvent:
    """Test gap_detected SSE event formatting."""

    def test_gap_detected_event_format(self):
        """gap_detected event has correct structure."""
        event = gap_detected_event(
            session_id="bo1_test123",
            expected_seq=6,
            actual_seq=10,
            missed_count=4,
        )

        # Parse SSE format
        lines = event.strip().split("\n")
        assert lines[0] == "event: gap_detected"
        assert lines[1].startswith("data: ")

        # Parse JSON data
        data = json.loads(lines[1][6:])  # Skip "data: "
        assert data["session_id"] == "bo1_test123"
        assert data["expected_sequence"] == 6
        assert data["actual_sequence"] == 10
        assert data["missed_count"] == 4
        assert "message" in data
        assert "timestamp" in data
        assert data["event_version"] == 1

    def test_gap_detected_event_message(self):
        """gap_detected event has user-friendly message."""
        event = gap_detected_event(
            session_id="bo1_test",
            expected_seq=1,
            actual_seq=5,
            missed_count=4,
        )

        lines = event.strip().split("\n")
        data = json.loads(lines[1][6:])

        assert "4" in data["message"]
        assert "missed" in data["message"].lower() or "event" in data["message"].lower()

    def test_gap_detected_event_single_missed(self):
        """gap_detected event handles single missed event."""
        event = gap_detected_event(
            session_id="bo1_test",
            expected_seq=5,
            actual_seq=6,
            missed_count=1,
        )

        lines = event.strip().split("\n")
        data = json.loads(lines[1][6:])

        assert data["missed_count"] == 1
