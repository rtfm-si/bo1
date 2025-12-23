/**
 * Event Derived State - Computed values based on events
 * Extracts key events and conditions from the event stream
 */

import type { SSEEvent, SubproblemCompletePayload, ClarificationRequiredPayload, PersonaSelectedPayload, DecompositionCompletePayload } from '$lib/api/sse-events';
import { isSubproblemCompleteEvent, isClarificationRequiredEvent, isPersonaSelectedEvent, isDecompositionEvent } from '$lib/api/sse-events';
import type { SubProblemResult } from '$lib/components/meeting';

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
		return events.filter(isSubproblemCompleteEvent);
	});

	const decompositionEvent = $derived.by(() => {
		const events = getEvents();
		return events.find((e) => e.event_type === 'decomposition_complete');
	});

	const clarificationRequiredEvent = $derived.by(() => {
		const events = getEvents();
		// Get the LAST clarification_required event (most recent questions)
		// This handles the case where user partially answers and session re-pauses
		const clarificationEvents = events.filter(isClarificationRequiredEvent);
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
		// Type is already narrowed by filter above
		return clarificationRequiredEvent?.data.questions;
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
		const personaEvents = events.filter(isPersonaSelectedEvent);
		const result: Record<number, PersonaSelectedPayload['persona'][]> = {};

		for (const event of personaEvents) {
			const subProblemIndex = event.data.sub_problem_index ?? 0;
			if (!result[subProblemIndex]) {
				result[subProblemIndex] = [];
			}
			result[subProblemIndex].push(event.data.persona);
		}

		return result;
	});

	// Partial success: Extract sub-problem results for MeetingError display
	const subProblemResultsForPartialSuccess = $derived.by((): SubProblemResult[] => {
		const events = getEvents();

		// Get decomposition to know all sub-problems
		const decomposition = events.find(isDecompositionEvent);
		if (!decomposition) return [];

		const decompositionData = decomposition.data as DecompositionCompletePayload;
		const subProblems = decompositionData.sub_problems || [];

		// Get completed sub-problems
		const completedEvents = events.filter(isSubproblemCompleteEvent);
		const completedMap = new Map<number, SubproblemCompletePayload>();
		for (const event of completedEvents) {
			completedMap.set(event.data.sub_problem_index, event.data);
		}

		// Check for subproblem_started events to detect in-progress
		const startedIndices = new Set<number>();
		for (const event of events) {
			if (event.event_type === 'subproblem_started') {
				const data = event.data as { sub_problem_index: number };
				startedIndices.add(data.sub_problem_index);
			}
		}

		// Build results array with status for each sub-problem
		return subProblems.map((sp, index): SubProblemResult => {
			const completed = completedMap.get(index);
			if (completed) {
				return {
					id: sp.id,
					goal: sp.goal,
					synthesis: completed.synthesis || '',
					status: 'complete',
				};
			}

			// Check if sub-problem has started but not completed
			if (startedIndices.has(index)) {
				return {
					id: sp.id,
					goal: sp.goal,
					synthesis: '',
					status: 'in_progress',
				};
			}

			// Check if this is the failed sub-problem (meeting_failed event)
			const meetingFailedEvent = events.find(e => e.event_type === 'meeting_failed');
			if (meetingFailedEvent) {
				const failedData = meetingFailedEvent.data as { failed_ids?: string[] };
				if (failedData.failed_ids?.includes(sp.id)) {
					return {
						id: sp.id,
						goal: sp.goal,
						synthesis: '',
						status: 'failed',
					};
				}
			}

			return {
				id: sp.id,
				goal: sp.goal,
				synthesis: '',
				status: 'pending',
			};
		});
	});

	// Total sub-problems count from decomposition
	const totalSubProblemsCount = $derived.by(() => {
		const events = getEvents();
		const decomposition = events.find(isDecompositionEvent);
		if (!decomposition) return 0;
		const data = decomposition.data as DecompositionCompletePayload;
		return data.sub_problems?.length || 0;
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
		get subProblemResultsForPartialSuccess() {
			return subProblemResultsForPartialSuccess;
		},
		get totalSubProblemsCount() {
			return totalSubProblemsCount;
		},
	};
}

export type EventDerivedState = ReturnType<typeof createEventDerivedState>;
