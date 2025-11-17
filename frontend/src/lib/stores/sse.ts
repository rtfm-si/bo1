/**
 * SSE Store - Svelte Store for SSE Connection Management
 *
 * Manages Server-Sent Events connection for real-time deliberation updates.
 * Automatically updates sessionStore when events are received.
 */

import { writable, derived, get } from 'svelte/store';
import { createSSEClient, type SSEClient, type AnySSEEvent } from '$lib/api/sse';
import { sessionStore } from './session';

/**
 * SSE connection state
 */
export interface SSEState {
	connected: boolean;
	sessionId: string | null;
	lastEvent: AnySSEEvent | null;
	error: string | null;
}

/**
 * Initial SSE state
 */
const initialState: SSEState = {
	connected: false,
	sessionId: null,
	lastEvent: null,
	error: null
};

/**
 * Create SSE store
 */
function createSSEStore() {
	const { subscribe, set, update } = writable<SSEState>(initialState);
	let client: SSEClient | null = null;

	return {
		subscribe,

		/**
		 * Connect to SSE stream for a session
		 */
		connect(sessionId: string) {
			// Disconnect existing connection if any
			this.disconnect();

			// Create new client
			client = createSSEClient({
				onOpen: () => {
					update((state) => ({
						...state,
						connected: true,
						sessionId,
						error: null
					}));
				},
				onError: (error) => {
					console.error('[SSE Store] Connection error:', error);
					update((state) => ({
						...state,
						connected: false,
						error: 'Connection error - attempting to reconnect...'
					}));
				},
				onClose: () => {
					update((state) => ({
						...state,
						connected: false
					}));
				}
			});

			// Register event handler - forward all events to sessionStore
			client.on('*', (event: AnySSEEvent) => {
				// Update SSE store with last event
				update((state) => ({
					...state,
					lastEvent: event
				}));

				// Forward to session store
				sessionStore.handleSSEEvent(event);
			});

			// Connect
			client.connect(sessionId);
		},

		/**
		 * Disconnect from SSE stream
		 */
		disconnect() {
			if (client) {
				client.close();
				client = null;
			}
			set(initialState);
		},

		/**
		 * Reconnect (close and reconnect to same session)
		 */
		reconnect() {
			const state = get({ subscribe });
			if (state.sessionId) {
				this.connect(state.sessionId);
			}
		},

		/**
		 * Get underlying SSE client (for advanced use cases)
		 */
		getClient(): SSEClient | null {
			return client;
		}
	};
}

/**
 * Singleton SSE store instance
 */
export const sseStore = createSSEStore();

/**
 * Derived store: Is SSE connected?
 */
export const isSSEConnected = derived(sseStore, ($sse) => $sse.connected);

/**
 * Derived store: Last event timestamp
 */
export const lastEventTime = derived(sseStore, ($sse) =>
	$sse.lastEvent ? new Date($sse.lastEvent.timestamp).getTime() : null
);
