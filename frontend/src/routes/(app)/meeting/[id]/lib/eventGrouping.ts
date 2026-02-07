/**
 * Event Grouping - Logic for grouping events by type and round
 * Handles grouping contributions by round and expert panels
 */

import type { SSEEvent } from '$lib/api/sse-events';
import { isSubproblemStartedEvent, isContributionEvent, getSubProblemIndex } from '$lib/api/sse-events';
import { createLogger } from '$lib/utils/debug';

const log = createLogger('ExpertPanel');

export interface EventGroup {
	type: 'single' | 'round' | 'expert_panel';
	event?: SSEEvent;
	events?: SSEEvent[];
	roundNumber?: number;
	subProblemGoal?: string;
	subProblemIndex?: number;
}

// Constants for internal event filtering
export const INTERNAL_EVENTS = ['node_start', 'node_end'];

// Status noise events to hide (UX redesign - these don't provide actionable info)
export const STATUS_NOISE_EVENTS = [
	'state_transition', // Hidden - internal graph node transitions
	'parallel_round_start', // Hidden - internal round orchestration
	'decomposition_started',
	'persona_selection_started',
	// NOTE: persona_selection_complete removed - used as flush trigger for expert panel
	'initial_round_started',
	'facilitator_decision',
	'voting_started',
	'voting_complete',
	'convergence',
	'complete', // Hidden - redundant with SynthesisComplete (renders empty card otherwise)
	'discussion_quality_status', // Hidden - adds noise to timeline
	'working_status', // Hidden - real-time status only, not for historical view
	'synthesis_started', // Hidden - synthesis_complete provides the actual content
	'meta_synthesis_started', // Hidden - meta_synthesis_complete provides the actual content
	'comparison_detected', // Hidden - internal info, not user-facing
	'clarification_required', // Hidden - triggers ClarificationForm UI, not shown as event card
	'contribution_started', // Hidden - lifecycle event, contributions shown via ExpertPerspectiveCard
	'speculative_execution_started', // Hidden - internal orchestration detail
];

/**
 * Filter function to hide internal events and status noise (unless debug mode)
 */
export function shouldShowEvent(eventType: string, debugMode: boolean = false): boolean {
	if (debugMode) return !INTERNAL_EVENTS.includes(eventType);
	return !INTERNAL_EVENTS.includes(eventType) && !STATUS_NOISE_EVENTS.includes(eventType);
}

/**
 * Group events by round and type
 * Returns grouped events for display
 */
export function groupEvents(events: SSEEvent[], debugMode: boolean = false): EventGroup[] {
	const groups: EventGroup[] = [];
	let currentRound: SSEEvent[] = [];
	let currentRoundNumber = 1;
	let currentExpertPanel: SSEEvent[] = [];
	let currentSubProblemGoal: string | undefined = undefined;
	let currentSubProblemIndex: number | undefined = undefined;

	// Pre-compute sub-problems that have received content (for stale waiting removal)
	const subProblemsWithContent = new Set<number>();
	for (const event of events) {
		if (event.event_type === 'contribution' || event.event_type === 'subproblem_complete') {
			const idx = getSubProblemIndex(event);
			if (idx !== undefined) subProblemsWithContent.add(idx);
		}
	}

	// Single iteration with inline filtering (combine filter + group logic)
	for (const event of events) {
		// Handle round_started BEFORE filtering - extract round number, then skip rendering
		if (event.event_type === 'round_started' || event.event_type === 'initial_round_started') {
			const data = event.data as { round_number?: number };
			if (data.round_number) {
				currentRoundNumber = data.round_number;
			}
			continue;
		}

		// Handle persona_selection_complete BEFORE filtering (used as flush trigger)
		if (event.event_type === 'persona_selection_complete') {
			// CRITICAL FIX: Flush expert panel immediately when selection completes
			if (currentExpertPanel.length > 0) {
				log.log('Flushing panel on selection_complete:', {
					expertCount: currentExpertPanel.length,
					subProblemGoal: currentSubProblemGoal
				});

				groups.push({
					type: 'expert_panel',
					events: currentExpertPanel,
					subProblemGoal: currentSubProblemGoal,
					subProblemIndex: currentSubProblemIndex,
				});
				currentExpertPanel = [];
			}
			// Don't add persona_selection_complete as visible event (reduces noise)
			// Just use it as a flush trigger
			continue;
		}

		// Skip internal/noise events (inline filtering)
		if (!shouldShowEvent(event.event_type, debugMode)) {
			continue;
		}

		// Hide stale "waiting" events once content has arrived for that sub-problem
		if ((event.event_type as string) === 'subproblem_waiting') {
			const idx = getSubProblemIndex(event);
			if (idx !== undefined && subProblemsWithContent.has(idx)) continue;
		}

		// Track subproblem_started for context
		if (isSubproblemStartedEvent(event)) {
			currentSubProblemGoal = event.data.goal;
			currentSubProblemIndex = event.data.sub_problem_index;
		}

		// Group persona_selected events
		if (event.event_type === 'persona_selected') {
			const eventSubIndex = getSubProblemIndex(event);

			// Flush if sub-problem changed
			if (currentExpertPanel.length > 0 &&
				eventSubIndex !== undefined &&
				eventSubIndex !== currentSubProblemIndex) {
				groups.push({
					type: 'expert_panel',
					events: currentExpertPanel,
					subProblemGoal: currentSubProblemGoal,
					subProblemIndex: currentSubProblemIndex,
				});
				currentExpertPanel = [];
			}

			currentSubProblemIndex = eventSubIndex;
			currentExpertPanel.push(event);
		} else if (isContributionEvent(event)) {
			// Flush expert panel if any
			if (currentExpertPanel.length > 0) {
				groups.push({
					type: 'expert_panel',
					events: currentExpertPanel,
					subProblemGoal: currentSubProblemGoal,
					subProblemIndex: currentSubProblemIndex,
				});
				currentExpertPanel = [];
			}

			// Get round number from contribution event itself
			const contributionRound = event.data.round;

			// If round number changed, flush previous round with OLD number
			if (contributionRound && contributionRound !== currentRoundNumber && currentRound.length > 0) {
				const previousRound = currentRoundNumber;
				currentRoundNumber = contributionRound;
				groups.push({
					type: 'round',
					events: currentRound,
					roundNumber: previousRound,
				});
				currentRound = [];
			} else if (contributionRound) {
				currentRoundNumber = contributionRound;
			}

			// Add contribution to current round
			currentRound.push(event);
		} else {
			// Flush expert panel if any
			if (currentExpertPanel.length > 0) {
				groups.push({
					type: 'expert_panel',
					events: currentExpertPanel,
					subProblemGoal: currentSubProblemGoal,
					subProblemIndex: currentSubProblemIndex,
				});
				currentExpertPanel = [];
			}
			// Flush contributions if any
			if (currentRound.length > 0) {
				groups.push({
					type: 'round',
					events: currentRound,
					roundNumber: currentRoundNumber,
				});
				currentRound = [];
			}
			// Add non-contribution/non-expert event as single
			groups.push({ type: 'single', event });
		}
	}

	// Flush remaining expert panel
	if (currentExpertPanel.length > 0) {
		log.log('Flushing remaining panel at end of loop:', {
			expertCount: currentExpertPanel.length
		});

		groups.push({
			type: 'expert_panel',
			events: currentExpertPanel,
			subProblemGoal: currentSubProblemGoal,
			subProblemIndex: currentSubProblemIndex,
		});
	}

	// Flush remaining contributions
	if (currentRound.length > 0) {
		groups.push({
			type: 'round',
			events: currentRound,
			roundNumber: currentRoundNumber,
		});
	}

	return groups;
}

/**
 * Index events by sub-problem for efficient lookup
 */
export function indexEventsBySubProblem(events: SSEEvent[]): Map<number, SSEEvent[]> {
	const index = new Map<number, SSEEvent[]>();

	for (const event of events) {
		const subIndex = getSubProblemIndex(event);
		if (subIndex !== undefined) {
			const existing = index.get(subIndex) || [];
			existing.push(event);
			index.set(subIndex, existing);
		}
	}

	return index;
}
