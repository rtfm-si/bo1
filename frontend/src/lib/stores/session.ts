/**
 * Session Store - Svelte Store for Deliberation Session State
 *
 * Manages deliberation session state including:
 * - Session metadata (id, status, phase)
 * - Contributions feed (real-time updates from SSE)
 * - Metrics (cost, rounds, tokens)
 * - Actions (create, load, update)
 */

import { writable, derived, get } from 'svelte/store';
import { apiClient, ApiClientError } from '$lib/api/client';
import type { SessionDetailResponse } from '$lib/api/types';
import type { ContributionEvent, AnySSEEvent } from '$lib/api/sse';

/**
 * Contribution in the feed
 */
export interface Contribution {
	persona_code: string;
	persona_name?: string;
	content: string;
	round_number: number;
	timestamp: string;
}

/**
 * Session state shape
 */
export interface SessionState {
	id: string | null;
	status: 'active' | 'paused' | 'completed' | 'failed' | 'killed' | null;
	phase: string | null;
	created_at: string | null;
	updated_at: string | null;
	problem_statement: string | null;
	contributions: Contribution[];
	metrics: {
		total_cost: number;
		total_tokens: number;
		phase_costs: Record<string, number>;
		convergence_score?: number;
	} | null;
	round_number: number;
	max_rounds: number;
	loading: boolean;
	error: string | null;
}

/**
 * Initial session state
 */
const initialState: SessionState = {
	id: null,
	status: null,
	phase: null,
	created_at: null,
	updated_at: null,
	problem_statement: null,
	contributions: [],
	metrics: null,
	round_number: 0,
	max_rounds: 15,
	loading: false,
	error: null
};

/**
 * Create session store
 */
function createSessionStore() {
	const { subscribe, set, update } = writable<SessionState>(initialState);

	return {
		subscribe,

		/**
		 * Create a new deliberation session
		 */
		async create(problemStatement: string, problemContext?: Record<string, unknown>) {
			update((state) => ({ ...state, loading: true, error: null }));

			try {
				const response = await apiClient.createSession({
					problem_statement: problemStatement,
					problem_context: problemContext
				});

				update((state) => ({
					...state,
					id: response.id,
					status: response.status,
					phase: response.phase,
					created_at: response.created_at,
					updated_at: response.updated_at,
					problem_statement: response.problem_statement,
					loading: false
				}));

				return response.id;
			} catch (error) {
				const errorMessage =
					error instanceof ApiClientError ? error.message : 'Failed to create session';
				update((state) => ({ ...state, loading: false, error: errorMessage }));
				throw error;
			}
		},

		/**
		 * Load an existing session
		 */
		async load(sessionId: string) {
			update((state) => ({ ...state, loading: true, error: null }));

			try {
				const response = await apiClient.getSession(sessionId);

				update((state) => ({
					...state,
					id: response.id,
					status: response.status,
					phase: response.phase,
					created_at: response.created_at,
					updated_at: response.updated_at,
					problem_statement: response.problem_statement,
					contributions: response.contributions || [],
					metrics: response.metrics || null,
					round_number: response.round_number || 0,
					max_rounds: response.max_rounds || 15,
					loading: false
				}));

				return response;
			} catch (error) {
				const errorMessage =
					error instanceof ApiClientError ? error.message : 'Failed to load session';
				update((state) => ({ ...state, loading: false, error: errorMessage }));
				throw error;
			}
		},

		/**
		 * Start deliberation (call API endpoint)
		 */
		async start() {
			const state = get({ subscribe });
			if (!state.id) {
				throw new Error('No session loaded');
			}

			try {
				await apiClient.startDeliberation(state.id);
				update((s) => ({ ...s, status: 'active' }));
			} catch (error) {
				const errorMessage =
					error instanceof ApiClientError ? error.message : 'Failed to start deliberation';
				update((s) => ({ ...s, error: errorMessage }));
				throw error;
			}
		},

		/**
		 * Pause deliberation
		 */
		async pause() {
			const state = get({ subscribe });
			if (!state.id) {
				throw new Error('No session loaded');
			}

			try {
				await apiClient.pauseDeliberation(state.id);
				update((s) => ({ ...s, status: 'paused' }));
			} catch (error) {
				const errorMessage =
					error instanceof ApiClientError ? error.message : 'Failed to pause deliberation';
				update((s) => ({ ...s, error: errorMessage }));
				throw error;
			}
		},

		/**
		 * Resume deliberation
		 */
		async resume() {
			const state = get({ subscribe });
			if (!state.id) {
				throw new Error('No session loaded');
			}

			try {
				await apiClient.resumeDeliberation(state.id);
				update((s) => ({ ...s, status: 'active' }));
			} catch (error) {
				const errorMessage =
					error instanceof ApiClientError ? error.message : 'Failed to resume deliberation';
				update((s) => ({ ...s, error: errorMessage }));
				throw error;
			}
		},

		/**
		 * Kill deliberation
		 */
		async kill(reason?: string) {
			const state = get({ subscribe });
			if (!state.id) {
				throw new Error('No session loaded');
			}

			try {
				await apiClient.killDeliberation(state.id, reason);
				update((s) => ({ ...s, status: 'killed' }));
			} catch (error) {
				const errorMessage =
					error instanceof ApiClientError ? error.message : 'Failed to kill deliberation';
				update((s) => ({ ...s, error: errorMessage }));
				throw error;
			}
		},

		/**
		 * Add a contribution to the feed (from SSE event)
		 */
		addContribution(contribution: Contribution) {
			update((state) => ({
				...state,
				contributions: [...state.contributions, contribution]
			}));
		},

		/**
		 * Update session from SSE event
		 */
		handleSSEEvent(event: AnySSEEvent) {
			switch (event.type) {
				case 'contribution':
					{
						const contribEvent = event as ContributionEvent;
						const contribution: Contribution = {
							persona_code: contribEvent.data.persona_code,
							persona_name: contribEvent.data.persona_name,
							content: contribEvent.data.content,
							round_number: contribEvent.data.round_number,
							timestamp: event.timestamp
						};
						update((state) => ({
							...state,
							contributions: [...state.contributions, contribution]
						}));
					}
					break;

				case 'facilitator_decision':
					update((state) => ({
						...state,
						phase: `facilitator_${event.data.action}`
					}));
					break;

				case 'convergence':
					update((state) => ({
						...state,
						metrics: state.metrics
							? {
									...state.metrics,
									convergence_score: event.data.convergence_score
								}
							: null
					}));
					break;

				case 'complete':
					update((state) => ({
						...state,
						status: 'completed',
						metrics: state.metrics
							? {
									...state.metrics,
									total_cost: event.data.final_cost
								}
							: {
									total_cost: event.data.final_cost,
									total_tokens: 0,
									phase_costs: {}
								}
					}));
					break;

				case 'error':
					update((state) => ({
						...state,
						status: 'failed',
						error: event.data.error
					}));
					break;

				case 'node_start':
					update((state) => ({
						...state,
						phase: event.data.node
					}));
					break;

				case 'node_end':
					// No-op, just update timestamp
					update((state) => ({
						...state,
						updated_at: event.timestamp
					}));
					break;

				case 'clarification_requested':
				case 'clarification_answered':
					// Handled by UI components
					break;
			}
		},

		/**
		 * Reset store to initial state
		 */
		reset() {
			set(initialState);
		},

		/**
		 * Clear error
		 */
		clearError() {
			update((state) => ({ ...state, error: null }));
		}
	};
}

/**
 * Singleton session store instance
 */
export const sessionStore = createSessionStore();

/**
 * Derived store: Is session active?
 */
export const isSessionActive = derived(sessionStore, ($session) => $session.status === 'active');

/**
 * Derived store: Can pause?
 */
export const canPause = derived(sessionStore, ($session) => $session.status === 'active');

/**
 * Derived store: Can resume?
 */
export const canResume = derived(sessionStore, ($session) => $session.status === 'paused');

/**
 * Derived store: Can kill?
 */
export const canKill = derived(
	sessionStore,
	($session) => $session.status === 'active' || $session.status === 'paused'
);

/**
 * Derived store: Is deliberation complete?
 */
export const isComplete = derived(
	sessionStore,
	($session) => $session.status === 'completed' || $session.status === 'failed' || $session.status === 'killed'
);
