/**
 * Session Store - State management for meeting session
 * Svelte 5 runes-based store for session data and events
 */

import type { SSEEvent } from '$lib/api/sse-events';

export interface SessionData {
	id: string;
	problem?: {
		statement: string;
		context?: Record<string, any>;
	};
	status: string;
	phase: string | null;
	round_number?: number;
	created_at: string;
}

/**
 * Create session store with reactive state
 */
export function createSessionStore() {
	let session = $state<SessionData | null>(null);
	let events = $state<SSEEvent[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let autoScroll = $state(true);
	let retryCount = $state(0);
	let connectionStatus = $state<'connecting' | 'connected' | 'error' | 'retrying'>('connecting');

	// Event deduplication tracking (bounded to prevent memory leaks)
	const MAX_SEEN_EVENTS = 500;
	let seenEventKeys = $state(new Set<string>());
	let eventSequence = $state(0);

	return {
		// Getters (reactive)
		get session() { return session; },
		get events() { return events; },
		get isLoading() { return isLoading; },
		get error() { return error; },
		get autoScroll() { return autoScroll; },
		get retryCount() { return retryCount; },
		get connectionStatus() { return connectionStatus; },
		get seenEventKeys() { return seenEventKeys; },
		get eventSequence() { return eventSequence; },

		// Setters
		setSession(value: SessionData | null) {
			session = value;
		},
		setEvents(value: SSEEvent[]) {
			events = value;
		},
		setIsLoading(value: boolean) {
			isLoading = value;
		},
		setError(value: string | null) {
			error = value;
		},
		setAutoScroll(value: boolean) {
			autoScroll = value;
		},
		setRetryCount(value: number) {
			retryCount = value;
		},
		setConnectionStatus(value: typeof connectionStatus) {
			connectionStatus = value;
		},

		// Event management
		addEvent(newEvent: SSEEvent) {
			const subProblemIndex = newEvent.data.sub_problem_index ?? 'global';
			const personaOrId = newEvent.data.persona_code || newEvent.data.sub_problem_id || '';
			const eventKey = `${subProblemIndex}-${eventSequence}-${newEvent.event_type}-${personaOrId}`;

			eventSequence++;

			if (seenEventKeys.has(eventKey)) {
				console.warn('[Events] Duplicate detected:', eventKey);
				return;
			}

			// Enforce max size to prevent unbounded memory growth
			if (seenEventKeys.size >= MAX_SEEN_EVENTS) {
				const keys = Array.from(seenEventKeys);
				seenEventKeys = new Set(keys.slice(-MAX_SEEN_EVENTS));
				console.debug(`[Events] Pruned deduplication set to ${MAX_SEEN_EVENTS} entries`);
			}

			seenEventKeys.add(eventKey);
			events = [...events, newEvent];

			// Debug convergence events
			if (newEvent.event_type === 'convergence') {
				console.log('[EVENT RECEIVED] Convergence event:', {
					sequence: eventSequence - 1,
					event_type: newEvent.event_type,
					sub_problem_index: newEvent.data.sub_problem_index,
					score: newEvent.data.score,
					threshold: newEvent.data.threshold,
					round: newEvent.data.round,
					data: newEvent.data
				});
			}
		},

		updateSessionPhase(eventType: string, payload: any) {
			if (!session) return;

			// Extract round_number from multiple event types
			if (payload.round !== undefined && typeof payload.round === 'number') {
				session.round_number = payload.round;
			} else if (payload.round_number !== undefined && typeof payload.round_number === 'number') {
				session.round_number = payload.round_number;
			}

			// Phase transitions
			if (eventType === 'decomposition_complete') {
				session.phase = 'persona_selection';
			} else if (eventType === 'persona_selection_complete') {
				session.phase = 'initial_round';
			} else if (eventType === 'initial_round_started') {
				session.phase = 'initial_round';
				session.round_number = session.round_number || 1;
			} else if (eventType === 'round_started') {
				session.phase = 'discussion';
			} else if (eventType === 'voting_started') {
				session.phase = 'voting';
			} else if (eventType === 'synthesis_started') {
				session.phase = 'synthesis';
			} else if (eventType === 'complete') {
				session.status = 'completed';
				session.phase = 'complete';
			}
		},

		reset() {
			session = null;
			events = [];
			isLoading = true;
			error = null;
			autoScroll = true;
			retryCount = 0;
			connectionStatus = 'connecting';
			seenEventKeys = new Set<string>();
			eventSequence = 0;
		}
	};
}

export type SessionStore = ReturnType<typeof createSessionStore>;
