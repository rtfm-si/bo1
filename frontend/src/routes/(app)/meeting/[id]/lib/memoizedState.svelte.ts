/**
 * Memoized State - Debounced event grouping and derived calculations
 * Optimizes expensive computations with caching and debouncing
 */

import type { SSEEvent } from '$lib/api/sse-events';
import { DEBOUNCE_CRITICAL_MS, DEBOUNCE_NORMAL_MS } from '$lib/config/constants';
import { groupEvents, indexEventsBySubProblem, type EventGroup } from './eventGrouping';
import { buildSubProblemTabs, calculateSubProblemProgress, type SubProblemTab } from './subProblemTabs';

export interface MemoizedStateConfig {
	getEvents: () => SSEEvent[];
	getSession: () => { status: string } | null;
	getDebugMode: () => boolean;
}

/**
 * Creates memoized state manager for expensive calculations
 */
export function createMemoizedState(config: MemoizedStateConfig) {
	const { getEvents, getSession, getDebugMode } = config;

	// ============================================================================
	// SUB-PROBLEM PROGRESS CACHE
	// ============================================================================

	let subProblemProgressCache = $state<{ current: number; total: number } | null>(null);
	let lastEventCountForProgress = $state(0);

	function updateSubProblemProgress() {
		const events = getEvents();
		if (events.length !== lastEventCountForProgress) {
			subProblemProgressCache = calculateSubProblemProgress(events);
			lastEventCountForProgress = events.length;
		}
	}

	// ============================================================================
	// GROUPED EVENTS CACHE (Debounced)
	// ============================================================================

	let groupedEventsCache = $state<EventGroup[]>([]);
	let lastEventCountForGrouping = $state(0);
	let groupingDebounceTimeout: ReturnType<typeof setTimeout> | null = null;

	function recalculateGroupedEvents(delay: number = DEBOUNCE_NORMAL_MS) {
		if (groupingDebounceTimeout) clearTimeout(groupingDebounceTimeout);
		groupingDebounceTimeout = setTimeout(() => {
			const events = getEvents();
			groupedEventsCache = groupEvents(events, getDebugMode());
			lastEventCountForGrouping = events.length;
		}, delay);
	}

	function updateGroupedEvents() {
		const events = getEvents();
		const session = getSession();

		if (events.length !== lastEventCountForGrouping) {
			const isCompleted = session?.status === 'completed' || session?.status === 'failed';

			if (isCompleted) {
				// Immediate calculation for completed sessions
				groupedEventsCache = groupEvents(events, getDebugMode());
				lastEventCountForGrouping = events.length;
			} else {
				// Debounced calculation for active sessions
				const lastEvent = events[events.length - 1];
				const isCritical =
					lastEvent?.event_type === 'persona_selection_complete' ||
					lastEvent?.event_type === 'round_started' ||
					lastEvent?.event_type === 'persona_selected';
				recalculateGroupedEvents(isCritical ? DEBOUNCE_CRITICAL_MS : DEBOUNCE_NORMAL_MS);
			}
		}
	}

	function forceGroupedEventsUpdate() {
		const events = getEvents();
		if (groupingDebounceTimeout) clearTimeout(groupingDebounceTimeout);
		groupedEventsCache = groupEvents(events, getDebugMode());
		lastEventCountForGrouping = events.length;
	}

	// ============================================================================
	// EVENT INDEX BY SUB-PROBLEM (Debounced)
	// ============================================================================

	let eventsBySubProblemCache = $state(new Map<number, SSEEvent[]>());
	let lastEventCountForIndex = $state(0);
	let indexDebounceTimeout: ReturnType<typeof setTimeout> | null = null;

	function recalculateEventIndex() {
		if (indexDebounceTimeout) clearTimeout(indexDebounceTimeout);
		indexDebounceTimeout = setTimeout(() => {
			const events = getEvents();
			eventsBySubProblemCache = indexEventsBySubProblem(events);
			lastEventCountForIndex = events.length;
		}, 200);
	}

	function updateEventIndex() {
		const events = getEvents();
		const session = getSession();

		if (events.length !== lastEventCountForIndex) {
			const isCompleted = session?.status === 'completed' || session?.status === 'failed';

			if (isCompleted) {
				eventsBySubProblemCache = indexEventsBySubProblem(events);
				lastEventCountForIndex = events.length;
			} else {
				recalculateEventIndex();
			}
		}
	}

	// ============================================================================
	// SUB-PROBLEM TABS CACHE
	// ============================================================================

	let subProblemTabsCache = $state<SubProblemTab[]>([]);
	let lastEventCountForTabs = $state(0);

	function updateSubProblemTabs() {
		const events = getEvents();
		if (events.length !== lastEventCountForTabs) {
			subProblemTabsCache = buildSubProblemTabs(events, eventsBySubProblemCache);
			lastEventCountForTabs = events.length;
		}
	}

	// ============================================================================
	// COMBINED UPDATE (call this when events change)
	// ============================================================================

	function updateAll() {
		updateSubProblemProgress();
		updateGroupedEvents();
		updateEventIndex();
		updateSubProblemTabs();
	}

	function cleanup() {
		if (groupingDebounceTimeout) clearTimeout(groupingDebounceTimeout);
		if (indexDebounceTimeout) clearTimeout(indexDebounceTimeout);
	}

	return {
		// Reactive getters
		get subProblemProgress() {
			return subProblemProgressCache;
		},
		get groupedEvents() {
			return groupedEventsCache;
		},
		get eventsBySubProblem() {
			return eventsBySubProblemCache;
		},
		get subProblemTabs() {
			return subProblemTabsCache;
		},

		// Methods
		updateSubProblemProgress,
		updateGroupedEvents,
		forceGroupedEventsUpdate,
		updateEventIndex,
		updateSubProblemTabs,
		updateAll,
		cleanup,
	};
}

export type MemoizedState = ReturnType<typeof createMemoizedState>;
