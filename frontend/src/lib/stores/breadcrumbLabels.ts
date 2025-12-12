import { writable } from 'svelte/store';

/**
 * Store for dynamic breadcrumb labels.
 * Keys are path patterns (e.g., '/meeting/abc-123') and values are display labels.
 * Child pages set their label on mount and clear on destroy.
 */
export const breadcrumbLabels = writable<Record<string, string>>({});

/**
 * Set a dynamic label for a path
 */
export function setBreadcrumbLabel(path: string, label: string): void {
	breadcrumbLabels.update((labels) => ({ ...labels, [path]: label }));
}

/**
 * Clear a dynamic label for a path
 */
export function clearBreadcrumbLabel(path: string): void {
	breadcrumbLabels.update((labels) => {
		const { [path]: _, ...rest } = labels;
		return rest;
	});
}

/**
 * Truncate text to a max length with ellipsis
 */
export function truncateLabel(text: string, maxLength = 40): string {
	if (text.length <= maxLength) return text;
	return text.slice(0, maxLength - 1).trim() + '…';
}
