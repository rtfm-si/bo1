<script lang="ts">
	/**
	 * Context Refresh Banner - Prompts users to update stale business context
	 *
	 * Shows a non-intrusive banner when user's business context hasn't been
	 * updated in 30+ days, encouraging them to review and update it.
	 */

	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import Button from './Button.svelte';
	import { trackEvent, AnalyticsEvents } from '$lib/utils/analytics';

	// State
	let needsRefresh = $state(false);
	let daysSinceUpdate = $state<number | null>(null);
	let missingFields = $state<string[]>([]);
	let isDismissed = $state(false);
	let isLoading = $state(true);

	onMount(async () => {
		try {
			const response = await apiClient.checkRefreshNeeded();
			needsRefresh = response.needs_refresh;
			daysSinceUpdate = response.days_since_update;
			missingFields = response.missing_fields || [];
		} catch (error) {
			console.error('Failed to check context refresh:', error);
		} finally {
			isLoading = false;
		}
	});

	async function handleDismiss() {
		isDismissed = true;
		trackEvent('context_refresh_dismissed');

		try {
			await apiClient.dismissRefresh();
		} catch (error) {
			console.error('Failed to dismiss refresh prompt:', error);
		}
	}

	function handleUpdate() {
		trackEvent('context_refresh_clicked');
	}

	// Format message based on state
	const message = $derived(() => {
		if (missingFields.length > 0) {
			return `Complete your business profile to get better recommendations.`;
		}
		if (daysSinceUpdate !== null && daysSinceUpdate > 60) {
			return `Your business context hasn't been updated in ${daysSinceUpdate} days. Has anything changed?`;
		}
		if (daysSinceUpdate !== null && daysSinceUpdate > 30) {
			return `Keep your business context up to date for more relevant advice.`;
		}
		return `Review your business context for more personalized recommendations.`;
	});
</script>

{#if !isLoading && needsRefresh && !isDismissed}
	<div
		class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-6"
	>
		<div class="flex items-start gap-3">
			<!-- Icon -->
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
						d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
					/>
				</svg>
			</div>

			<!-- Content -->
			<div class="flex-1 min-w-0">
				<p class="text-sm font-medium text-amber-800 dark:text-amber-200">
					{message()}
				</p>
				{#if missingFields.length > 0}
					<p class="mt-1 text-xs text-amber-700 dark:text-amber-300">
						Missing: {missingFields.slice(0, 3).join(', ')}{missingFields.length > 3
							? ` and ${missingFields.length - 3} more`
							: ''}
					</p>
				{/if}
			</div>

			<!-- Actions -->
			<div class="flex items-center gap-2 flex-shrink-0">
				<a href="/settings/context" onclick={handleUpdate}>
					<Button size="sm" variant="accent">
						Update
					</Button>
				</a>
				<button
					type="button"
					onclick={handleDismiss}
					class="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200 p-1 rounded"
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
	</div>
{/if}
