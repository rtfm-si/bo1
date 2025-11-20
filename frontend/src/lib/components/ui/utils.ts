/**
 * Shared Component Utilities
 * Common helpers for component variant and style management
 */

import { spacing, shadows, borderRadius } from '$lib/design/tokens';

/**
 * Combines class strings, filtering out falsy values
 */
export function cn(...classes: (string | false | null | undefined)[]): string {
	return classes.filter(Boolean).join(' ');
}

/**
 * Common component size tokens
 */
export const componentSizes = {
	xs: 'xs',
	sm: 'sm',
	md: 'md',
	lg: 'lg',
	xl: 'xl',
} as const;

export type ComponentSize = keyof typeof componentSizes;

/**
 * Common semantic color variants
 */
export const semanticVariants = {
	brand: 'brand',
	accent: 'accent',
	success: 'success',
	warning: 'warning',
	error: 'error',
	info: 'info',
	neutral: 'neutral',
} as const;

export type SemanticVariant = keyof typeof semanticVariants;

/**
 * Generate responsive padding classes
 */
export function paddingClasses(size: 'none' | 'sm' | 'md' | 'lg'): string {
	const paddingMap = {
		none: '',
		sm: 'p-4',
		md: 'p-6',
		lg: 'p-8',
	};
	return paddingMap[size];
}

/**
 * Generate responsive text size classes
 */
export function textSizeClasses(size: ComponentSize): string {
	const sizeMap = {
		xs: 'text-xs',
		sm: 'text-sm',
		md: 'text-base',
		lg: 'text-lg',
		xl: 'text-xl',
	};
	return sizeMap[size];
}

/**
 * Design Token Utilities
 */

/**
 * Get spacing value by token key
 */
export function getSpacing(key: keyof typeof spacing): string {
	return spacing[key];
}

/**
 * Get shadow value by token key
 */
export function getShadow(key: keyof typeof shadows): string {
	return shadows[key];
}

/**
 * Get border radius value by token key
 */
export function getBorderRadius(key: keyof typeof borderRadius): string {
	return borderRadius[key];
}

/**
 * Get spacing value in pixels for display purposes
 */
export function getSpacingInPixels(key: keyof typeof spacing): string {
	const value = spacing[key];
	if (value === '0') return '0px';
	if (value === '1px') return '1px';

	// Convert rem to pixels (assuming 1rem = 16px)
	const remMatch = value.match(/^([\d.]+)rem$/);
	if (remMatch) {
		const pixels = parseFloat(remMatch[1]) * 16;
		return `${pixels}px`;
	}

	return value;
}
