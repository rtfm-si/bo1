/**
 * Event Grouping - Logic for grouping events by type and round
 * Handles grouping contributions by round and expert panels
 */

import type { SSEEvent } from '$lib/api/sse-events';

export interface EventGroup {
	type: 'single' | 'round' | 'expert_panel';
	event?: SSEEvent;
	events?: SSEEvent[];
	roundNumber?: number;
	subProblemGoal?: string;
}

// Constants for internal event filtering
export const INTERNAL_EVENTS = ['node_start', 'node_end'];

// Status noise events to hide (UX redesign - these don't provide actionable info)
export const STATUS_NOISE_EVENTS = [
	'decomposition_started',
	'persona_selection_started',
	'persona_selection_complete',
	'initial_round_started',
	'facilitator_decision',
	'voting_started',
	'voting_complete',
	'convergence',
	'complete', // Hidden - redundant with SynthesisComplete (renders empty card otherwise)
	'discussion_quality_status', // Hidden - adds noise to timeline
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

	// Single iteration with inline filtering (combine filter + group logic)
	for (const event of events) {
		// Skip internal/noise events (inline filtering)
		if (!shouldShowEvent(event.event_type, debugMode)) {
			continue;
		}

		// Track round_started events to get round numbers
		if (event.event_type === 'round_started' || event.event_type === 'initial_round_started') {
			if (event.data.round_number) {
				currentRoundNumber = event.data.round_number as number;
			}
		}

		// Track subproblem_started for context
		if (event.event_type === 'subproblem_started') {
			currentSubProblemGoal = event.data.goal as string;
		}

		// Group persona_selected events
		if (event.event_type === 'persona_selected') {
			currentExpertPanel.push(event);
		} else if (event.event_type === 'contribution') {
			// Flush expert panel if any
			if (currentExpertPanel.length > 0) {
				groups.push({
					type: 'expert_panel',
					events: currentExpertPanel,
					subProblemGoal: currentSubProblemGoal,
				});
				currentExpertPanel = [];
			}

			// Get round number from contribution event itself
			const contributionRound = event.data.round as number | undefined;

			// If round number changed, flush previous round
			if (contributionRound && contributionRound !== currentRoundNumber && currentRound.length > 0) {
				groups.push({
					type: 'round',
					events: currentRound,
					roundNumber: currentRoundNumber,
				});
				currentRound = [];
			}

			// Update current round number from contribution
			if (contributionRound) {
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
		groups.push({
			type: 'expert_panel',
			events: currentExpertPanel,
			subProblemGoal: currentSubProblemGoal,
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
		const subIndex = event.data.sub_problem_index as number | undefined;
		if (subIndex !== undefined) {
			const existing = index.get(subIndex) || [];
			existing.push(event);
			index.set(subIndex, existing);
		}
	}

	return index;
}
