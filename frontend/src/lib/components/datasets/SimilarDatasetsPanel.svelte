<script lang="ts">
	/**
	 * SimilarDatasetsPanel - Shows datasets similar to the current one
	 *
	 * Features:
	 * - Collapsible panel with "Find Similar" toggle
	 * - Shows matching datasets with similarity %, shared columns, insight preview
	 * - Click to navigate to similar dataset
	 */
	import { apiClient } from '$lib/api/client';
	import type { SimilarDataset } from '$lib/api/types';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import { goto } from '$app/navigation';

	interface Props {
		datasetId: string;
	}

	let { datasetId }: Props = $props();

	let isExpanded = $state(false);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let similarDatasets = $state<SimilarDataset[]>([]);
	let hasSearched = $state(false);

	async function findSimilar() {
		if (loading) return;

		isExpanded = true;
		loading = true;
		error = null;

		try {
			const response = await apiClient.getSimilarDatasets(datasetId, 0.55, 5);
			similarDatasets = response.similar;
			hasSearched = true;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to find similar datasets';
		} finally {
			loading = false;
		}
	}

	function navigateToDataset(id: string) {
		goto(`/datasets/${id}`);
	}

	function formatSimilarity(score: number): string {
		return `${Math.round(score * 100)}%`;
	}

	function getSimilarityColor(score: number): string {
		if (score >= 0.8) return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300';
		if (score >= 0.65) return 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300';
		return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400';
	}
</script>

<BoCard variant="bordered" padding="md" class="mt-6">
	{#snippet header()}
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<svg class="w-5 h-5 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
				</svg>
				<h3 class="text-base font-medium text-neutral-900 dark:text-neutral-100">Similar Datasets</h3>
			</div>
			<BoButton
				variant={isExpanded ? 'secondary' : 'outline'}
				size="sm"
				onclick={findSimilar}
				disabled={loading}
			>
				{#if loading}
					<Spinner size="sm" class="mr-2" />
					Searching...
				{:else if hasSearched}
					Refresh
				{:else}
					Find Similar
				{/if}
			</BoButton>
		</div>
	{/snippet}

	{#if isExpanded}
		<div class="mt-4">
			{#if loading && !hasSearched}
				<div class="flex items-center justify-center py-8">
					<Spinner size="md" />
					<span class="ml-3 text-sm text-neutral-500">Finding similar datasets...</span>
				</div>
			{:else if error}
				<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4">
					<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
					<BoButton variant="ghost" size="sm" class="mt-2" onclick={findSimilar}>
						Try again
					</BoButton>
				</div>
			{:else if similarDatasets.length === 0}
				<div class="text-center py-8">
					<svg class="w-12 h-12 mx-auto text-neutral-300 dark:text-neutral-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
					</svg>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">No similar datasets found</p>
					<p class="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
						Try uploading more datasets with similar columns or topics
					</p>
				</div>
			{:else}
				<div class="space-y-3">
					{#each similarDatasets as dataset (dataset.dataset_id)}
						<button
							type="button"
							class="w-full text-left bg-neutral-50 dark:bg-neutral-800/50 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg p-4 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
							onclick={() => navigateToDataset(dataset.dataset_id)}
						>
							<div class="flex items-start justify-between gap-3">
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="font-medium text-neutral-900 dark:text-neutral-100 truncate">
											{dataset.name}
										</span>
										<Badge class={getSimilarityColor(dataset.similarity)}>
											{formatSimilarity(dataset.similarity)} match
										</Badge>
									</div>

									{#if dataset.shared_columns.length > 0}
										<div class="flex items-center gap-1 mb-2">
											<span class="text-xs text-neutral-500 dark:text-neutral-400">
												Shared columns:
											</span>
											<div class="flex flex-wrap gap-1">
												{#each dataset.shared_columns.slice(0, 4) as col (col)}
													<span class="text-xs px-1.5 py-0.5 bg-neutral-200 dark:bg-neutral-700 rounded text-neutral-600 dark:text-neutral-300">
														{col}
													</span>
												{/each}
												{#if dataset.shared_columns.length > 4}
													<span class="text-xs text-neutral-400 dark:text-neutral-500">
														+{dataset.shared_columns.length - 4} more
													</span>
												{/if}
											</div>
										</div>
									{/if}

									{#if dataset.insight_preview}
										<p class="text-sm text-neutral-600 dark:text-neutral-400 line-clamp-2">
											{dataset.insight_preview}
										</p>
									{/if}
								</div>

								<svg class="w-5 h-5 text-neutral-400 flex-shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
								</svg>
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</BoCard>
