<script lang="ts">
	/**
	 * BenchmarkRefreshBanner - Prompts user to confirm stale benchmark values
	 *
	 * Displays when benchmark values haven't been updated in 30+ days,
	 * prompting user to verify they're still accurate.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { StaleBenchmarksResponse, StaleBenchmark } from '$lib/api/types';
	import Alert from '$lib/components/ui/Alert.svelte';

	// State
	let isLoading = $state(true);
	let staleBenchmarks = $state<StaleBenchmark[]>([]);
	let hasStaleBenchmarks = $state(false);
	let isDismissed = $state(false);
	let error = $state<string | null>(null);

	// Check localStorage for recent dismiss
	const DISMISS_KEY = 'benchmark_refresh_dismissed_at';
	const DISMISS_HOURS = 24; // Re-show after 24 hours

	onMount(async () => {
		// Check if recently dismissed
		const dismissedAt = localStorage.getItem(DISMISS_KEY);
		if (dismissedAt) {
			const dismissedTime = new Date(dismissedAt).getTime();
			const now = Date.now();
			const hoursSinceDismiss = (now - dismissedTime) / (1000 * 60 * 60);
			if (hoursSinceDismiss < DISMISS_HOURS) {
				isDismissed = true;
				isLoading = false;
				return;
			}
		}

		await loadStaleBenchmarks();
	});

	async function loadStaleBenchmarks() {
		try {
			const response: StaleBenchmarksResponse = await apiClient.getStaleBenchmarks();
			hasStaleBenchmarks = response.has_stale_benchmarks;
			staleBenchmarks = response.stale_benchmarks;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to check benchmarks';
		} finally {
			isLoading = false;
		}
	}

	function dismiss() {
		localStorage.setItem(DISMISS_KEY, new Date().toISOString());
		isDismissed = true;
	}

	function formatDaysAgo(days: number): string {
		if (days >= 999) return 'never confirmed';
		if (days < 30) return `${days} days ago`;
		if (days < 60) return '1 month ago';
		const months = Math.floor(days / 30);
		return `${months} months ago`;
	}
</script>

{#if !isLoading && !isDismissed && hasStaleBenchmarks && staleBenchmarks.length > 0}
	<div
		class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-6"
	>
		<div class="flex items-start gap-3">
			<div class="flex-shrink-0">
				<svg
					class="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
			</div>
			<div class="flex-1 min-w-0">
				<h3 class="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-1">
					Monthly Check-in: Are these values still accurate?
				</h3>
				<p class="text-sm text-amber-700 dark:text-amber-300 mb-3">
					Some of your benchmark values haven't been updated recently. Please verify they're still
					correct for accurate comparisons.
				</p>
				<ul class="text-sm text-amber-700 dark:text-amber-300 space-y-1 mb-3">
					{#each staleBenchmarks.slice(0, 3) as benchmark}
						<li class="flex items-center gap-2">
							<span class="font-medium">{benchmark.display_name}:</span>
							<span class="text-amber-600 dark:text-amber-400">
								{formatDaysAgo(benchmark.days_since_update)}
							</span>
						</li>
					{/each}
					{#if staleBenchmarks.length > 3}
						<li class="text-amber-500 dark:text-amber-400 text-xs italic">
							+{staleBenchmarks.length - 3} more...
						</li>
					{/if}
				</ul>
				<div class="flex items-center gap-3">
					<a
						href="/context/metrics"
						class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-md transition-colors"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
							/>
						</svg>
						Update Values
					</a>
					<button
						type="button"
						onclick={dismiss}
						class="text-sm text-amber-600 dark:text-amber-400 hover:underline"
					>
						Remind me later
					</button>
				</div>
			</div>
			<button
				type="button"
				onclick={dismiss}
				class="flex-shrink-0 text-amber-500 hover:text-amber-700 dark:hover:text-amber-300"
				aria-label="Dismiss"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M6 18L18 6M6 6l12 12"
					/>
				</svg>
			</button>
		</div>
	</div>
{/if}

{#if error}
	<Alert variant="error" class="mb-6">{error}</Alert>
{/if}
