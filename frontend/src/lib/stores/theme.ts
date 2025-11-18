/**
 * Theme Store - Svelte store for theme state management
 * Handles theme switching and persistence
 */

import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import type { ThemeName } from '$lib/design/themes';
import { applyTheme, getCurrentTheme } from '$lib/design/themes';

// ============================================================================
// Theme Store
// ============================================================================

function createThemeStore() {
	// Initialize with current theme (only in browser)
	const initialTheme: ThemeName = browser ? getCurrentTheme() : 'light';
	const { subscribe, set } = writable<ThemeName>(initialTheme);

	return {
		subscribe,
		/**
		 * Set theme and persist to localStorage
		 */
		setTheme: (theme: ThemeName) => {
			if (!browser) return;

			applyTheme(theme);
			set(theme);
		},
		/**
		 * Initialize theme on app mount
		 */
		initialize: () => {
			if (!browser) return;

			const currentTheme = getCurrentTheme();
			applyTheme(currentTheme);
			set(currentTheme);

			// Listen for system theme changes
			const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
			const handleChange = (e: MediaQueryListEvent) => {
				// Only auto-switch if user hasn't set a preference
				const storedTheme = localStorage.getItem('theme');
				if (!storedTheme) {
					const newTheme: ThemeName = e.matches ? 'dark' : 'light';
					applyTheme(newTheme);
					set(newTheme);
				}
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
