import { colors, spacing, typography, shadows, borderRadius, transitions, zIndex } from './src/lib/design/tokens';

/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class', // Use class-based dark mode for theme switcher
	theme: {
		extend: {
			// Semantic color system (NOT primary/secondary)
			colors: {
				brand: colors.brand,
				accent: colors.accent,
				success: colors.success,
				warning: colors.warning,
				error: colors.error,
				info: colors.info,
				neutral: colors.neutral,
			},
			// Spacing system
			spacing,
			// Typography
			fontFamily: typography.fontFamily,
			fontSize: typography.fontSize,
			fontWeight: typography.fontWeight,
			lineHeight: typography.lineHeight,
			letterSpacing: typography.letterSpacing,
			// Shadows
			boxShadow: shadows,
			// Border radius
			borderRadius,
			// Transitions
			transitionDuration: transitions.duration,
			transitionTimingFunction: transitions.timing,
			// Z-index
			zIndex,
		},
	},
	plugins: [],
};
