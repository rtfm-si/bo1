<script lang="ts">
	/**
	 * Context Refresh Banner - Prompts users to update stale business context
	 *
	 * Shows a volatility-aware banner when user's business context metrics are stale.
	 * Displays specific field names and uses visual urgency based on volatility:
	 * - Red: action-affected or volatile metrics (revenue, customers)
	 * - Amber: moderate volatility (team size, competitors)
	 * - Subtle: stable metrics (business stage, industry)
	 */

	import { onMount } from 'svelte';
	import { apiClient, type StaleFieldSummary } from '$lib/api/client';
	import Button from './Button.svelte';
	import { trackEvent } from '$lib/utils/analytics';

	// State
	let needsRefresh = $state(false);
	let staleMetrics = $state<StaleFieldSummary[]>([]);
	let highestUrgency = $state<string | null>(null);
	let isDismissed = $state(false);
	let isLoading = $state(true);

	onMount(async () => {
		try {
			const response = await apiClient.checkRefreshNeeded();
			needsRefresh = response.needs_refresh;
			staleMetrics = response.stale_metrics || [];
			highestUrgency = response.highest_urgency;
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
			// Use highest urgency to determine dismiss expiry
			const volatility = highestUrgency === 'action_affected' ? 'volatile' : highestUrgency;
			await apiClient.dismissRefresh(volatility as 'volatile' | 'moderate' | 'stable' | undefined);
		} catch (error) {
			console.error('Failed to dismiss refresh prompt:', error);
		}
	}

	function handleUpdate() {
		trackEvent('context_refresh_clicked');
	}

	// Get urgency color classes
	const urgencyColors = $derived.by(() => {
		if (highestUrgency === 'action_affected' || highestUrgency === 'volatile') {
			return {
				bg: 'bg-red-50 dark:bg-red-900/20',
				border: 'border-red-200 dark:border-red-800',
				icon: 'text-red-600 dark:text-red-400',
				text: 'text-red-800 dark:text-red-200',
				subtext: 'text-red-700 dark:text-red-300'
			};
		}
		if (highestUrgency === 'moderate') {
			return {
				bg: 'bg-amber-50 dark:bg-amber-900/20',
				border: 'border-amber-200 dark:border-amber-800',
				icon: 'text-amber-600 dark:text-amber-400',
				text: 'text-amber-800 dark:text-amber-200',
				subtext: 'text-amber-700 dark:text-amber-300'
			};
		}
		// stable
		return {
			bg: 'bg-blue-50 dark:bg-blue-900/20',
			border: 'border-blue-200 dark:border-blue-800',
			icon: 'text-blue-600 dark:text-blue-400',
			text: 'text-blue-800 dark:text-blue-200',
			subtext: 'text-blue-700 dark:text-blue-300'
		};
	});

	// Format stale field names for display
	const staleFieldNames = $derived(staleMetrics.map((m) => m.display_name));

	// Build message based on urgency and fields
	const message = $derived.by(() => {
		const fieldList = staleFieldNames.slice(0, 3).join(', ');
		const hasActionAffected = staleMetrics.some((m) => m.action_affected);

		if (hasActionAffected) {
			return `You recently completed an action. Update ${fieldList} for accurate recommendations.`;
		}
		if (highestUrgency === 'volatile') {
			return `${fieldList} may have changed. Keep these metrics current for better advice.`;
		}
		if (highestUrgency === 'moderate') {
			return `Review ${fieldList} to ensure recommendations stay relevant.`;
		}
		return `Consider reviewing ${fieldList} for more personalized recommendations.`;
	});
</script>

{#if !isLoading && needsRefresh && !isDismissed && staleMetrics.length > 0}
	<div class="{urgencyColors.bg} border {urgencyColors.border} rounded-lg p-4 mb-6">
		<div class="flex items-start gap-3">
			<!-- Icon -->
			<div class="flex-shrink-0">
				<svg class="w-5 h-5 {urgencyColors.icon} mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
				<p class="text-sm font-medium {urgencyColors.text}">
					{message}
				</p>
				{#if staleFieldNames.length > 3}
					<p class="mt-1 text-xs {urgencyColors.subtext}">
						+{staleFieldNames.length - 3} more fields need attention
					</p>
				{/if}
			</div>

			<!-- Actions -->
			<div class="flex items-center gap-2 flex-shrink-0">
				<a href="/context" onclick={handleUpdate}>
					<Button size="sm" variant={highestUrgency === 'action_affected' || highestUrgency === 'volatile' ? 'danger' : 'accent'}>
						Update
					</Button>
				</a>
				<button
					type="button"
					onclick={handleDismiss}
					class="{urgencyColors.icon} hover:opacity-80 p-1 rounded"
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
