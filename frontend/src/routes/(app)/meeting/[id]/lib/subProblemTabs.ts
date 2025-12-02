/**
 * Focus Area Tabs - Logic for building and managing focus area tabs
 */

import type { SSEEvent } from '$lib/api/sse-events';

export interface SubProblemTab {
	id: string;
	label: string;
	goal: string;
	status: 'pending' | 'active' | 'voting' | 'synthesis' | 'complete' | 'blocked';
	metrics: {
		expertCount: number;
		convergencePercent: number;
		currentRound: number;
		maxRounds: number;
		duration: string;
	};
	events: SSEEvent[];
}

/**
 * Build sub-problem tabs from events
 */
export function buildSubProblemTabs(
	events: SSEEvent[],
	eventsBySubProblem: Map<number, SSEEvent[]>
): SubProblemTab[] {
	// Find decomposition event
	const decompositionEvent = events.find(e => e.event_type === 'decomposition_complete');

	if (!decompositionEvent) {
		console.log('[TAB BUILD DEBUG] No decomposition_complete event found');
		return [];
	}

	const subProblems = decompositionEvent.data.sub_problems as Array<{
		goal: string;
		complexity: number;
		dependencies?: number[];
	}>;

	console.log('[TAB BUILD DEBUG] Decomposition event:', {
		eventData: decompositionEvent.data,
		subProblemsCount: subProblems?.length || 0,
		subProblems
	});

	if (!subProblems || subProblems.length <= 1) {
		console.log('[TAB BUILD DEBUG] Single sub-problem scenario, not building tabs');
		return [];
	}

	const tabs: SubProblemTab[] = [];

	console.log('[TAB BUILD DEBUG] Building tabs for', subProblems.length, 'sub-problems');

	for (let index = 0; index < subProblems.length; index++) {
		const subProblem = subProblems[index];

		// Use indexed lookup
		const subEvents = eventsBySubProblem.get(index) || [];
		console.log(`[TAB BUILD DEBUG] Sub-problem ${index}:`, {
			totalEvents: subEvents.length,
			eventTypes: subEvents.map(e => e.event_type)
		});

		// Single iteration for all metrics (instead of multiple filters)
		let expertCount = 0;
		let convergencePercent = 0;
		let roundCount = 0;
		let status: SubProblemTab['status'] = 'pending';
		let latestConvergenceEvent: SSEEvent | null = null;

		for (const event of subEvents) {
			// Count experts
			if (event.event_type === 'persona_selected') {
				expertCount++;
			}
			// Track latest convergence
			else if (event.event_type === 'convergence') {
				latestConvergenceEvent = event;
			}
			// Count rounds
			else if (event.event_type === 'round_started' || event.event_type === 'initial_round_started') {
				roundCount++;
			}
			// Determine status (priority order: complete > synthesis > voting > active)
			else if (event.event_type === 'subproblem_complete') {
				status = 'complete';
			} else if (event.event_type === 'synthesis_started' && status !== 'complete') {
				status = 'synthesis';
			} else if (event.event_type === 'voting_started' && status !== 'complete' && status !== 'synthesis') {
				status = 'voting';
			} else if (event.event_type === 'subproblem_started' && status === 'pending') {
				status = 'active';
			}
		}

		// Calculate convergence percentage
		if (latestConvergenceEvent) {
			const score = latestConvergenceEvent.data.score as number;
			const threshold = latestConvergenceEvent.data.threshold as number;
			convergencePercent = Math.round((score / threshold) * 100);
			console.log('[CONVERGENCE DEBUG]', {
				subProblem: index,
				score,
				threshold,
				convergencePercent,
				eventData: latestConvergenceEvent.data
			});
		} else {
			console.log('[CONVERGENCE DEBUG] No convergence event found for sub-problem', index, {
				subEvents: subEvents.length,
				eventTypes: subEvents.map(e => e.event_type)
			});
		}

		// Calculate duration - prefer duration_seconds from subproblem_complete event
		let duration = '0s';

		// First, check if we have a subproblem_complete or synthesis_complete event with duration_seconds
		const completionEvent = subEvents.find(
			e => (e.event_type === 'subproblem_complete' || e.event_type === 'synthesis_complete') &&
			     e.data?.duration_seconds !== undefined
		);

		if (completionEvent?.data?.duration_seconds) {
			// Use backend-provided duration
			const totalSeconds = Math.floor(Number(completionEvent.data.duration_seconds));
			const minutes = Math.floor(totalSeconds / 60);
			const seconds = totalSeconds % 60;
			duration = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
		} else if (subEvents.length > 1) {
			// Fallback: calculate from timestamps
			const firstTime = new Date(subEvents[0].timestamp);
			const lastTime = new Date(subEvents[subEvents.length - 1].timestamp);
			const diffMs = lastTime.getTime() - firstTime.getTime();
			const diffMin = Math.floor(diffMs / 60000);
			const diffSec = Math.floor((diffMs % 60000) / 1000);
			duration = diffMin > 0 ? `${diffMin}m ${diffSec}s` : `${diffSec}s`;
		}

		tabs.push({
			id: `subproblem-${index}`,
			label: `Focus Area ${index + 1}`,
			goal: subProblem.goal,
			status,
			metrics: {
				expertCount,
				convergencePercent,
				currentRound: roundCount || 1,
				maxRounds: 10,
				duration,
			},
			events: subEvents,
		});
	}

	return tabs;
}

/**
 * Calculate sub-problem progress
 */
export function calculateSubProblemProgress(
	events: SSEEvent[]
): { current: number; total: number } | null {
	let startedCount = 0;
	let completedCount = 0;
	let totalSubProblems = 1;
	let firstStarted: SSEEvent | null = null;
	const startedIndices = new Set<number>();

	for (const event of events) {
		if (event.event_type === 'subproblem_started') {
			startedCount++;
			if (!firstStarted) {
				firstStarted = event;
				totalSubProblems = (event.data.total_sub_problems as number) ?? 1;
			}
			const index = event.data.sub_problem_index as number;
			if (index !== undefined) {
				startedIndices.add(index);
			}
		} else if (event.event_type === 'subproblem_complete') {
			completedCount++;
		}
	}

	// Calculate current/total - use null when no sub-problems started yet
	if (startedCount === 0) {
		return null; // Not yet known - show "Preparing..."
	} else if (completedCount > 0) {
		return {
			current: completedCount,
			total: totalSubProblems
		};
	} else {
		return {
			current: startedIndices.size,
			total: totalSubProblems
		};
	}
}
