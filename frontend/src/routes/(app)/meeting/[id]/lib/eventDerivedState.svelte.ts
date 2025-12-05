/**
 * Event Derived State - Computed values based on events
 * Extracts key events and conditions from the event stream
 */

import type { SSEEvent } from '$lib/api/sse-events';

export interface EventDerivedStateConfig {
	getEvents: () => SSEEvent[];
	getSession: () => { status: string } | null;
	getSubProblemTabsLength: () => number;
}

/**
 * Creates event-derived state manager
 */
export function createEventDerivedState(config: EventDerivedStateConfig) {
	const { getEvents, getSession, getSubProblemTabsLength } = config;

	// ============================================================================
	// DERIVED VALUES
	// ============================================================================

	const metaSynthesisEvent = $derived.by(() => {
		const events = getEvents();
		return events.find((e) => e.event_type === 'meta_synthesis_complete');
	});

	const synthesisCompleteEvent = $derived.by(() => {
		const events = getEvents();
		return events.find((e) => e.event_type === 'synthesis_complete');
	});

	const subProblemCompleteEvents = $derived.by(() => {
		const events = getEvents();
		return events.filter((e) => e.event_type === 'subproblem_complete');
	});

	const decompositionEvent = $derived.by(() => {
		const events = getEvents();
		return events.find((e) => e.event_type === 'decomposition_complete');
	});

	const clarificationRequiredEvent = $derived.by(() => {
		const events = getEvents();
		return events.find((e) => e.event_type === 'clarification_required');
	});

	const showConclusionTab = $derived.by(() => {
		return (
			metaSynthesisEvent !== undefined ||
			synthesisCompleteEvent !== undefined ||
			(subProblemCompleteEvents.length > 0 &&
				subProblemCompleteEvents.some((e) => e.data.synthesis)) ||
			getSession()?.status === 'completed'
		);
	});

	const clarificationQuestions = $derived.by(() => {
		return clarificationRequiredEvent?.data?.questions as
			| Array<{ question: string; reason?: string; priority?: string }>
			| undefined;
	});

	const needsClarification = $derived.by(() => {
		const session = getSession();
		return (
			clarificationRequiredEvent !== undefined &&
			session?.status === 'active' &&
			clarificationQuestions !== undefined
		);
	});

	const shouldHideDecomposition = $derived.by(() => {
		return getSubProblemTabsLength() > 1;
	});

	return {
		// Reactive getters
		get metaSynthesisEvent() {
			return metaSynthesisEvent;
		},
		get synthesisCompleteEvent() {
			return synthesisCompleteEvent;
		},
		get subProblemCompleteEvents() {
			return subProblemCompleteEvents;
		},
		get decompositionEvent() {
			return decompositionEvent;
		},
		get clarificationRequiredEvent() {
			return clarificationRequiredEvent;
		},
		get showConclusionTab() {
			return showConclusionTab;
		},
		get clarificationQuestions() {
			return clarificationQuestions;
		},
		get needsClarification() {
			return needsClarification;
		},
		get shouldHideDecomposition() {
			return shouldHideDecomposition;
		},
	};
}

export type EventDerivedState = ReturnType<typeof createEventDerivedState>;
