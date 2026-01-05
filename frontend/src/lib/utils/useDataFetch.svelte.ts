/**
 * Data fetching utility for Svelte 5 (using runes)
 *
 * Consolidates the repeated pattern of:
 * - let isLoading = $state(true)
 * - let error = $state<string | null>(null)
 * - let data = $state<T | null>(null)
 *
 * Usage:
 * ```ts
 * import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
 *
 * const sessions = useDataFetch(() => apiClient.listSessions());
 *
 * onMount(() => {
 *   sessions.fetch();
 * });
 *
 * // In template:
 * {#if sessions.isLoading}
 *   <div>Loading...</div>
 * {:else if sessions.error}
 *   <div>Error: {sessions.error}</div>
 * {:else if sessions.data}
 *   <div>Data: {sessions.data}</div>
 * {/if}
 * ```
 */

/**
 * Data fetch state and operations
 */
export interface DataFetchState<T> {
	/** Current data (null until loaded) */
	data: T | null;
	/** Loading state */
	isLoading: boolean;
	/** Error message (null if no error) */
	error: string | null;
	/** Fetch/refetch the data */
	fetch: () => Promise<void>;
	/** Reset state to initial */
	reset: () => void;
}

/**
 * Create a data fetching utility with loading/error state management
 *
 * @param fetchFn - Async function that fetches the data
 * @returns Data fetch state object with reactive properties
 *
 * @example
 * ```ts
 * // Basic usage
 * const sessions = useDataFetch(() => apiClient.listSessions());
 *
 * onMount(() => {
 *   sessions.fetch();
 * });
 *
 * // With parameters
 * const session = useDataFetch(() => apiClient.getSession(sessionId));
 *
 * // Manual refetch
 * async function handleRefresh() {
 *   await session.fetch();
 * }
 * ```
 */
export function useDataFetch<T>(fetchFn: () => Promise<T>): DataFetchState<T> {
	let data = $state<T | null>(null);
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	async function fetch() {
		// Use setTimeout(0) to properly defer state mutations outside Svelte's render cycle
		// Promise.resolve() runs as a microtask which can still be within the same render batch
		await new Promise(resolve => setTimeout(resolve, 0));

		try {
			isLoading = true;
			error = null;

			const result = await fetchFn();
			data = result;
		} catch (err) {
			console.error('Data fetch failed:', err);
			error = err instanceof Error ? err.message : 'Failed to fetch data';
			data = null;
		} finally {
			isLoading = false;
		}
	}

	function reset() {
		data = null;
		isLoading = false;
		error = null;
	}

	return {
		get data() { return data; },
		get isLoading() { return isLoading; },
		get error() { return error; },
		fetch,
		reset,
	};
}
