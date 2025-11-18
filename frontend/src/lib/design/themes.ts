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
		// Semantic (use design tokens)
		brand: colors.brand[600],
		accent: colors.accent[600],
		success: colors.success[600],
		warning: colors.warning[500],
		error: colors.error[600],
		info: colors.info[600],
	},
};

export const darkTheme: Theme = {
	name: 'dark',
	displayName: 'Dark',
	colors: {
		// Surfaces
		background: colors.neutral[950],
		surface: colors.neutral[900],
		surfaceVariant: colors.neutral[800],
		// Text
		textPrimary: colors.neutral[50],
		textSecondary: colors.neutral[400],
		textTertiary: colors.neutral[500],
		// Borders
		border: colors.neutral[700],
		borderFocus: colors.brand[400],
		// Semantic (brighter in dark mode)
		brand: colors.brand[400],
		accent: colors.accent[400],
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

// ============================================================================
// Theme Application Logic
// ============================================================================

/**
 * Apply theme to document by setting CSS custom properties
 */
export function applyTheme(themeName: ThemeName): void {
	const theme = themes[themeName];
	if (!theme) {
		console.warn(`Theme "${themeName}" not found. Using light theme.`);
		applyTheme('light');
		return;
	}

	const root = document.documentElement;

	// Apply CSS custom properties
	Object.entries(theme.colors).forEach(([key, value]) => {
		root.style.setProperty(`--color-${key}`, value);
	});

	// Update dark mode class
	if (themeName === 'dark' || themeName === 'ocean') {
		root.classList.add('dark');
	} else {
		root.classList.remove('dark');
	}

	// Store theme preference
	localStorage.setItem('theme', themeName);
}

/**
 * Get current theme from localStorage or system preference
 */
export function getCurrentTheme(): ThemeName {
	// Check localStorage first
	const stored = localStorage.getItem('theme') as ThemeName | null;
	if (stored && themes[stored]) {
		return stored;
	}

	// Fall back to system preference
	if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
		return 'dark';
	}

	return 'light';
}

/**
 * Initialize theme on app load
 */
export function initializeTheme(): ThemeName {
	const theme = getCurrentTheme();
	applyTheme(theme);
	return theme;
}
