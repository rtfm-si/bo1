/**
 * Reusable Timer Hooks for Svelte 5
 *
 * Consolidates 6 duplicate timer implementations from meeting page:
 * - Working status elapsed time
 * - Synthesis timing
 * - Voting timing
 * - Staleness detection
 * - Initial waiting message carousel
 * - Between-rounds message carousel
 */

/**
 * Basic elapsed time timer.
 * Tracks seconds since activation.
 *
 * @example
 * ```svelte
 * const timer = useElapsedTimer(() => isSynthesizing);
 * // Access: timer.elapsed, timer.reset()
 * ```
 */
export function useElapsedTimer(isActive: () => boolean, interval = 1000) {
	let startTime = $state<number | null>(null);
	let elapsed = $state(0);

	$effect(() => {
		if (isActive()) {
			startTime = Date.now();
			const id = setInterval(() => {
				if (startTime) {
					elapsed = Math.floor((Date.now() - startTime) / 1000);
				}
			}, interval);
			return () => clearInterval(id);
		} else {
			startTime = null;
			elapsed = 0;
		}
	});

	return {
		get elapsed() {
			return elapsed;
		},
		get isRunning() {
			return startTime !== null;
		},
		reset() {
			startTime = Date.now();
			elapsed = 0;
		}
	};
}

/**
 * Staleness detection timer.
 * Tracks time since last event and triggers stale state after threshold.
 *
 * @example
 * ```svelte
 * const staleness = useStalenessTimer(8000, () => session?.status === 'active');
 * // Call staleness.touch() when event received
 * // Access: staleness.isStale, staleness.secondsSinceLastEvent
 * ```
 */
export function useStalenessTimer(
	thresholdMs: number,
	shouldTrack: () => boolean,
	interval = 1000
) {
	let lastEventTime = $state(Date.now());
	let isStale = $state(false);
	let secondsSinceLastEvent = $state(0);

	$effect(() => {
		if (!shouldTrack()) {
			isStale = false;
			secondsSinceLastEvent = 0;
			return;
		}

		const id = setInterval(() => {
			const timeSince = Date.now() - lastEventTime;
			if (timeSince >= thresholdMs) {
				isStale = true;
				secondsSinceLastEvent = Math.floor(timeSince / 1000);
			} else {
				isStale = false;
				secondsSinceLastEvent = 0;
			}
		}, interval);

		return () => clearInterval(id);
	});

	return {
		get isStale() {
			return isStale;
		},
		get secondsSinceLastEvent() {
			return secondsSinceLastEvent;
		},
		touch() {
			lastEventTime = Date.now();
			isStale = false;
			secondsSinceLastEvent = 0;
		}
	};
}

/**
 * Message carousel timer.
 * Cycles through array of messages at specified interval.
 *
 * @example
 * ```svelte
 * const messages = ['Loading...', 'Please wait...', 'Almost there...'];
 * const carousel = useCarouselTimer(messages, 1500, () => isLoading);
 * // Access: carousel.currentMessage, carousel.currentIndex
 * ```
 */
export function useCarouselTimer<T>(
	messages: T[],
	intervalMs: number,
	isActive: () => boolean
) {
	let currentIndex = $state(0);

	$effect(() => {
		if (isActive() && messages.length > 0) {
			const id = setInterval(() => {
				currentIndex = (currentIndex + 1) % messages.length;
			}, intervalMs);
			return () => clearInterval(id);
		} else {
			currentIndex = 0;
		}
	});

	return {
		get currentIndex() {
			return currentIndex;
		},
		get currentMessage() {
			return messages[currentIndex];
		},
		reset() {
			currentIndex = 0;
		}
	};
}

/**
 * Multi-phase elapsed timer.
 * Tracks elapsed time across multiple mutually-exclusive phases.
 * Only one phase can be active at a time.
 *
 * @example
 * ```svelte
 * const phaseTimer = usePhaseTimer();
 *
 * // When voting starts:
 * phaseTimer.startPhase('voting');
 *
 * // When synthesis starts:
 * phaseTimer.startPhase('synthesis');
 *
 * // Access current elapsed:
 * phaseTimer.elapsed // seconds since current phase started
 * phaseTimer.currentPhase // 'voting' | 'synthesis' | null
 * ```
 */
export function usePhaseTimer(interval = 1000) {
	let currentPhase = $state<string | null>(null);
	let startTime = $state<number | null>(null);
	let elapsed = $state(0);

	$effect(() => {
		if (currentPhase && startTime) {
			const id = setInterval(() => {
				if (startTime) {
					elapsed = Math.floor((Date.now() - startTime) / 1000);
				}
			}, interval);
			return () => clearInterval(id);
		}
	});

	return {
		get elapsed() {
			return elapsed;
		},
		get currentPhase() {
			return currentPhase;
		},
		get isRunning() {
			return currentPhase !== null;
		},
		startPhase(phase: string) {
			currentPhase = phase;
			startTime = Date.now();
			elapsed = 0;
		},
		stopPhase() {
			currentPhase = null;
			startTime = null;
			elapsed = 0;
		}
	};
}
