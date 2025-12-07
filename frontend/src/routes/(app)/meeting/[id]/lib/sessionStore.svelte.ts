/**
 * Session Store - State management for meeting session
 * Svelte 5 runes-based store for session data and events
 */

import type { SSEEvent } from '$lib/api/sse-events';
import { createLogger } from '$lib/utils/debug';

const log = createLogger('Events');

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
	// P2-004: Expert summaries by sub-problem index
	expert_summaries_by_subproblem?: Record<number, Record<string, string>>;
	// P2-006: Research results by sub-problem index
	research_results_by_subproblem?: Record<number, any[]>;
}

/**
 * Create session store with reactive state
 */
export function createSessionStore() {
	let session = $state<SessionData | null>(null);
	// Use $state.raw for events - they're immutable (only appended/replaced)
	// This avoids deep proxy overhead for potentially 1000s of event objects
	let events = $state.raw<SSEEvent[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let autoScroll = $state(true);
	let retryCount = $state(0);
	let connectionStatus = $state<'connecting' | 'connected' | 'error' | 'retrying'>('connecting');

	// Event deduplication tracking (bounded to prevent memory leaks)
	const MAX_SEEN_EVENTS = 500;
	// Maximum events to retain in memory (prevents unbounded growth)
	const MAX_EVENTS = 5000;
	// Use $state.raw for Set - it's reassigned, not mutated in place
	let seenEventKeys = $state.raw(new Set<string>());
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
				log.warn('Duplicate detected:', eventKey);
				return;
			}

			// Enforce max size to prevent unbounded memory growth
			if (seenEventKeys.size >= MAX_SEEN_EVENTS) {
				const keys = Array.from(seenEventKeys);
				seenEventKeys = new Set(keys.slice(-MAX_SEEN_EVENTS));
				log.debug(`Pruned deduplication set to ${MAX_SEEN_EVENTS} entries`);
			}

			seenEventKeys.add(eventKey);

			// Enforce max events limit to prevent unbounded memory growth
			if (events.length >= MAX_EVENTS) {
				// Keep the most recent events, prune oldest 10%
				const pruneCount = Math.floor(MAX_EVENTS * 0.1);
				events = [...events.slice(pruneCount), newEvent];
				log.debug(`Pruned ${pruneCount} oldest events to maintain max size of ${MAX_EVENTS}`);
			} else {
				events = [...events, newEvent];
			}

			// Debug convergence events
			if (newEvent.event_type === 'convergence') {
				log.log('Convergence event:', {
					sequence: eventSequence - 1,
					event_type: newEvent.event_type,
					sub_problem_index: newEvent.data.sub_problem_index,
					score: newEvent.data.score,
					threshold: newEvent.data.threshold,
					round: newEvent.data.round
				});
			}
			// Debug contribution events
			if (newEvent.event_type === 'contribution') {
				const data = newEvent.data as Record<string, unknown>;
				const summary = data?.summary as Record<string, unknown> | undefined;
				log.log('Contribution event:', {
					persona_name: data?.persona_name,
					persona_code: data?.persona_code,
					archetype: data?.archetype,
					has_summary: !!summary
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

			// P2-004: Handle expert_summaries event
			if (eventType === 'expert_summaries' && payload.expert_summaries) {
				const subProblemIndex = payload.sub_problem_index ?? 0;
				if (!session.expert_summaries_by_subproblem) {
					session.expert_summaries_by_subproblem = {};
				}
				session.expert_summaries_by_subproblem[subProblemIndex] = payload.expert_summaries;
			}

			// P2-006: Handle research_results event
			if (eventType === 'research_results' && payload.research_results) {
				const subProblemIndex = payload.sub_problem_index ?? 0;
				if (!session.research_results_by_subproblem) {
					session.research_results_by_subproblem = {};
				}
				if (!session.research_results_by_subproblem[subProblemIndex]) {
					session.research_results_by_subproblem[subProblemIndex] = [];
				}
				// BUG FIX: Deduplicate by query to prevent duplicates on page refresh
				// When historical events are replayed, the same research results would
				// be appended multiple times without this check
				const existingQueries = new Set(
					session.research_results_by_subproblem[subProblemIndex].map((r: any) => r.query)
				);
				const newResults = payload.research_results.filter(
					(r: any) => !existingQueries.has(r.query)
				);
				if (newResults.length > 0) {
					session.research_results_by_subproblem[subProblemIndex].push(...newResults);
				}
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
			} else if (eventType === 'clarification_required') {
				// Session pauses for clarification questions
				session.status = 'paused';
				session.phase = 'clarification_needed';
			} else if (eventType === 'complete') {
				session.status = 'completed';
				session.phase = 'complete';
			}
		},

		reset() {
			session = null;
			events = [];  // $state.raw allows direct assignment
			isLoading = true;
			error = null;
			autoScroll = true;
			retryCount = 0;
			connectionStatus = 'connecting';
			seenEventKeys = new Set<string>();  // $state.raw allows direct assignment
			eventSequence = 0;
		}
	};
}

export type SessionStore = ReturnType<typeof createSessionStore>;
