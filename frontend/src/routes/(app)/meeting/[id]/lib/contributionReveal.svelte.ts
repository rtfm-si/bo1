/**
 * Contribution Reveal - Manages staggered display of expert contributions
 * Creates a progressive reveal effect where contributions appear one at a time
 * with random delays (400-600ms) to feel more dynamic and natural
 */

import type { SSEEvent, ContributionEvent } from '$lib/api/sse-events';
import type { EventGroup } from './eventGrouping';

// Delay constants for staggered reveal
const MIN_DELAY = 400; // 400ms minimum
const MAX_DELAY = 600; // 600ms maximum

/**
 * Generate random delay between min and max
 */
function getRandomDelay(): number {
	return Math.floor(Math.random() * (MAX_DELAY - MIN_DELAY + 1)) + MIN_DELAY;
}

/**
 * Varied thinking messages for pending experts
 */
export const THINKING_MESSAGES = [
	(name: string) => `${name} is thinking...`,
	(name: string) => `${name} is formulating a response...`,
	(name: string) => `${name} wants to contribute...`,
	(name: string) => `${name} is considering the discussion...`,
	(name: string) => `${name} is preparing insights...`,
];

/**
 * Initial waiting messages (before any events arrive)
 */
export const INITIAL_WAITING_MESSAGES = [
	'Waiting for deliberation to start...',
	'Preparing your expert panel...',
	'Setting up the discussion...',
];

/**
 * Between-rounds waiting messages
 */
export const BETWEEN_ROUNDS_MESSAGES = [
	'Experts are consulting...',
	'Analyzing the discussion so far...',
	'Preparing the next round of insights...',
	'Experts are researching...',
	'Synthesizing perspectives...',
	'Evaluating different viewpoints...',
	'Building on previous contributions...',
];

/**
 * Phase-specific messages
 */
export const PHASE_MESSAGES: Record<string, string> = {
	persona_selection: 'Experts are being selected...',
	initial_round: 'Experts are familiarising themselves with the problem...',
};

export interface PendingExpert {
	name: string;
	roundKey: string;
}

/**
 * Creates a contribution reveal manager
 * Handles staggered display of contributions with reactive state
 */
export function createContributionReveal() {
	// Visible contribution counts per round
	let visibleContributionCounts = $state<Map<string, number>>(new Map());

	// Track pending experts for "thinking" indicator
	let pendingExperts = $state<PendingExpert[]>([]);

	// Message rotation indices
	let initialWaitingMessageIndex = $state(0);
	let betweenRoundsMessageIndex = $state(0);

	// Interval references for cleanup
	let initialWaitingInterval: ReturnType<typeof setInterval> | null = null;
	let betweenRoundsInterval: ReturnType<typeof setInterval> | null = null;

	/**
	 * Process grouped events and stage reveals for new contributions
	 */
	function processGroups(groupedEvents: EventGroup[], isCompleted: boolean) {
		for (const group of groupedEvents) {
			if (group.type === 'round' && group.events) {
				const roundKey = `round-${group.roundNumber}`;
				const currentVisible = visibleContributionCounts.get(roundKey) || 0;
				const totalContributions = group.events.length;

				// If we have new contributions to reveal
				if (currentVisible < totalContributions) {
					// For completed meetings, reveal all immediately
					if (isCompleted) {
						visibleContributionCounts.set(roundKey, totalContributions);
						visibleContributionCounts = new Map(visibleContributionCounts);
						continue;
					}

					// Calculate how many we need to reveal
					const toReveal = totalContributions - currentVisible;

					// Update pending experts list
					const newPending = group.events.slice(currentVisible).map((e) => {
						const contribEvent = e as ContributionEvent;
						return {
							name: contribEvent.data.persona_name || 'Expert',
							roundKey,
						};
					});
					pendingExperts = newPending;

					// Stage the reveals with random delays
					let cumulativeDelay = 0;
					for (let i = 0; i < toReveal; i++) {
						const revealIndex = currentVisible + i;
						const delay = i === 0 ? getRandomDelay() : cumulativeDelay;
						cumulativeDelay += getRandomDelay();

						setTimeout(() => {
							visibleContributionCounts.set(roundKey, revealIndex + 1);
							visibleContributionCounts = new Map(visibleContributionCounts);

							// Update pending experts (remove the one we just revealed)
							pendingExperts = pendingExperts.filter((_, idx) => idx !== 0);
						}, delay);
					}
				}
			}
		}
	}

	/**
	 * Start cycling initial waiting messages
	 */
	function startInitialWaitingCycle() {
		if (!initialWaitingInterval) {
			initialWaitingInterval = setInterval(() => {
				initialWaitingMessageIndex =
					(initialWaitingMessageIndex + 1) % INITIAL_WAITING_MESSAGES.length;
			}, 1500);
		}
	}

	/**
	 * Stop cycling initial waiting messages
	 */
	function stopInitialWaitingCycle() {
		if (initialWaitingInterval) {
			clearInterval(initialWaitingInterval);
			initialWaitingInterval = null;
		}
	}

	/**
	 * Start cycling between-rounds messages
	 */
	function startBetweenRoundsCycle() {
		if (!betweenRoundsInterval) {
			betweenRoundsInterval = setInterval(() => {
				betweenRoundsMessageIndex =
					(betweenRoundsMessageIndex + 1) % BETWEEN_ROUNDS_MESSAGES.length;
			}, 1500);
		}
	}

	/**
	 * Stop cycling between-rounds messages
	 */
	function stopBetweenRoundsCycle() {
		if (betweenRoundsInterval) {
			clearInterval(betweenRoundsInterval);
			betweenRoundsInterval = null;
		}
	}

	/**
	 * Clean up all intervals
	 */
	function cleanup() {
		stopInitialWaitingCycle();
		stopBetweenRoundsCycle();
	}

	/**
	 * Get visible count for a specific round
	 */
	function getVisibleCount(roundKey: string): number {
		return visibleContributionCounts.get(roundKey) || 0;
	}

	return {
		// Reactive getters
		get visibleContributionCounts() {
			return visibleContributionCounts;
		},
		get pendingExperts() {
			return pendingExperts;
		},
		get initialWaitingMessageIndex() {
			return initialWaitingMessageIndex;
		},
		get betweenRoundsMessageIndex() {
			return betweenRoundsMessageIndex;
		},

		// Methods
		processGroups,
		startInitialWaitingCycle,
		stopInitialWaitingCycle,
		startBetweenRoundsCycle,
		stopBetweenRoundsCycle,
		cleanup,
		getVisibleCount,
	};
}

export type ContributionReveal = ReturnType<typeof createContributionReveal>;
