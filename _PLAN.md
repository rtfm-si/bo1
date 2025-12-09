# Plan: [REL][P1] Add Automatic Session Resume

## Summary

- Support SSE client reconnection using `Last-Event-ID` header
- Track event sequence numbers in Redis and PostgreSQL
- On reconnect, replay missed events from history before streaming new events
- Frontend can automatically resume in-progress sessions

## Implementation Steps

1. **Add sequence numbers to events** (`backend/api/events.py`)
   - Modify `format_sse_event()` to accept and include `event_id` parameter
   - Generate sequence-based IDs: `{session_id}:{sequence}`
   - Track sequence counter per session in Redis

2. **Update event publishing** (`backend/api/event_collector.py`)
   - Increment sequence counter on each event publish
   - Include `event_id` in SSE output
   - Store sequence in Redis history with each event

3. **Parse Last-Event-ID on stream connect** (`backend/api/streaming.py`)
   - Accept `Last-Event-ID` header in stream endpoint
   - Parse `session_id:sequence` format from header
   - Pass to `stream_session_events()` generator

4. **Replay missed events on reconnect** (`backend/api/streaming.py`)
   - If `Last-Event-ID` provided, fetch events from history
   - Filter events with sequence > last_seen
   - Yield missed events before subscribing to PubSub

5. **Add resume status to /events endpoint** (`backend/api/streaming.py`)
   - Return `last_event_id` in response
   - Include `can_resume: true` if session is resumable

## Tests

- Unit tests (`tests/api/test_streaming_resume.py`):
  - `test_event_id_format`
  - `test_last_event_id_parsing`
  - `test_replay_missed_events`
  - `test_resume_in_progress_session`

- Manual validation:
  - Start session, disconnect mid-stream, reconnect
  - Verify no events missed on reconnect
  - Verify duplicate events not sent

## Dependencies & Risks

- Dependencies:
  - Existing Redis event history (`events_history:{session_id}`)
  - PostgreSQL `session_events` table for fallback

- Risks/edge cases:
  - Race condition: events published during replay
  - Solution: Subscribe to PubSub first, then replay, dedupe by sequence
  - Redis history TTL may expire for long sessions
