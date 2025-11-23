/**
 * Design Tokens - Central source of truth for all design values
 * Used by Tailwind config and theme system
 */

// ============================================================================
// Color Tokens - Minimalist 3-Context System (Notion/Linear/Anthropic-inspired)
// ============================================================================

export const colors = {
	// NEUTRAL CONTEXT - Base colors for text, borders, backgrounds
	// Used for: All non-interactive UI elements, card backgrounds, dividers
	neutral: {
		50: 'hsl(210 10% 98%)',   // Lightest background (cards, modals)
		100: 'hsl(210 10% 96%)',  // Card backgrounds
		200: 'hsl(210 10% 90%)',  // Borders, dividers
		300: 'hsl(210 8% 80%)',   // Muted borders
		400: 'hsl(210 8% 65%)',   // Disabled text
		500: 'hsl(210 8% 50%)',   // Secondary text (meta info)
		600: 'hsl(210 10% 40%)',  // Secondary headings
		700: 'hsl(210 12% 30%)',  // Primary text
		800: 'hsl(210 15% 20%)',  // Emphasized text
		900: 'hsl(210 20% 10%)',  // Headings, strong emphasis
		950: 'hsl(210 20% 5%)',   // Maximum contrast
	},

	// BRAND CONTEXT - Primary brand color (teal #00C8B3)
	// Used ONLY for: CTAs, active states, brand moments, primary actions
	brand: {
		50: 'hsl(174 70% 97%)',   // Lightest teal background
		100: 'hsl(174 65% 90%)',  // Subtle hover backgrounds
		200: 'hsl(174 60% 80%)',  // Light accents
		300: 'hsl(174 60% 65%)',  // Medium accents
		400: 'hsl(174 60% 55%)',  // Active states
		500: 'hsl(174 100% 39%)', // PRIMARY BRAND (#00C8B3)
		600: 'hsl(174 100% 33%)', // Hover states
		700: 'hsl(174 100% 26%)', // Pressed states
		800: 'hsl(174 100% 19%)', // Dark brand
		900: 'hsl(174 100% 12%)', // Darkest brand
	},

	// SEMANTIC CONTEXT - Status indicators ONLY
	// Used ONLY for: Success/warning/error states, status badges
	semantic: {
		success: 'hsl(142 76% 36%)',      // Green - success states
		successLight: 'hsl(142 76% 95%)', // Success backgrounds
		warning: 'hsl(38 92% 50%)',       // Amber - warnings
		warningLight: 'hsl(38 92% 95%)',  // Warning backgrounds
		error: 'hsl(0 84% 60%)',          // Red - errors
		errorLight: 'hsl(0 84% 95%)',     // Error backgrounds
		info: 'hsl(200 84% 60%)',         // Blue - informational
		infoLight: 'hsl(200 84% 95%)',    // Info backgrounds
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
// Typography Tokens - 4-Level Hierarchy (Notion/Linear-inspired)
// ============================================================================

export const typography = {
	// Font Families
	fontFamily: {
		sans: [
			'Inter',
			'-apple-system',
			'BlinkMacSystemFont',
			'"Segoe UI"',
			'system-ui',
			'sans-serif',
		],
		mono: [
			'"JetBrains Mono"',
			'Consolas',
			'ui-monospace',
			'monospace',
		],
	},

	// Font Sizes - 4 LEVELS ONLY (H1, H2, H3, Body, Small)
	fontSize: {
		h1: '1.875rem',    // 30px - Page title, problem statement
		h2: '1.5rem',      // 24px - Section headers, major events
		h3: '1.25rem',     // 20px - Card titles, expert names
		body: '0.875rem',  // 14px - Body text (matches Linear/Notion)
		small: '0.75rem',  // 12px - Metadata, timestamps, labels
	},

	// Font Weights - 3 ONLY (no bold, extrabold, black)
	fontWeight: {
		normal: '400',   // Body text
		medium: '500',   // Subtle emphasis, navigation
		semibold: '600', // Headings, strong emphasis
	},

	// Line Heights - Optimized for readability
	lineHeight: {
		tight: '1.2',     // H1, H2 headings
		snug: '1.3',      // H3 headings
		normal: '1.5',    // Body text (14px)
		relaxed: '1.6',   // Long-form content (contributions, synthesis)
	},

	// Letter Spacing - Minimal use
	letterSpacing: {
		tight: '-0.025em',  // Large headings only
		normal: '0em',      // Default (most text)
		wide: '0.025em',    // Small caps, labels (sparingly)
	},
} as const;

// Pre-composed Text Styles - Apply these classes consistently
export const textStyles = {
	h1: 'text-[1.875rem] font-semibold leading-tight text-neutral-900 dark:text-white',
	h2: 'text-[1.5rem] font-semibold leading-tight text-neutral-900 dark:text-white',
	h3: 'text-[1.25rem] font-medium leading-snug text-neutral-800 dark:text-neutral-100',
	body: 'text-[0.875rem] font-normal leading-normal text-neutral-700 dark:text-neutral-300',
	bodyRelaxed: 'text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300',
	small: 'text-[0.75rem] font-normal leading-normal text-neutral-500 dark:text-neutral-400',
	label: 'text-[0.75rem] font-medium leading-normal text-neutral-600 dark:text-neutral-400',
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
// Gradient Tokens - MINIMAL USE (functional only, not decorative)
// ============================================================================

export const gradients = {
	// Functional gradients only (progress bars, loading states)
	progress: 'linear-gradient(90deg, hsl(174 100% 39%) 0%, hsl(174 60% 55%) 50%, hsl(174 100% 39%) 100%)',
	shimmer: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
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
// Semantic Component Tokens - Minimal color usage
// ============================================================================

export const eventTokens = {
	// Event card priority (NEUTRAL - no colorful backgrounds)
	priority: {
		major: {
			bg: 'bg-neutral-50 dark:bg-neutral-900/50',
			border: 'border-neutral-300 dark:border-neutral-700',
			text: 'text-neutral-900 dark:text-white',
		},
		supporting: {
			bg: 'bg-neutral-50 dark:bg-neutral-900/50',
			border: 'border-neutral-200 dark:border-neutral-700',
			text: 'text-neutral-900 dark:text-white',
		},
		meta: {
			bg: 'bg-neutral-50/50 dark:bg-neutral-900/30',
			border: 'border-neutral-200 dark:border-neutral-700',
			text: 'text-neutral-600 dark:text-neutral-400',
		},
	},

	// Phase indicators (NO emojis - will use lucide icons)
	phase: {
		decomposition: { label: 'Analysis' },
		persona_selection: { label: 'Expert Selection' },
		initial_round: { label: 'Initial Discussion' },
		discussion: { label: 'Discussion' },
		voting: { label: 'Recommendations' },
		synthesis: { label: 'Synthesis' },
		complete: { label: 'Complete' },
	},

	// Consensus levels (semantic colors ONLY for status)
	consensus: {
		strong: {
			bg: 'bg-[hsl(142,76%,95%)] dark:bg-[hsl(142,76%,20%)]',
			text: 'text-[hsl(142,76%,36%)] dark:text-[hsl(142,76%,60%)]',
			label: 'Strong',
		},
		moderate: {
			bg: 'bg-[hsl(38,92%,95%)] dark:bg-[hsl(38,92%,20%)]',
			text: 'text-[hsl(38,92%,50%)] dark:text-[hsl(38,92%,70%)]',
			label: 'Moderate',
		},
		weak: {
			bg: 'bg-neutral-100 dark:bg-neutral-800',
			text: 'text-neutral-600 dark:text-neutral-400',
			label: 'Weak',
		},
		unknown: {
			bg: 'bg-neutral-100 dark:bg-neutral-800',
			text: 'text-neutral-500 dark:text-neutral-500',
			label: 'Unknown',
		},
	},

	// Action priority (semantic colors for status ONLY)
	actionPriority: {
		critical: {
			label: 'Critical',
			bg: 'bg-[hsl(0,84%,95%)] dark:bg-[hsl(0,84%,20%)]',
			border: 'border-[hsl(0,84%,60%)] dark:border-[hsl(0,84%,40%)]',
			text: 'text-[hsl(0,84%,40%)] dark:text-[hsl(0,84%,70%)]',
			badge: 'bg-[hsl(0,84%,95%)] text-[hsl(0,84%,40%)] dark:bg-[hsl(0,84%,20%)] dark:text-[hsl(0,84%,70%)]',
		},
		high: {
			label: 'High',
			bg: 'bg-[hsl(38,92%,95%)] dark:bg-[hsl(38,92%,20%)]',
			border: 'border-[hsl(38,92%,50%)] dark:border-[hsl(38,92%,40%)]',
			text: 'text-[hsl(38,92%,40%)] dark:text-[hsl(38,92%,70%)]',
			badge: 'bg-[hsl(38,92%,95%)] text-[hsl(38,92%,40%)] dark:bg-[hsl(38,92%,20%)] dark:text-[hsl(38,92%,70%)]',
		},
		medium: {
			label: 'Medium',
			bg: 'bg-neutral-100 dark:bg-neutral-800',
			border: 'border-neutral-300 dark:border-neutral-600',
			text: 'text-neutral-700 dark:text-neutral-300',
			badge: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
		},
		low: {
			label: 'Low',
			bg: 'bg-neutral-50 dark:bg-neutral-900/50',
			border: 'border-neutral-200 dark:border-neutral-700',
			text: 'text-neutral-600 dark:text-neutral-400',
			badge: 'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400',
		},
	},

	// Insight sections (NO emojis - will use lucide icons)
	insights: {
		analyzing: { label: 'Analysis' },
		insight: { label: 'Key Insight' },
		concern: { label: 'Concerns' },
		question: { label: 'Questions' },
	},

	// Chart colors (using new brand system)
	charts: {
		cost: {
			primary: 'hsl(174 100% 39%)',    // brand-500
			secondary: 'hsl(174 60% 55%)',   // brand-400
			background: 'hsla(174 100% 39% / 0.1)',
		},
		convergence: {
			line: 'hsl(200 84% 60%)',        // semantic.info
			threshold: 'hsl(38 92% 50%)',    // semantic.warning
			area: 'hsla(200 84% 60% / 0.2)',
			grid: 'hsla(210 8% 50% / 0.2)',  // neutral-500
		},
		progress: {
			complete: 'hsl(142 76% 36%)',    // semantic.success
			current: 'hsl(174 100% 39%)',    // brand-500
			pending: 'hsl(210 8% 50%)',      // neutral-500
		},
	},
} as const;

// ============================================================================
// Component-Specific Spacing (for compact layouts)
// ============================================================================

export const componentSpacing = {
	// Card spacing
	card: {
		padding: {
			sm: 'p-3',
			md: 'p-4',
			lg: 'p-6',
		},
		gap: {
			sm: 'gap-2',
			md: 'gap-3',
			lg: 'gap-4',
		},
	},
	// Stack spacing
	stack: {
		tight: 'space-y-2',
		normal: 'space-y-3',
		relaxed: 'space-y-4',
		loose: 'space-y-6',
	},
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
	eventTokens,
	componentSpacing,
} as const;

export default tokens;
