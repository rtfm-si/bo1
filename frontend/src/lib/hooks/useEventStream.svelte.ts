/**
 * useEventStream - Reusable SSE event stream hook for Svelte 5
 *
 * Manages SSE connection lifecycle with retry logic and state tracking.
 * Extracted from meeting page for reusability across the application.
 *
 * @example
 * ```ts
 * const eventStream = useEventStream({
 *   sessionId: 'session-123',
 *   onEvent: (eventType, event) => {
 *     console.log('Received event:', eventType, event);
 *   },
 *   onError: (error) => {
 *     console.error('SSE error:', error);
 *   }
 * });
 *
 * // Start connection
 * eventStream.start();
 *
 * // Stop connection
 * eventStream.stop();
 *
 * // Check connection state
 * if (eventStream.connectionStatus === 'connected') {
 *   console.log('Connected!');
 * }
 * ```
 */

import { SSEClient } from '$lib/utils/sse';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'retrying' | 'error';

export interface UseEventStreamOptions {
	/** Session ID for the SSE stream */
	sessionId: string;

	/** Callback for handling SSE events */
	onEvent: (eventType: string, event: MessageEvent) => void;

	/** Callback for handling connection errors */
	onError?: (error: string) => void;

	/** Maximum retry attempts (default: 3) */
	maxRetries?: number;

	/** List of event types to listen for */
	eventTypes?: string[];
}

export interface EventStreamState {
	/** Current connection status */
	connectionStatus: ConnectionStatus;

	/** Current retry count */
	retryCount: number;

	/** Start the SSE connection */
	start: () => Promise<void>;

	/** Stop the SSE connection */
	stop: () => void;
}

/**
 * Default event types to listen for (can be overridden via options)
 */
const DEFAULT_EVENT_TYPES = [
	'node_start',
	'node_end',
	'session_started',
	'decomposition_started',
	'decomposition_complete',
	'persona_selection_started',
	'persona_selected',
	'persona_selection_complete',
	'subproblem_started',
	'initial_round_started',
	'contribution',
	'moderator_intervention',
	'convergence',
	'round_started',
	'voting_started',
	'persona_vote',
	'voting_complete',
	'synthesis_started',
	'synthesis_complete',
	'subproblem_complete',
	'meta_synthesis_started',
	'meta_synthesis_complete',
	'phase_cost_breakdown',
	'complete',
	'error',
	'clarification_requested',
	'working_status',
];

/**
 * Create a reusable SSE event stream with connection management
 */
export function useEventStream(options: UseEventStreamOptions): EventStreamState {
	const {
		sessionId,
		onEvent,
		onError,
		maxRetries = 3,
		eventTypes = DEFAULT_EVENT_TYPES,
	} = options;

	let sseClient = $state<SSEClient | null>(null);
	let connectionStatus = $state<ConnectionStatus>('disconnected');
	let retryCount = $state<number>(0);
	let retryTimeout = $state<ReturnType<typeof setTimeout> | null>(null);

	/**
	 * Start the SSE connection with retry logic
	 */
	async function start(): Promise<void> {
		// Close existing connection if any
		if (sseClient) {
			sseClient.close();
			sseClient = null;
		}

		// Clear any pending retry timeout
		if (retryTimeout) {
			clearTimeout(retryTimeout);
			retryTimeout = null;
		}

		// Update connection state
		connectionStatus = 'connecting';

		// Build event handlers map
		const eventHandlers: Record<string, (event: MessageEvent) => void> = {};
		for (const eventType of eventTypes) {
			eventHandlers[eventType] = (event: MessageEvent) => {
				onEvent(eventType, event);
			};
		}

		// Create new SSE client with credentials support
		// Use relative URL - will be proxied by Vite dev server
		sseClient = new SSEClient(`/api/v1/sessions/${sessionId}/stream`, {
			onOpen: () => {
				console.log('[SSE] Connection established');
				retryCount = 0;
				connectionStatus = 'connected';
			},
			onError: (err) => {
				console.error('[SSE] Connection error:', err, 'retry count:', retryCount);

				// Close existing connection
				if (sseClient) {
					sseClient.close();
					sseClient = null;
				}

				if (retryCount < maxRetries) {
					retryCount = retryCount + 1;
					connectionStatus = 'retrying';

					// Exponential backoff: 1s, 2s, 4s (capped at 5s)
					const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 5000);
					console.log(`[SSE] Retrying in ${delay}ms...`);

					retryTimeout = setTimeout(() => {
						start();
					}, delay);
				} else {
					console.error('[SSE] Max retries reached');
					connectionStatus = 'error';

					const errorMessage = 'Failed to connect to session stream. Please refresh the page.';
					onError?.(errorMessage);
				}
			},
			eventHandlers,
		});

		// Start the connection
		try {
			await sseClient.connect();
		} catch (err) {
			console.error('[SSE] Failed to start connection:', err);
		}
	}

	/**
	 * Stop the SSE connection and clean up
	 */
	function stop(): void {
		// Clear any pending retry timeout
		if (retryTimeout) {
			clearTimeout(retryTimeout);
			retryTimeout = null;
		}

		// Close SSE connection
		if (sseClient) {
			sseClient.close();
			sseClient = null;
		}

		connectionStatus = 'disconnected';
		retryCount = 0;
	}

	// Return the reactive state object
	return {
		get connectionStatus() {
			return connectionStatus;
		},
		get retryCount() {
			return retryCount;
		},
		start,
		stop,
	};
}
