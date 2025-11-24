/**
 * Debounce utility for delaying function execution until after a specified delay.
 *
 * Useful for optimizing expensive operations that fire frequently (e.g., scroll handlers,
 * reactive recalculations on every event addition).
 *
 * @param fn - The function to debounce
 * @param delay - Delay in milliseconds to wait before executing
 * @returns Debounced function
 *
 * @example
 * ```typescript
 * const recalculateGroupedEvents = debounce(() => {
 *     // Expensive grouping logic
 * }, 200);
 *
 * $effect(() => {
 *     if (events.length !== lastEventCount) {
 *         recalculateGroupedEvents();
 *     }
 * });
 * ```
 */
export function debounce<T extends (...args: any[]) => void>(
	fn: T,
	delay: number
): (...args: Parameters<T>) => void {
	let timeoutId: ReturnType<typeof setTimeout> | null = null;

	return function (...args: Parameters<T>) {
		// Clear previous timeout
		if (timeoutId !== null) {
			clearTimeout(timeoutId);
		}

		// Set new timeout
		timeoutId = setTimeout(() => {
			fn(...args);
			timeoutId = null;
		}, delay);
	};
}

/**
 * Throttle utility for limiting function execution frequency.
 *
 * Ensures function is called at most once every `limit` milliseconds.
 * Useful for scroll handlers where you want consistent updates but not on every pixel.
 *
 * @param fn - The function to throttle
 * @param limit - Minimum time in milliseconds between executions
 * @returns Throttled function
 *
 * @example
 * ```typescript
 * const handleScroll = throttle(() => {
 *     console.log('Scroll position:', window.scrollY);
 * }, 100); // Max once every 100ms
 *
 * window.addEventListener('scroll', handleScroll);
 * ```
 */
export function throttle<T extends (...args: any[]) => void>(
	fn: T,
	limit: number
): (...args: Parameters<T>) => void {
	let lastRun = 0;
	let timeoutId: ReturnType<typeof setTimeout> | null = null;

	return function (...args: Parameters<T>) {
		const now = Date.now();

		if (now - lastRun >= limit) {
			// Execute immediately if enough time has passed
			fn(...args);
			lastRun = now;
		} else {
			// Schedule execution for later
			if (timeoutId !== null) {
				clearTimeout(timeoutId);
			}

			timeoutId = setTimeout(
				() => {
					fn(...args);
					lastRun = Date.now();
					timeoutId = null;
				},
				limit - (now - lastRun)
			);
		}
	};
}
