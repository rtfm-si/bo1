/**
 * Meeting Store - Global state for active meeting context
 * Used by CookieConsent to auto-hide during active meetings
 */

import { writable } from 'svelte/store';

export interface ActiveMeetingState {
	isActive: boolean;
	sessionId: string | null;
}

const initialState: ActiveMeetingState = {
	isActive: false,
	sessionId: null,
};

function createActiveMeetingStore() {
	const { subscribe, set, update } = writable<ActiveMeetingState>(initialState);

	return {
		subscribe,
		/**
		 * Set meeting as active (hides cookie consent banner)
		 */
		setActive(sessionId: string) {
			set({ isActive: true, sessionId });
		},
		/**
		 * Clear active meeting state (re-shows cookie consent if not yet consented)
		 */
		setInactive() {
			set(initialState);
		},
		/**
		 * Update based on session status - only hide for truly active sessions
		 */
		updateFromStatus(sessionId: string, status: string) {
			// Hide banner for sessions that are actively running
			const activeStatuses = ['active', 'created', 'running', 'paused'];
			const isActive = activeStatuses.includes(status);
			set({ isActive, sessionId: isActive ? sessionId : null });
		},
	};
}

export const activeMeeting = createActiveMeetingStore();
