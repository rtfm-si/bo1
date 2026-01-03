/**
 * User preferences store.
 *
 * Manages user preferences that affect UI display, including:
 * - Currency display preference
 * - Other display preferences
 *
 * Loads from /api/v1/user/preferences on init.
 */

import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import type { CurrencyCode } from '$lib/utils/currency';

export interface UserPreferences {
	skip_clarification: boolean;
	default_reminder_frequency_days: number;
	preferred_currency: CurrencyCode;
}

interface PreferencesState {
	preferences: UserPreferences | null;
	isLoading: boolean;
	error: string | null;
}

const defaultPreferences: UserPreferences = {
	skip_clarification: false,
	default_reminder_frequency_days: 3,
	preferred_currency: 'GBP'
};

const initialState: PreferencesState = {
	preferences: null,
	isLoading: true,
	error: null
};

const preferencesStore = writable<PreferencesState>(initialState);

// Derived stores for convenience
export const preferences = derived(preferencesStore, ($state) => $state.preferences ?? defaultPreferences);
export const preferredCurrency = derived(
	preferencesStore,
	($state) => ($state.preferences?.preferred_currency ?? 'GBP') as CurrencyCode
);
export const isLoadingPreferences = derived(preferencesStore, ($state) => $state.isLoading);
export const preferencesError = derived(preferencesStore, ($state) => $state.error);

/**
 * Load user preferences from API.
 * Called after authentication is confirmed.
 */
export async function loadPreferences(): Promise<void> {
	if (!browser) return;

	try {
		preferencesStore.update((state) => ({ ...state, isLoading: true, error: null }));

		const { env } = await import('$env/dynamic/public');
		const API_BASE_URL = env.PUBLIC_API_URL || 'http://localhost:8000';

		const response = await fetch(`${API_BASE_URL}/api/v1/user/preferences`, {
			credentials: 'include'
		});

		if (response.ok) {
			const data = await response.json();
			preferencesStore.set({
				preferences: {
					skip_clarification: data.skip_clarification ?? false,
					default_reminder_frequency_days: data.default_reminder_frequency_days ?? 3,
					preferred_currency: (data.preferred_currency ?? 'GBP') as CurrencyCode
				},
				isLoading: false,
				error: null
			});
		} else {
			// Use defaults on error
			preferencesStore.set({
				preferences: defaultPreferences,
				isLoading: false,
				error: null
			});
		}
	} catch (error) {
		console.warn('Failed to load preferences:', error);
		preferencesStore.set({
			preferences: defaultPreferences,
			isLoading: false,
			error: 'Failed to load preferences'
		});
	}
}

/**
 * Update preferred currency.
 *
 * @param currency - New currency code
 */
export async function updatePreferredCurrency(currency: CurrencyCode): Promise<void> {
	if (!browser) return;

	const currentState = preferencesStore;
	let previousCurrency: CurrencyCode = 'GBP';

	// Optimistic update
	preferencesStore.update((state) => {
		previousCurrency = state.preferences?.preferred_currency ?? 'GBP';
		return {
			...state,
			preferences: state.preferences
				? { ...state.preferences, preferred_currency: currency }
				: { ...defaultPreferences, preferred_currency: currency }
		};
	});

	try {
		const { env } = await import('$env/dynamic/public');
		const API_BASE_URL = env.PUBLIC_API_URL || 'http://localhost:8000';

		const response = await fetch(`${API_BASE_URL}/api/v1/user/preferences`, {
			method: 'PATCH',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ preferred_currency: currency })
		});

		if (!response.ok) {
			throw new Error('Failed to update currency preference');
		}
	} catch (error) {
		// Revert on error
		preferencesStore.update((state) => ({
			...state,
			preferences: state.preferences
				? { ...state.preferences, preferred_currency: previousCurrency }
				: { ...defaultPreferences, preferred_currency: previousCurrency },
			error: 'Failed to save currency preference'
		}));
	}
}

/**
 * Reset preferences store (on logout).
 */
export function resetPreferences(): void {
	preferencesStore.set(initialState);
}

export default preferencesStore;
