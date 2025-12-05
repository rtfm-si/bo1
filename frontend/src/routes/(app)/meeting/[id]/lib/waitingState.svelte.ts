/**
 * Waiting State - Detection of various waiting conditions
 * Determines when to show waiting indicators for first contributions, between rounds, etc.
 */

import type { SSEEvent } from '$lib/api/sse-events';
import type { EventGroup } from './eventGrouping';
import { PHASE_MESSAGES } from './contributionReveal.svelte';

export interface WaitingStateConfig {
	getSession: () => { status: string; phase: string | null } | null;
	getEvents: () => SSEEvent[];
	getGroupedEvents: () => EventGroup[];
	getVisibleCount: (roundKey: string) => number;
	isSynthesizing: () => boolean;
	isVoting: () => boolean;
}

/**
 * Creates waiting state detector
 */
export function createWaitingState(config: WaitingStateConfig) {
	const { getSession, getEvents, getGroupedEvents, getVisibleCount, isSynthesizing, isVoting } =
		config;

	// ============================================================================
	// DERIVED VALUES
	// ============================================================================

	const isWaitingForFirstContributions = $derived.by(() => {
		const session = getSession();
		const events = getEvents();

		if (!session || session.status === 'completed') return false;

		const contributionCount = events.filter((e) => e.event_type === 'contribution').length;

		if (events.length > 0 && contributionCount === 0) {
			const phase = session.phase;
			if (phase === 'persona_selection' || phase === 'initial_round') {
				return true;
			}
		}
		return false;
	});

	const phaseWaitingMessage = $derived.by(() => {
		const session = getSession();
		if (!session?.phase) return 'Preparing...';
		return PHASE_MESSAGES[session.phase] || 'Experts are preparing...';
	});

	const isWaitingForNextRound = $derived.by(() => {
		const session = getSession();
		const groupedEvents = getGroupedEvents();

		if (
			session?.status === 'completed' ||
			session?.phase === 'complete' ||
			session?.phase === 'synthesis'
		) {
			return false;
		}

		if (isSynthesizing() || isVoting() || isWaitingForFirstContributions) {
			return false;
		}

		const roundGroups = groupedEvents.filter((g) => g.type === 'round' && g.events);
		if (roundGroups.length === 0) return false;

		const latestRound = roundGroups[roundGroups.length - 1];
		if (!latestRound.events || !latestRound.roundNumber) return false;

		const roundKey = `round-${latestRound.roundNumber}`;
		const visibleCount = getVisibleCount(roundKey);
		const totalInRound = latestRound.events.length;

		return visibleCount >= totalInRound && session?.status === 'active';
	});

	const isTransitioningSubProblem = $derived.by(() => {
		const session = getSession();
		const events = getEvents();

		if (session?.status !== 'active') return false;

		const lastSubProblemComplete = events.findLast((e) => e.event_type === 'subproblem_complete');
		const lastSubProblemStarted = events.findLast((e) => e.event_type === 'subproblem_started');

		if (!lastSubProblemComplete) return false;
		if (!lastSubProblemStarted) return true;

		const completeTime = new Date(lastSubProblemComplete.timestamp).getTime();
		const startTime = new Date(lastSubProblemStarted.timestamp).getTime();

		return completeTime > startTime;
	});

	return {
		// Reactive getters
		get isWaitingForFirstContributions() {
			return isWaitingForFirstContributions;
		},
		get phaseWaitingMessage() {
			return phaseWaitingMessage;
		},
		get isWaitingForNextRound() {
			return isWaitingForNextRound;
		},
		get isTransitioningSubProblem() {
			return isTransitioningSubProblem;
		},
	};
}

export type WaitingState = ReturnType<typeof createWaitingState>;
