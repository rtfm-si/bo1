/**
 * Unit tests for useEventStream hook
 *
 * Tests SSE connection lifecycle, retry logic, and event handling.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Global state to capture mock callbacks
const mockState = {
  onOpen: undefined as (() => void) | undefined,
  onError: undefined as ((err: Error) => void) | undefined,
  eventHandlers: {} as Record<string, (event: MessageEvent) => void>,
  closeCalled: false,
};

// Mock must be defined before imports that use it
vi.mock('$lib/utils/sse', () => {
  return {
    SSEClient: class MockSSEClient {
      constructor(_url: string, options: {
        onOpen?: () => void;
        onError?: (err: Error) => void;
        eventHandlers?: Record<string, (event: MessageEvent) => void>;
      }) {
        mockState.onOpen = options.onOpen;
        mockState.onError = options.onError;
        mockState.eventHandlers = options.eventHandlers || {};
        mockState.closeCalled = false;
      }

      async connect(): Promise<void> {
        return Promise.resolve();
      }

      close(): void {
        mockState.closeCalled = true;
      }
    },
  };
});

// Import after mock is set up
import { useEventStream } from './useEventStream.svelte';

describe('useEventStream', () => {
  it('should initialize with disconnected status', () => {
    const eventStream = useEventStream({
      sessionId: 'test-session',
      onEvent: () => {},
    });

    expect(eventStream.connectionStatus).toBe('disconnected');
    expect(eventStream.retryCount).toBe(0);
  });

  it('should expose start and stop methods', () => {
    const eventStream = useEventStream({
      sessionId: 'test-session',
      onEvent: () => {},
    });

    expect(typeof eventStream.start).toBe('function');
    expect(typeof eventStream.stop).toBe('function');
  });

  it('should accept custom maxRetries option', () => {
    const eventStream = useEventStream({
      sessionId: 'test-session',
      onEvent: () => {},
      maxRetries: 5,
    });

    // Hook should be initialized successfully with custom maxRetries
    expect(eventStream).toBeDefined();
  });

  it('should accept custom event types', () => {
    const eventStream = useEventStream({
      sessionId: 'test-session',
      onEvent: () => {},
      eventTypes: ['custom_event', 'another_event'],
    });

    // Hook should be initialized successfully with custom event types
    expect(eventStream).toBeDefined();
  });

  it('should accept optional onError callback', () => {
    const errorCallback = (error: string) => {
      console.error('Test error:', error);
    };

    const eventStream = useEventStream({
      sessionId: 'test-session',
      onEvent: () => {},
      onError: errorCallback,
    });

    // Hook should be initialized successfully with error callback
    expect(eventStream).toBeDefined();
  });
});

describe('useEventStream connection lifecycle', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockState.onOpen = undefined;
    mockState.onError = undefined;
    mockState.eventHandlers = {};
    mockState.closeCalled = false;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('should transition to connecting when start() is called', async () => {
    const eventStream = useEventStream({
      sessionId: 'test-session',
      onEvent: () => {},
    });

    expect(eventStream.connectionStatus).toBe('disconnected');

    // Start connection (don't await - check intermediate state)
    const startPromise = eventStream.start();

    // Should be connecting
    expect(eventStream.connectionStatus).toBe('connecting');

    // Simulate successful connection
    if (mockState.onOpen) {
      mockState.onOpen();
    }

    expect(eventStream.connectionStatus).toBe('connected');
    expect(eventStream.retryCount).toBe(0);

    // Cleanup
    eventStream.stop();
  });

  it('should reset retry count on successful connection', async () => {
    const eventStream = useEventStream({
      sessionId: 'test-session',
      onEvent: () => {},
      maxRetries: 3,
    });

    // Start connection
    eventStream.start();

    // Simulate error to trigger retry
    if (mockState.onError) {
      mockState.onError(new Error('Connection failed'));
    }

    expect(eventStream.connectionStatus).toBe('retrying');
    expect(eventStream.retryCount).toBe(1);

    // Advance timer to trigger retry
    await vi.advanceTimersByTimeAsync(1000);

    // Simulate successful connection on retry
    if (mockState.onOpen) {
      mockState.onOpen();
    }

    expect(eventStream.connectionStatus).toBe('connected');
    expect(eventStream.retryCount).toBe(0);

    eventStream.stop();
  });

  it('should transition to error state after max retries', async () => {
    const onErrorMock = vi.fn();
    const eventStream = useEventStream({
      sessionId: 'test-session',
      onEvent: () => {},
      onError: onErrorMock,
      maxRetries: 2,
    });

    // Start connection
    eventStream.start();

    // First failure
    if (mockState.onError) mockState.onError(new Error('Fail 1'));
    expect(eventStream.retryCount).toBe(1);
    expect(eventStream.connectionStatus).toBe('retrying');

    // Advance and second failure
    await vi.advanceTimersByTimeAsync(1000);
    if (mockState.onError) mockState.onError(new Error('Fail 2'));
    expect(eventStream.retryCount).toBe(2);

    // Advance and third failure (exceeds maxRetries=2)
    await vi.advanceTimersByTimeAsync(2000);
    if (mockState.onError) mockState.onError(new Error('Fail 3'));

    // Should be in error state
    expect(eventStream.connectionStatus).toBe('error');
    expect(onErrorMock).toHaveBeenCalledWith(
      'Failed to connect to session stream. Please refresh the page.'
    );

    eventStream.stop();
  });

  it('should handle events through onEvent callback', async () => {
    const onEventMock = vi.fn();
    const eventStream = useEventStream({
      sessionId: 'test-session',
      onEvent: onEventMock,
      eventTypes: ['contribution', 'complete'],
    });

    // Start and connect
    eventStream.start();
    if (mockState.onOpen) mockState.onOpen();

    // Simulate an event
    const mockEvent = new MessageEvent('contribution', {
      data: JSON.stringify({ message: 'test contribution' }),
    });

    if (mockState.eventHandlers['contribution']) {
      mockState.eventHandlers['contribution'](mockEvent);
    }

    expect(onEventMock).toHaveBeenCalledWith('contribution', mockEvent);

    eventStream.stop();
  });

  it('should cleanup on stop()', async () => {
    const eventStream = useEventStream({
      sessionId: 'test-session',
      onEvent: () => {},
    });

    // Start connection
    eventStream.start();
    if (mockState.onOpen) mockState.onOpen();

    expect(eventStream.connectionStatus).toBe('connected');

    // Stop connection
    eventStream.stop();

    expect(eventStream.connectionStatus).toBe('disconnected');
    expect(eventStream.retryCount).toBe(0);
    expect(mockState.closeCalled).toBe(true);
  });

  it('should clear pending retry timeout on stop()', async () => {
    const eventStream = useEventStream({
      sessionId: 'test-session',
      onEvent: () => {},
      maxRetries: 3,
    });

    // Start connection
    eventStream.start();

    // Trigger error to start retry timer
    if (mockState.onError) mockState.onError(new Error('Connection failed'));
    expect(eventStream.connectionStatus).toBe('retrying');

    // Stop before retry happens
    eventStream.stop();

    expect(eventStream.connectionStatus).toBe('disconnected');
    expect(eventStream.retryCount).toBe(0);

    // Advance timer - should not trigger any reconnection attempts
    await vi.advanceTimersByTimeAsync(5000);
    expect(eventStream.connectionStatus).toBe('disconnected');
  });
});
