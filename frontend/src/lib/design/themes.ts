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
		// Semantic colors (use token colors)
		brand: string;
		accent: string;
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
		// Semantic (use design tokens - subdued)
		brand: colors.brand[600],
		accent: colors.accent[500],
		success: colors.success[500],
		warning: colors.warning[500],
		error: colors.error[500],
		info: colors.info[500],
	},
};

export const darkTheme: Theme = {
	name: 'dark',
	displayName: 'Dark',
	colors: {
		// Surfaces - lighter for better contrast
		background: colors.neutral[900], // Was 950 - now lighter
		surface: colors.neutral[800],     // Was 900 - now lighter
		surfaceVariant: '#3a4246', // Between 700 and 800 for better contrast
		// Text - brighter for better readability
		textPrimary: colors.neutral[100],  // Was 50 - now slightly less bright but still high contrast
		textSecondary: colors.neutral[300], // Was 400 - now brighter
		textTertiary: colors.neutral[400],  // Was 500 - now brighter
		// Borders - more visible
		border: colors.neutral[600],        // Was 700 - now lighter/more visible
		borderFocus: colors.brand[400],
		// Semantic (slightly brighter in dark mode, but still muted)
		brand: colors.brand[400],
		accent: colors.accent[300],
		success: colors.success[400],
		warning: colors.warning[400],
		error: colors.error[400],
		info: colors.info[400],
	},
};

export const oceanTheme: Theme = {
	name: 'ocean',
	displayName: 'Ocean',
	colors: {
		// Surfaces (rich teal-blue ocean depths)
		background: '#001a1f', // Deep ocean blue-teal
		surface: '#003d47', // Dark ocean teal
		surfaceVariant: '#00565e', // Medium ocean teal
		// Text (bright aqua and teal)
		textPrimary: '#b3f0ea', // Bright aqua (brand 100)
		textSecondary: '#4dddce', // Vibrant teal (brand 300)
		textTertiary: '#1ad3c0', // Medium teal (brand 400)
		// Borders (teal-cyan with glow)
		border: '#00a594', // Teal border (brand 600)
		borderFocus: '#1ad3c0', // Bright teal focus (brand 400)
		// Semantic (ocean-themed - brighter for contrast on dark teal bg)
		brand: colors.brand[300], // Brighter teal
		accent: '#ff8a6b', // Warmer coral for strong contrast
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
