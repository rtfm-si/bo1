/**
 * Timing State - Consolidated timer, working status, staleness detection
 * Handles all time-based state for the meeting page with a single ticker
 */

import { STALENESS_THRESHOLD_MS } from '$lib/config/constants';
import type { SSEEvent } from '$lib/api/sse-events';

export interface TimingStateConfig {
	getSession: () => { status: string; phase: string | null } | null;
	getEvents: () => SSEEvent[];
}

/**
 * Creates timing state manager
 * Uses a single consolidated ticker for all time-based updates
 */
export function createTimingState(config: TimingStateConfig) {
	const { getSession, getEvents } = config;

	// ============================================================================
	// CONSOLIDATED TIMER (Single 1s ticker for all time-based updates)
	// ============================================================================

	let timerTick = $state(0);
	let timerInterval: ReturnType<typeof setInterval> | null = null;

	// ============================================================================
	// WORKING STATUS STATE
	// ============================================================================

	let currentWorkingPhase = $state<string | null>(null);
	let workingStatusStartTime = $state<number | null>(null);
	let estimatedDuration = $state<string | undefined>(undefined);

	// ============================================================================
	// STALENESS DETECTION
	// ============================================================================

	let lastEventReceivedTime = $state<number>(Date.now());

	// ============================================================================
	// SYNTHESIS/VOTING TIMING
	// ============================================================================

	let synthesisStartTime = $state<number | null>(null);
	let votingStartTime = $state<number | null>(null);
	let elapsedSeconds = $state(0);

	// ============================================================================
	// DERIVED VALUES
	// ============================================================================

	const workingElapsedSeconds = $derived.by(() => {
		void timerTick; // Create dependency
		if (!workingStatusStartTime) return 0;
		return Math.floor((Date.now() - workingStatusStartTime) / 1000);
	});

	const staleSinceSeconds = $derived.by(() => {
		void timerTick; // Create dependency
		const session = getSession();
		if (session?.status !== 'active') return 0;
		const timeSince = Date.now() - lastEventReceivedTime;
		return timeSince >= STALENESS_THRESHOLD_MS ? Math.floor(timeSince / 1000) : 0;
	});

	const isStale = $derived(staleSinceSeconds > 0);

	const isSynthesizing = $derived.by(() => {
		const events = getEvents();
		if (events.length === 0) return false;
		const lastEvent = events[events.length - 1];
		return (
			lastEvent.event_type === 'voting_complete' &&
			!events.some(
				(e) =>
					e.event_type === 'synthesis_complete' || e.event_type === 'meta_synthesis_complete'
			)
		);
	});

	const isVoting = $derived.by(() => {
		const events = getEvents();
		if (events.length === 0) return false;
		const lastEvent = events[events.length - 1];
		return (
			lastEvent.event_type === 'voting_started' &&
			!events.some((e) => e.event_type === 'voting_complete')
		);
	});

	// ============================================================================
	// METHODS
	// ============================================================================

	function startTimer() {
		if (timerInterval) return;
		timerInterval = setInterval(() => {
			timerTick++;
		}, 1000);
	}

	function stopTimer() {
		if (timerInterval) {
			clearInterval(timerInterval);
			timerInterval = null;
		}
	}

	function setWorkingStatus(phase: string | null, duration?: string) {
		currentWorkingPhase = phase;
		estimatedDuration = duration;
		if (phase) {
			workingStatusStartTime = Date.now();
		} else {
			workingStatusStartTime = null;
		}
	}

	function resetStaleness() {
		lastEventReceivedTime = Date.now();
	}

	function startSynthesisTiming() {
		synthesisStartTime = Date.now();
	}

	function stopSynthesisTiming() {
		synthesisStartTime = null;
		elapsedSeconds = 0;
	}

	function startVotingTiming() {
		votingStartTime = Date.now();
	}

	function stopVotingTiming() {
		votingStartTime = null;
	}

	function updateElapsedSeconds() {
		if (synthesisStartTime) {
			elapsedSeconds = Math.floor((Date.now() - synthesisStartTime) / 1000);
		} else if (votingStartTime) {
			elapsedSeconds = Math.floor((Date.now() - votingStartTime) / 1000);
		} else {
			elapsedSeconds = 0;
		}
	}

	function cleanup() {
		stopTimer();
	}

	return {
		// Reactive getters
		get timerTick() {
			return timerTick;
		},
		get currentWorkingPhase() {
			return currentWorkingPhase;
		},
		get workingElapsedSeconds() {
			return workingElapsedSeconds;
		},
		get estimatedDuration() {
			return estimatedDuration;
		},
		get staleSinceSeconds() {
			return staleSinceSeconds;
		},
		get isStale() {
			return isStale;
		},
		get isSynthesizing() {
			return isSynthesizing;
		},
		get isVoting() {
			return isVoting;
		},
		get elapsedSeconds() {
			return elapsedSeconds;
		},
		get votingStartTime() {
			return votingStartTime;
		},
		get synthesisStartTime() {
			return synthesisStartTime;
		},

		// Methods
		startTimer,
		stopTimer,
		setWorkingStatus,
		resetStaleness,
		startSynthesisTiming,
		stopSynthesisTiming,
		startVotingTiming,
		stopVotingTiming,
		updateElapsedSeconds,
		cleanup,
	};
}

export type TimingState = ReturnType<typeof createTimingState>;
