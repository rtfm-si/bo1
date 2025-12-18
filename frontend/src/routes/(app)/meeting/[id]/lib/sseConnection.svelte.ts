/**
 * SSE Connection - Manages Server-Sent Events connection for live meeting updates
 * Handles connection lifecycle, retry logic, and event dispatching
 */

import { SSEClient } from '$lib/utils/sse';
import type { SSEEvent, SSEEventType } from '$lib/api/sse-events';
import type { SessionStore } from './sessionStore.svelte';

export interface SSEConnectionConfig {
	sessionId: string;
	store: SessionStore;
	maxRetries?: number;
	onEvent: (event: SSEEvent) => void;
	onWorkingStatus?: (phase: string | null, estimatedDuration?: string) => void;
	onSessionError?: (errorType: string, errorMessage: string) => void;
}

// Event types to listen for
const EVENT_TYPES = [
	'node_start',
	'node_end',
	'session_started',
	'decomposition_started',
	'decomposition_complete',
	'persona_selection_started',
	'persona_selected',
	'persona_selection_complete',
	'subproblem_started',
	'subproblem_waiting', // Sub-problem waiting for dependencies
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
	'expert_summaries', // P2-004: Expert summaries event
	'subproblem_complete',
	'all_subproblems_complete',
	'meta_synthesis_started',
	'meta_synthesis_complete',
	'phase_cost_breakdown',
	'complete',
	'error',
	'clarification_requested',
	'clarification_required',
	'working_status',
	'meeting_terminating',
	'meeting_terminated',
];

// Events that clear the working status
const CLEAR_WORKING_STATUS_EVENTS = [
	'contribution',
	'convergence',
	'voting_complete',
	'synthesis_complete',
	'meta_synthesis_complete',
	'subproblem_complete',
	'meeting_terminated',
];

/**
 * Creates an SSE connection manager for a meeting session
 */
export function createSSEConnection(config: SSEConnectionConfig) {
	const { sessionId, store, maxRetries = 3, onEvent, onWorkingStatus, onSessionError } = config;

	let sseClient: SSEClient | null = null;
	let lastEventId: string | null = null;

	/**
	 * Handle incoming SSE events
	 */
	function handleSSEEvent(eventType: string, event: MessageEvent) {
		try {
			const payload = JSON.parse(event.data);

			// Handle working_status events specially
			if (eventType === 'working_status') {
				onWorkingStatus?.(payload.phase || null, payload.estimated_duration);
				console.log('[WORKING STATUS]', payload.phase, payload.estimated_duration);
				return;
			}

			// Handle error events - propagate to session error state
			if (eventType === 'error') {
				const errorType = payload.error_type || 'UnknownError';
				const errorMessage = payload.error || 'An unknown error occurred';
				console.error('[SSE] Session error event received:', { errorType, errorMessage });
				onSessionError?.(errorType, errorMessage);
				// Still dispatch as event for timeline
				const sseEvent: SSEEvent = {
					event_type: eventType,
					session_id: payload.session_id || sessionId,
					timestamp: payload.timestamp || new Date().toISOString(),
					data: payload,
				};
				onEvent(sseEvent);
				return;
			}

			// Clear working status for significant events
			if (CLEAR_WORKING_STATUS_EVENTS.includes(eventType)) {
				onWorkingStatus?.(null);
			}

			// Debug persona events
			if (eventType === 'persona_selected') {
				console.log('[EXPERT PANEL] Persona selected:', {
					persona_code: payload.persona?.code,
					persona_name: payload.persona?.name,
					order: payload.order,
					sub_problem_index: payload.sub_problem_index,
					timestamp: new Date().toISOString(),
				});
			}

			if (eventType === 'persona_selection_complete') {
				console.log('[EXPERT PANEL] Selection complete - triggering panel flush');
			}

			// Construct SSEEvent
			const sseEvent: SSEEvent = {
				event_type: eventType as SSEEventType,
				session_id: payload.session_id || sessionId,
				timestamp: payload.timestamp || new Date().toISOString(),
				data: payload,
			};

			// Dispatch to handler
			onEvent(sseEvent);

			// Update session phase
			store.updateSessionPhase(eventType, payload);
		} catch (err) {
			console.error(`Failed to parse ${eventType} event:`, err);
		}
	}

	/**
	 * Start the SSE connection
	 */
	async function connect() {
		// Preserve lastEventId from previous connection for resume
		if (sseClient) {
			lastEventId = sseClient.lastEventId;
			sseClient.close();
		}

		store.setConnectionStatus('connecting');

		// Build event handlers map
		const eventHandlers: Record<string, (event: MessageEvent) => void> = {};
		for (const eventType of EVENT_TYPES) {
			eventHandlers[eventType] = (event: MessageEvent) => handleSSEEvent(eventType, event);
		}

		// Create new SSE client with lastEventId for resume support
		sseClient = new SSEClient(`/api/v1/sessions/${sessionId}/stream`, {
			lastEventId: lastEventId || undefined,
			onOpen: () => {
				console.log('[SSE] Connection established', lastEventId ? `(resuming from ${lastEventId})` : '');
				store.setRetryCount(0);
				store.setConnectionStatus('connected');
			},
			onError: (err) => {
				console.error('[SSE] Connection error:', err, 'retry count:', store.retryCount);

				// Preserve lastEventId before closing
				if (sseClient) {
					lastEventId = sseClient.lastEventId;
				}
				sseClient?.close();

				if (store.retryCount < maxRetries) {
					store.setRetryCount(store.retryCount + 1);
					store.setConnectionStatus('retrying');
					const delay = Math.min(1000 * Math.pow(2, store.retryCount - 1), 5000);
					console.log(`[SSE] Retrying in ${delay}ms... (will resume from ${lastEventId || 'start'})`);

					setTimeout(() => {
						connect();
					}, delay);
				} else {
					console.error('[SSE] Max retries reached');
					store.setConnectionStatus('error');
					store.setError('Failed to connect to session stream. Please refresh the page.');
					// Notify via session error callback for UI display
					onSessionError?.('ConnectionError', 'Lost connection to the meeting. Maximum reconnection attempts exceeded.');
				}
			},
			eventHandlers,
		});

		try {
			await sseClient.connect();
		} catch (err) {
			console.error('[SSE] Failed to start connection:', err);
		}
	}

	/**
	 * Close the SSE connection
	 */
	function close() {
		if (sseClient) {
			sseClient.close();
			sseClient = null;
		}
	}

	/**
	 * Reconnect (for manual retry or resume)
	 */
	async function reconnect() {
		store.setRetryCount(0);
		await connect();
	}

	return {
		connect,
		close,
		reconnect,
	};
}

export type SSEConnection = ReturnType<typeof createSSEConnection>;
