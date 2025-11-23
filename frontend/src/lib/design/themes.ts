/**
 * Theme System - Multiple theme presets with plug-and-play architecture
 * Themes define color mappings for semantic tokens
 */

import { colors } from './tokens';

// ============================================================================
// Theme Type Definitions
// ============================================================================

export interface Theme {
	name: string;
	displayName: string;
	colors: {
		// Surface colors
		background: string;
		surface: string;
		surfaceVariant: string;
		// Text colors
		textPrimary: string;
		textSecondary: string;
		textTertiary: string;
		// Border colors
		border: string;
		borderFocus: string;
		// Semantic colors (minimal - using new 3-context system)
		brand: string;
		success: string;
		warning: string;
		error: string;
		info: string;
	};
}

// ============================================================================
// Theme Presets
// ============================================================================

export const lightTheme: Theme = {
	name: 'light',
	displayName: 'Light',
	colors: {
		// Surfaces
		background: colors.neutral[50],
		surface: '#ffffff',
		surfaceVariant: colors.neutral[100],
		// Text
		textPrimary: colors.neutral[900],
		textSecondary: colors.neutral[600],
		textTertiary: colors.neutral[500],
		// Borders
		border: colors.neutral[200],
		borderFocus: colors.brand[500],
		// Semantic (using new 3-context system)
		brand: colors.brand[600],
		success: colors.semantic.success,
		warning: colors.semantic.warning,
		error: colors.semantic.error,
		info: colors.semantic.info,
	},
};

export const darkTheme: Theme = {
	name: 'dark',
	displayName: 'Dark',
	colors: {
		// Surfaces - lighter for better contrast
		background: colors.neutral[900],
		surface: colors.neutral[800],
		surfaceVariant: colors.neutral[700],
		// Text - brighter for better readability
		textPrimary: colors.neutral[100],
		textSecondary: colors.neutral[300],
		textTertiary: colors.neutral[400],
		// Borders - more visible
		border: colors.neutral[600],
		borderFocus: colors.brand[400],
		// Semantic (using new 3-context system)
		brand: colors.brand[400],
		success: colors.semantic.success,
		warning: colors.semantic.warning,
		error: colors.semantic.error,
		info: colors.semantic.info,
	},
};

export const oceanTheme: Theme = {
	name: 'ocean',
	displayName: 'Ocean',
	colors: {
		// Surfaces (rich teal-blue ocean depths)
		background: '#001a1f',
		surface: '#003d47',
		surfaceVariant: '#00565e',
		// Text (bright aqua and teal)
		textPrimary: colors.brand[100],
		textSecondary: colors.brand[300],
		textTertiary: colors.brand[400],
		// Borders (teal-cyan)
		border: colors.brand[600],
		borderFocus: colors.brand[400],
		// Semantic (ocean-themed - using new 3-context system)
		brand: colors.brand[300],
		success: '#4ade80', // Bright sea green
		warning: '#fbbf24', // Bright amber
		error: '#fb7185', // Bright coral-pink
		info: '#22d3ee', // Bright cyan
	},
};

// ============================================================================
// Theme Registry
// ============================================================================

export const themes: Record<string, Theme> = {
	light: lightTheme,
	dark: darkTheme,
	ocean: oceanTheme,
};

export type ThemeName = keyof typeof themes;

// Theme mode includes 'auto' for system preference following
export type ThemeMode = 'auto' | ThemeName;

// ============================================================================
// Theme Application Logic
// ============================================================================

/**
 * Get system color scheme preference
 */
function getSystemTheme(): ThemeName {
	if (typeof window === 'undefined') return 'light';
	return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Apply theme to document by setting CSS custom properties and classes
 * Uses .theme-{name} class pattern for better isolation
 */
export function applyTheme(themeName: ThemeName, preserveAuto: boolean = false): void {
	const theme = themes[themeName];
	if (!theme) {
		console.warn(`Theme "${themeName}" not found. Using light theme.`);
		applyTheme('light', preserveAuto);
		return;
	}

	const root = document.documentElement;

	// Apply CSS custom properties (for components that use --color-* directly)
	Object.entries(theme.colors).forEach(([key, value]) => {
		root.style.setProperty(`--color-${key}`, value);
	});

	// Remove theme classes (but preserve theme-auto if requested)
	root.classList.remove('theme-light', 'theme-dark', 'theme-ocean', 'dark');
	if (!preserveAuto) {
		root.classList.remove('theme-auto');
	}

	// Add theme-specific class
	root.classList.add(`theme-${themeName}`);

	// Add dark class for dark/ocean themes (for backward compatibility)
	if (themeName === 'dark' || themeName === 'ocean') {
		root.classList.add('dark');
	}
}

/**
 * Apply theme mode (handles 'auto' by detecting system preference)
 */
export function applyThemeMode(mode: ThemeMode): void {
	const root = document.documentElement;
	let effectiveTheme: ThemeName;

	if (mode === 'auto') {
		effectiveTheme = getSystemTheme();
		// Add auto-mode class BEFORE applying theme to preserve it
		root.classList.add('theme-auto');
		// Apply theme while preserving theme-auto class
		applyTheme(effectiveTheme, true);
	} else {
		// Remove auto-mode class for explicit themes
		root.classList.remove('theme-auto');
		effectiveTheme = mode;
		applyTheme(effectiveTheme, false);
	}

	// Store mode preference (not effective theme)
	localStorage.setItem('theme', mode);
}

/**
 * Get current theme mode from localStorage or default to 'auto'
 * SIMPLIFIED: Always returns 'auto' to follow system preference
 */
export function getCurrentThemeMode(): ThemeMode {
	// Always use auto mode - follow system preference
	return 'auto';
}

/**
 * Get effective theme (resolves 'auto' to actual theme)
 */
export function getEffectiveTheme(mode: ThemeMode): ThemeName {
	if (mode === 'auto') {
		return getSystemTheme();
	}
	return mode;
}

/**
 * Initialize theme on app load
 */
export function initializeTheme(): ThemeMode {
	const mode = getCurrentThemeMode();
	applyThemeMode(mode);
	return mode;
}
