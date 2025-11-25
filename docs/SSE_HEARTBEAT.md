# SSE Heartbeat and Stall Detection

## Overview

The SSE client (`frontend/src/lib/utils/sse.ts`) now includes automatic heartbeat/stall detection to warn users if the connection appears to have stalled.

## Features

### Stall Detection
- **Default Threshold**: 30 seconds (configurable)
- **Check Interval**: 5 seconds
- **Behavior**: Triggers `onStall` callback if no data received within threshold
- **Auto-Reset**: Warning flag resets when new data is received

### Configuration

```typescript
const client = new SSEClient('/api/v1/sessions/123/stream', {
  onOpen: () => console.log('Connected'),
  onMessage: (event) => console.log('Message:', event.data),
  onError: (error) => console.error('Error:', error),

  // Stall detection callback (optional)
  onStall: () => {
    console.warn('Connection may be stalled - no data for 30s');
    // Show UI warning to user
  },

  // Custom stall threshold (optional, default: 30000ms)
  stallDetectionInterval: 45000, // 45 seconds
});

await client.connect();
```

## Manual Testing

### Test Scenario 1: Normal Operation
1. Start a deliberation session
2. Connect SSE client
3. Verify no stall warnings during active deliberation
4. Keepalive messages from server should prevent stalls

### Test Scenario 2: Stalled Connection
1. Start a deliberation session
2. Connect SSE client
3. Simulate network issues (e.g., pause backend, block network)
4. After 30 seconds, verify `onStall` callback is triggered
5. Should see warning in browser console and/or UI

### Test Scenario 3: Recovery After Stall
1. Trigger a stall warning (wait 30s)
2. Resume network/backend
3. When new data arrives, verify warning flag is reset
4. Should not trigger multiple warnings for same stall

### Test Scenario 4: Custom Threshold
```typescript
const client = new SSEClient('/api/v1/sessions/123/stream', {
  stallDetectionInterval: 10000, // 10 seconds
  onStall: () => alert('Stalled!'),
});
```
1. Use shorter threshold (10s)
2. Verify callback triggers after 10s of no data

## Implementation Details

### State Tracking
- `lastMessageTime`: Timestamp of last received data
- `hasWarned`: Prevents duplicate warnings for same stall
- `stallCheckInterval`: Timer that checks every 5 seconds

### Cleanup
- Stall detection timer is cleared on `close()`
- Timer is stopped in `cleanup()` method
- No memory leaks from lingering timers

### Backend Compatibility
- Works with existing SSE keepalive (`:keepalive\n\n` every 15s)
- Server-side keepalives prevent false positives
- 30s threshold gives buffer beyond 15s keepalive interval

## UI Integration

Example React component:

```typescript
import { useState } from 'react';
import { SSEClient } from '$lib/utils/sse';

function DeliberationView({ sessionId }) {
  const [isStalled, setIsStalled] = useState(false);

  const connectSSE = () => {
    const client = new SSEClient(`/api/v1/sessions/${sessionId}/stream`, {
      onStall: () => {
        setIsStalled(true);
        // Show toast or banner to user
      },
      onMessage: () => {
        setIsStalled(false); // Clear warning on new data
      },
    });

    client.connect();
  };

  return (
    <div>
      {isStalled && (
        <div className="warning-banner">
          Connection may be stalled. Waiting for response...
        </div>
      )}
      {/* Rest of UI */}
    </div>
  );
}
```

## Related Audit Items

- **P2-SSE-6**: SSE heartbeat/stall detection ✅
- **P2-SSE-7**: Test SSE with non-owned session ✅
- **P2-SSE-8**: Test event history with non-owned session ✅
- **P2-SSE-9**: Test SSE with uninitialized state ✅

## Testing

Backend security tests: `tests/api/test_sse_security.py`
- Ownership validation returns 404 (not 403)
- Event history rejects non-owned sessions
- Uninitialized state handling
- Session not found scenarios

Run tests:
```bash
uv run pytest tests/api/test_sse_security.py -v
```
