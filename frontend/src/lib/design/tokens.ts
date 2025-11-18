/**
 * Design Tokens - Central source of truth for all design values
 * Used by Tailwind config and theme system
 */

// ============================================================================
// Color Tokens - Semantic naming (NOT primary/secondary)
// ============================================================================

export const colors = {
	// Brand colors (primary teal from logo #00C8B3)
	brand: {
		50: '#e6faf8', // Very light teal (backgrounds, hover states)
		100: '#b3f0ea', // Light teal (subtle highlights)
		200: '#80e7dc', // Lighter teal
		300: '#4dddce', // Light-medium teal
		400: '#1ad3c0', // Medium teal
		500: '#00C8B3', // PRIMARY BRAND COLOR (from logo)
		600: '#00a594', // Darker teal (text, buttons)
		700: '#008275', // Dark teal (active states)
		800: '#006056', // Very dark teal
		900: '#003d37', // Deepest teal
		950: '#002621', // Almost black teal
	},
	// Accent colors (warm coral - complementary to teal)
	accent: {
		50: '#fff5f3', // Very light coral
		100: '#ffe4de', // Light coral
		200: '#ffcdc2', // Lighter coral
		300: '#ffab99', // Light-medium coral
		400: '#ff8a70', // Medium coral
		500: '#ff6b47', // Main accent color (warm coral)
		600: '#f04e2a', // Darker coral
		700: '#d13818', // Dark coral-red
		800: '#a82d14', // Very dark coral
		900: '#7f2312', // Deepest coral
		950: '#4a1409', // Almost black coral
	},
	// Success (green tones aligned with teal)
	success: {
		50: '#edfcf2', // Very light green
		100: '#d3f8df', // Light green
		200: '#aaf0c4', // Lighter green
		300: '#73e2a3', // Light-medium green
		400: '#3dd87e', // Medium green
		500: '#10b05e', // Main success color
		600: '#059a4f', // Darker green
		700: '#047a3f', // Dark green
		800: '#056132', // Very dark green
		900: '#04502a', // Deepest green
		950: '#022d17', // Almost black green
	},
	// Warning (amber tones)
	warning: {
		50: '#fffbeb', // Very light amber
		100: '#fef3c7', // Light amber
		200: '#fde68a', // Lighter amber
		300: '#fcd34d', // Light-medium amber
		400: '#fbbf24', // Medium amber
		500: '#f59e0b', // Main warning color
		600: '#d97706', // Darker amber
		700: '#b45309', // Dark amber
		800: '#92400e', // Very dark amber
		900: '#78350f', // Deepest amber
		950: '#451a03', // Almost black amber
	},
	// Error (red-orange to harmonize with coral accent)
	error: {
		50: '#fef2f2', // Very light red
		100: '#fee2e2', // Light red
		200: '#fecaca', // Lighter red
		300: '#fca5a5', // Light-medium red
		400: '#f87171', // Medium red
		500: '#ef4444', // Main error color
		600: '#dc2626', // Darker red
		700: '#b91c1c', // Dark red
		800: '#991b1b', // Very dark red
		900: '#7f1d1d', // Deepest red
		950: '#450a0a', // Almost black red
	},
	// Info (lighter teal/cyan for informational messages)
	info: {
		50: '#ecfeff', // Very light cyan
		100: '#cffafe', // Light cyan
		200: '#a5f3fc', // Lighter cyan
		300: '#67e8f9', // Light-medium cyan
		400: '#22d3ee', // Medium cyan
		500: '#06b6d4', // Main info color (cyan)
		600: '#0891b2', // Darker cyan
		700: '#0e7490', // Dark cyan
		800: '#155e75', // Very dark cyan
		900: '#164e63', // Deepest cyan
		950: '#083344', // Almost black cyan
	},
	// Neutral (cool grays with subtle teal tint for consistency)
	neutral: {
		50: '#f8fafa', // Very light cool gray
		100: '#f1f4f5', // Light cool gray
		200: '#e3e8ea', // Lighter cool gray
		300: '#d1d9dc', // Light-medium cool gray
		400: '#a3b1b7', // Medium cool gray
		500: '#738891', // Main neutral color
		600: '#526b75', // Darker cool gray
		700: '#3f5459', // Dark cool gray
		800: '#2a3b40', // Very dark cool gray
		900: '#1a2629', // Deepest cool gray
		950: '#0d1416', // Almost black cool gray
	},
} as const;

// ============================================================================
// Spacing Tokens - 4px grid system
// ============================================================================

export const spacing = {
	0: '0',
	px: '1px',
	0.5: '0.125rem', // 2px
	1: '0.25rem', // 4px
	1.5: '0.375rem', // 6px
	2: '0.5rem', // 8px
	2.5: '0.625rem', // 10px
	3: '0.75rem', // 12px
	3.5: '0.875rem', // 14px
	4: '1rem', // 16px
	5: '1.25rem', // 20px
	6: '1.5rem', // 24px
	7: '1.75rem', // 28px
	8: '2rem', // 32px
	9: '2.25rem', // 36px
	10: '2.5rem', // 40px
	11: '2.75rem', // 44px
	12: '3rem', // 48px
	14: '3.5rem', // 56px
	16: '4rem', // 64px
	20: '5rem', // 80px
	24: '6rem', // 96px
	28: '7rem', // 112px
	32: '8rem', // 128px
	36: '9rem', // 144px
	40: '10rem', // 160px
	44: '11rem', // 176px
	48: '12rem', // 192px
	52: '13rem', // 208px
	56: '14rem', // 224px
	60: '15rem', // 240px
	64: '16rem', // 256px
	72: '18rem', // 288px
	80: '20rem', // 320px
	96: '24rem', // 384px
} as const;

// ============================================================================
// Typography Tokens
// ============================================================================

export const typography = {
	fontFamily: {
		sans: [
			'-apple-system',
			'BlinkMacSystemFont',
			'"Segoe UI"',
			'Roboto',
			'Oxygen',
			'Ubuntu',
			'Cantarell',
			'"Open Sans"',
			'"Helvetica Neue"',
			'sans-serif',
		],
		mono: [
			'ui-monospace',
			'SFMono-Regular',
			'"SF Mono"',
			'Menlo',
			'Consolas',
			'"Liberation Mono"',
			'monospace',
		],
	},
	fontSize: {
		xs: ['0.75rem', { lineHeight: '1rem' }], // 12px
		sm: ['0.875rem', { lineHeight: '1.25rem' }], // 14px
		base: ['1rem', { lineHeight: '1.5rem' }], // 16px
		lg: ['1.125rem', { lineHeight: '1.75rem' }], // 18px
		xl: ['1.25rem', { lineHeight: '1.75rem' }], // 20px
		'2xl': ['1.5rem', { lineHeight: '2rem' }], // 24px
		'3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
		'4xl': ['2.25rem', { lineHeight: '2.5rem' }], // 36px
		'5xl': ['3rem', { lineHeight: '1' }], // 48px
		'6xl': ['3.75rem', { lineHeight: '1' }], // 60px
		'7xl': ['4.5rem', { lineHeight: '1' }], // 72px
		'8xl': ['6rem', { lineHeight: '1' }], // 96px
		'9xl': ['8rem', { lineHeight: '1' }], // 128px
	},
	fontWeight: {
		thin: '100',
		extralight: '200',
		light: '300',
		normal: '400',
		medium: '500',
		semibold: '600',
		bold: '700',
		extrabold: '800',
		black: '900',
	},
	lineHeight: {
		none: '1',
		tight: '1.25',
		snug: '1.375',
		normal: '1.5',
		relaxed: '1.625',
		loose: '2',
	},
	letterSpacing: {
		tighter: '-0.05em',
		tight: '-0.025em',
		normal: '0em',
		wide: '0.025em',
		wider: '0.05em',
		widest: '0.1em',
	},
} as const;

// ============================================================================
// Shadow Tokens - Elevation system
// ============================================================================

export const shadows = {
	sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
	DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
	md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
	lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
	xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
	'2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
	inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
	none: 'none',
} as const;

// ============================================================================
// Border Radius Tokens
// ============================================================================

export const borderRadius = {
	none: '0',
	sm: '0.125rem', // 2px
	DEFAULT: '0.25rem', // 4px
	md: '0.375rem', // 6px
	lg: '0.5rem', // 8px
	xl: '0.75rem', // 12px
	'2xl': '1rem', // 16px
	'3xl': '1.5rem', // 24px
	full: '9999px',
} as const;

// ============================================================================
// Transition Tokens
// ============================================================================

export const transitions = {
	duration: {
		75: '75ms',
		100: '100ms',
		150: '150ms',
		200: '200ms',
		300: '300ms',
		500: '500ms',
		700: '700ms',
		1000: '1000ms',
		// Progressive disclosure animations
		reveal: '400ms', // Staggered reveal animations
		typing: '150ms', // Typing indicator pulse
		progress: '300ms', // Progress bar animations
	},
	timing: {
		DEFAULT: 'cubic-bezier(0.4, 0, 0.2, 1)',
		linear: 'linear',
		in: 'cubic-bezier(0.4, 0, 1, 1)',
		out: 'cubic-bezier(0, 0, 0.2, 1)',
		'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
		// Smooth, natural easing for UX animations
		smooth: 'cubic-bezier(0.4, 0, 0.2, 1)',
		bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
	},
} as const;

// ============================================================================
// Z-Index Tokens - Layering system
// ============================================================================

export const zIndex = {
	0: '0',
	10: '10',
	20: '20',
	30: '30',
	40: '40',
	50: '50',
	auto: 'auto',
	// Named layers
	dropdown: '1000',
	sticky: '1020',
	fixed: '1030',
	modalBackdrop: '1040',
	modal: '1050',
	popover: '1060',
	tooltip: '1070',
} as const;

// ============================================================================
// Gradient Tokens - For progressive disclosure and visual appeal
// ============================================================================

export const gradients = {
	brand: 'linear-gradient(135deg, #00C8B3 0%, #00a594 100%)',
	brandSubtle: 'linear-gradient(135deg, #e6faf8 0%, #b3f0ea 100%)',
	accent: 'linear-gradient(135deg, #ff6b47 0%, #f04e2a 100%)',
	success: 'linear-gradient(135deg, #10b05e 0%, #059a4f 100%)',
	shimmer: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
	progress: 'linear-gradient(90deg, #00C8B3 0%, #1ad3c0 50%, #00C8B3 100%)',
} as const;

// ============================================================================
// Animation Tokens - For progressive disclosure
// ============================================================================

export const animations = {
	// Typing indicator pulse
	pulse: 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
	// Spinner rotation
	spin: 'spin 1s linear infinite',
	// Slide in animations
	slideInFromRight: 'slideInFromRight 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
	slideInFromLeft: 'slideInFromLeft 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
	slideInFromTop: 'slideInFromTop 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
	slideInFromBottom: 'slideInFromBottom 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
	// Fade animations
	fadeIn: 'fadeIn 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
	fadeOut: 'fadeOut 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
	// Shimmer effect for loading states
	shimmer: 'shimmer 2s infinite',
} as const;

// ============================================================================
// Export all tokens
// ============================================================================

export const tokens = {
	colors,
	spacing,
	typography,
	shadows,
	borderRadius,
	transitions,
	zIndex,
	gradients,
	animations,
} as const;

export default tokens;
