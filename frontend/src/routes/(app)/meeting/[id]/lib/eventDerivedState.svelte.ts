/**
 * Event Derived State - Computed values based on events
 * Extracts key events and conditions from the event stream
 */

import type { SSEEvent } from '$lib/api/sse-events';

export interface EventDerivedStateConfig {
	getEvents: () => SSEEvent[];
	getSession: () => { status: string; phase?: string | null } | null;
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
		// Get the LAST clarification_required event (most recent questions)
		// This handles the case where user partially answers and session re-pauses
		const clarificationEvents = events.filter((e) => e.event_type === 'clarification_required');
		return clarificationEvents.length > 0 ? clarificationEvents[clarificationEvents.length - 1] : undefined;
	});

	// Context insufficient event (Option D+E Hybrid)
	const contextInsufficientEvent = $derived.by(() => {
		const events = getEvents();
		// Get the LAST context_insufficient event
		const contextEvents = events.filter((e) => e.event_type === 'context_insufficient');
		return contextEvents.length > 0 ? contextEvents[contextEvents.length - 1] : undefined;
	});

	const showConclusionTab = $derived.by(() => {
		const session = getSession();
		const tabsLength = getSubProblemTabsLength();

		// For multi-sub-problem meetings, only show conclusion when:
		// 1. Meta-synthesis is available (all sub-problems done + combined), OR
		// 2. Session is explicitly completed
		// Don't show conclusion tab early just because one sub-problem finished
		if (tabsLength > 1) {
			return metaSynthesisEvent !== undefined || session?.status === 'completed';
		}

		// For single sub-problem (atomic problem), show conclusion when:
		// 1. Synthesis is complete, OR
		// 2. Session is completed
		return (
			synthesisCompleteEvent !== undefined ||
			(subProblemCompleteEvents.length > 0 &&
				subProblemCompleteEvents.some((e) => e.data.synthesis)) ||
			session?.status === 'completed'
		);
	});

	const clarificationQuestions = $derived.by(() => {
		return clarificationRequiredEvent?.data?.questions as
			| Array<{ question: string; reason?: string; priority?: string }>
			| undefined;
	});

	const needsClarification = $derived.by(() => {
		const session = getSession();
		// Show clarification form when session is paused for clarification
		// Status can be 'active' (legacy) or 'paused' (new behavior)
		const isPausedForClarification =
			session?.status === 'paused' && session?.phase === 'clarification_needed';

		// Primary: phase-based detection
		if (isPausedForClarification) {
			return (
				clarificationRequiredEvent !== undefined && clarificationQuestions !== undefined
			);
		}

		// Fallback: event-based detection when phase not available (e.g., Redis TTL expired)
		// If session is paused and we have clarification event, show the form
		if (session?.status === 'paused' && clarificationRequiredEvent !== undefined) {
			return clarificationQuestions !== undefined;
		}

		// Legacy: active session with clarification event
		return (
			clarificationRequiredEvent !== undefined &&
			session?.status === 'active' &&
			clarificationQuestions !== undefined
		);
	});

	// Context insufficient - show modal when we have the event and session is paused
	const needsContextChoice = $derived.by(() => {
		const session = getSession();
		// Show modal when session is paused for context choice
		const isPausedForContext =
			session?.status === 'paused' && session?.phase === 'context_insufficient';
		return contextInsufficientEvent !== undefined && isPausedForContext;
	});

	const shouldHideDecomposition = $derived.by(() => {
		return getSubProblemTabsLength() > 1;
	});

	// P2-004: Get personas by sub-problem index from persona_selected events
	const personasBySubProblem = $derived.by(() => {
		const events = getEvents();
		const personaEvents = events.filter((e) => e.event_type === 'persona_selected');
		const result: Record<number, any[]> = {};

		for (const event of personaEvents) {
			// Type assertion: event.data contains sub_problem_index as number
			const subProblemIndex = (event.data as { sub_problem_index?: number }).sub_problem_index ?? 0;
			if (!result[subProblemIndex]) {
				result[subProblemIndex] = [];
			}
			// Type assertion: event.data contains persona object
			const persona = (event.data as { persona: any }).persona;
			result[subProblemIndex].push(persona);
		}

		return result;
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
		get contextInsufficientEvent() {
			return contextInsufficientEvent;
		},
		get showConclusionTab() {
			return showConclusionTab;
		},
		get clarificationQuestions() {
			return clarificationQuestions;
		},
		get personasBySubProblem() {
			return personasBySubProblem;
		},
		get needsClarification() {
			return needsClarification;
		},
		get needsContextChoice() {
			return needsContextChoice;
		},
		get shouldHideDecomposition() {
			return shouldHideDecomposition;
		},
	};
}

export type EventDerivedState = ReturnType<typeof createEventDerivedState>;
