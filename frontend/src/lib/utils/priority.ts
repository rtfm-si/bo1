/**
 * Priority utility - wraps eventTokens.actionPriority from design tokens
 */
import { eventTokens } from '$lib/design/tokens';

interface PriorityConfig {
	label: string;
	bg: string;
	border: string;
	text: string;
	badge: string;
}

const fallback: PriorityConfig = {
	label: 'Unknown',
	bg: 'bg-neutral-100 dark:bg-neutral-800',
	border: 'border-neutral-200 dark:border-neutral-700',
	text: 'text-neutral-600 dark:text-neutral-400',
	badge: 'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400',
};

/**
 * Get priority display config from design tokens with fallback
 */
export function getPriorityConfig(priority: string): PriorityConfig {
	const key = priority?.toLowerCase() as keyof typeof eventTokens.actionPriority;
	return eventTokens.actionPriority[key] ?? fallback;
}

/**
 * Get priority badge classes (bg + text combined)
 */
export function getPriorityBadgeClass(priority: string): string {
	return getPriorityConfig(priority).badge;
}

/**
 * Get Badge component variant for a priority level
 */
export function getPriorityBadgeVariant(priority: string): 'error' | 'warning' | 'success' | 'neutral' {
	const key = priority?.toLowerCase();
	if (key === 'critical' || key === 'high') return 'error';
	if (key === 'medium') return 'warning';
	if (key === 'low') return 'success';
	return 'neutral';
}
