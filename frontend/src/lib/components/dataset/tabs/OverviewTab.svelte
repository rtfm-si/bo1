<script lang="ts">
	/**
	 * OverviewTab - Dataset overview with stats, insights summary, and profile button
	 */
	import type { DatasetDetailResponse, DatasetInsights } from '$lib/api/types';
	import DataInsightsPanel from '../DataInsightsPanel.svelte';
	import { Button } from '$lib/components/ui';

	interface Props {
		dataset: DatasetDetailResponse;
		datasetId: string;
		insights: DatasetInsights | null;
		insightsLoading: boolean;
		insightsError: string | null;
		isProfiling: boolean;
		profileError: string | null;
		onProfile: () => void;
		onRefreshInsights: () => void;
		onQuestionClick: (question: string) => void;
	}

	let {
		dataset,
		datasetId,
		insights,
		insightsLoading,
		insightsError,
		isProfiling,
		profileError,
		onProfile,
		onRefreshInsights,
		onQuestionClick
	}: Props = $props();

	const isProfiled = $derived((dataset.profiles?.length ?? 0) > 0);
</script>

<div class="space-y-6">
	{#if !isProfiled}
		<!-- Not yet profiled - show prompt -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
			<svg class="w-16 h-16 mx-auto text-brand-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
			</svg>
			<h2 class="text-xl font-semibold text-neutral-900 dark:text-white mb-2">
				Ready to Analyze Your Data
			</h2>
			<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-md mx-auto">
				Generate a profile to unlock insights, statistics, and AI-powered analysis of your dataset.
			</p>
			{#if profileError}
				<div class="mb-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4 max-w-md mx-auto">
					<p class="text-sm text-error-700 dark:text-error-300">{profileError}</p>
				</div>
			{/if}
			<Button variant="brand" size="lg" onclick={onProfile} disabled={isProfiling}>
				{#snippet children()}
					{#if isProfiling}
						<svg class="w-5 h-5 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Analyzing...
					{:else}
						<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
						</svg>
						Generate Profile
					{/if}
				{/snippet}
			</Button>
		</div>
	{:else}
		<!-- Profiled - show insights -->
		<DataInsightsPanel
			{insights}
			{datasetId}
			loading={insightsLoading}
			error={insightsError}
			onQuestionClick={onQuestionClick}
			onRefresh={onRefreshInsights}
		/>
	{/if}
</div>
