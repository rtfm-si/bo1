/**
 * Theme Store - Svelte store for theme state management
 * SIMPLIFIED: Always follows system preference (auto mode only)
 */

import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import type { ThemeMode } from '$lib/design/themes';
import { applyThemeMode, getEffectiveTheme } from '$lib/design/themes';

// ============================================================================
// Theme Store (Auto-only)
// ============================================================================

function createThemeStore() {
	// Always use 'auto' mode - follow system preference
	const { subscribe, set } = writable<ThemeMode>('auto');

	return {
		subscribe,
		/**
		 * Get current effective theme (resolves 'auto' to 'light' or 'dark')
		 */
		getEffective: (mode: ThemeMode) => {
			return getEffectiveTheme(mode);
		},
		/**
		 * Initialize theme on app mount
		 * Sets up auto-switching based on system preference
		 */
		initialize: () => {
			if (!browser) return;

			// Apply auto mode (follows system preference)
			applyThemeMode('auto');
			set('auto');

			// Listen for system theme changes and automatically switch
			const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
			const handleChange = (e: MediaQueryListEvent) => {
				// Always re-apply to pick up system preference change
				applyThemeMode('auto');
			};

			mediaQuery.addEventListener('change', handleChange);

			// Return cleanup function
			return () => {
				mediaQuery.removeEventListener('change', handleChange);
			};
		},
	};
}

export const themeStore = createThemeStore();
