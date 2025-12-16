import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { activeMeeting } from './meeting';

describe('activeMeeting store', () => {
	beforeEach(() => {
		activeMeeting.setInactive();
	});

	describe('initial state', () => {
		it('starts inactive', () => {
			const state = get(activeMeeting);
			expect(state.isActive).toBe(false);
			expect(state.sessionId).toBeNull();
		});
	});

	describe('setActive', () => {
		it('sets meeting as active with session ID', () => {
			activeMeeting.setActive('session-123');
			const state = get(activeMeeting);
			expect(state.isActive).toBe(true);
			expect(state.sessionId).toBe('session-123');
		});
	});

	describe('setInactive', () => {
		it('clears active state', () => {
			activeMeeting.setActive('session-123');
			activeMeeting.setInactive();
			const state = get(activeMeeting);
			expect(state.isActive).toBe(false);
			expect(state.sessionId).toBeNull();
		});
	});

	describe('updateFromStatus', () => {
		it.each([
			['active', true],
			['created', true],
			['running', true],
			['paused', true],
			['completed', false],
			['failed', false],
		])('status "%s" sets isActive to %s', (status, expectedActive) => {
			activeMeeting.updateFromStatus('session-456', status);
			const state = get(activeMeeting);
			expect(state.isActive).toBe(expectedActive);
			if (expectedActive) {
				expect(state.sessionId).toBe('session-456');
			} else {
				expect(state.sessionId).toBeNull();
			}
		});
	});

	describe('cookie consent integration', () => {
		it('banner should be hidden during active meeting', () => {
			// Simulate: needsConsent = true, meeting active
			activeMeeting.setActive('session-789');
			const state = get(activeMeeting);
			// CookieConsent uses: shouldShow = needsConsent && !$activeMeeting.isActive
			const needsConsent = true;
			const shouldShow = needsConsent && !state.isActive;
			expect(shouldShow).toBe(false);
		});

		it('banner should show when meeting completes', () => {
			// Simulate: meeting was active, now completed
			activeMeeting.setActive('session-789');
			activeMeeting.updateFromStatus('session-789', 'completed');
			const state = get(activeMeeting);
			const needsConsent = true;
			const shouldShow = needsConsent && !state.isActive;
			expect(shouldShow).toBe(true);
		});

		it('banner should show on other pages (no active meeting)', () => {
			const state = get(activeMeeting);
			const needsConsent = true;
			const shouldShow = needsConsent && !state.isActive;
			expect(shouldShow).toBe(true);
		});

		it('banner stays hidden if already consented', () => {
			activeMeeting.setInactive();
			const state = get(activeMeeting);
			const needsConsent = false; // User already consented
			const shouldShow = needsConsent && !state.isActive;
			expect(shouldShow).toBe(false);
		});
	});
});
