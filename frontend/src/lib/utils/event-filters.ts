/**
 * Event filtering utilities
 * Centralizes repeated event filtering logic across components
 */

import type { SSEEvent } from '$lib/api/sse-events';

/**
 * Helper to safely extract sub_problem_index from event data
 * Many event types include this field for tab filtering
 */
function getSubProblemIndex(data: unknown): number | undefined {
	if (data && typeof data === 'object' && 'sub_problem_index' in data) {
		const idx = (data as Record<string, unknown>).sub_problem_index;
		return typeof idx === 'number' ? idx : undefined;
	}
	return undefined;
}

/**
 * Filter events by type and optional sub-problem index
 */
export function filterEventsByType(
	events: SSEEvent[],
	eventType: string,
	activeSubProblemIndex: number | null = null,
	totalSubProblems: number = 1
): SSEEvent[] {
	return events.filter((e) => {
		if (e.event_type !== eventType) return false;

		// No sub-problem filtering needed
		if (totalSubProblems <= 1 || activeSubProblemIndex === null) {
			return true;
		}

		// Filter by active sub-problem
		const eventSubIndex = getSubProblemIndex(e.data);
		return eventSubIndex === activeSubProblemIndex;
	});
}

/**
 * Filter events by multiple types
 */
export function filterEventsByTypes(
	events: SSEEvent[],
	eventTypes: string[],
	activeSubProblemIndex: number | null = null,
	totalSubProblems: number = 1
): SSEEvent[] {
	return events.filter((e) => {
		if (!eventTypes.includes(e.event_type)) return false;

		// No sub-problem filtering needed
		if (totalSubProblems <= 1 || activeSubProblemIndex === null) {
			return true;
		}

		// Filter by active sub-problem
		const eventSubIndex = getSubProblemIndex(e.data);
		return eventSubIndex === activeSubProblemIndex;
	});
}

/**
 * Get latest event of a specific type
 */
export function getLatestEvent(
	events: SSEEvent[],
	eventType: string,
	activeSubProblemIndex: number | null = null,
	totalSubProblems: number = 1
): SSEEvent | null {
	const filtered = filterEventsByType(events, eventType, activeSubProblemIndex, totalSubProblems);
	return filtered.length > 0 ? filtered[filtered.length - 1] : null;
}

/**
 * Count events by type
 */
export function countEventsByType(
	events: SSEEvent[],
	eventType: string,
	activeSubProblemIndex: number | null = null,
	totalSubProblems: number = 1
): number {
	return filterEventsByType(events, eventType, activeSubProblemIndex, totalSubProblems).length;
}

/**
 * Check if an event of a specific type exists
 */
export function hasEventOfType(
	events: SSEEvent[],
	eventType: string,
	activeSubProblemIndex: number | null = null,
	totalSubProblems: number = 1
): boolean {
	return (
		filterEventsByType(events, eventType, activeSubProblemIndex, totalSubProblems).length > 0
	);
}

/**
 * Filter events by sub-problem index only (for mixed event types)
 */
export function filterEventsBySubProblem(
	events: SSEEvent[],
	activeSubProblemIndex: number | null,
	totalSubProblems: number = 1
): SSEEvent[] {
	// If single sub-problem OR no active tab, show all events
	if (totalSubProblems <= 1 || activeSubProblemIndex === null) {
		return events;
	}

	// Filter to active sub-problem only
	return events.filter((e) => {
		const eventSubIndex = getSubProblemIndex(e.data);
		return eventSubIndex === activeSubProblemIndex;
	});
}
