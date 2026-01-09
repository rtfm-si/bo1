<script lang="ts">
	/**
	 * DatasetHeader - Header section with title, stats, and compare dropdown
	 */
	import { goto } from '$app/navigation';
	import type { DatasetDetailResponse, DatasetResponse } from '$lib/api/types';
	import { apiClient } from '$lib/api/client';

	interface Props {
		dataset: DatasetDetailResponse;
		datasetId: string;
	}

	let { dataset, datasetId }: Props = $props();

	// Compare dropdown state
	let showCompareDropdown = $state(false);
	let otherDatasets = $state<DatasetResponse[]>([]);
	let loadingOtherDatasets = $state(false);

	async function loadOtherDatasets() {
		if (otherDatasets.length > 0) return;
		loadingOtherDatasets = true;
		try {
			const response = await apiClient.getDatasets({ limit: 50 });
			otherDatasets = (response.datasets ?? []).filter((d) => d.id !== datasetId);
		} catch (err) {
			console.error('Failed to load datasets for comparison:', err);
		} finally {
			loadingOtherDatasets = false;
		}
	}

	function handleCompareClick() {
		showCompareDropdown = !showCompareDropdown;
		if (showCompareDropdown) {
			loadOtherDatasets();
		}
	}

	function startComparison(otherDatasetId: string) {
		showCompareDropdown = false;
		goto(`/datasets/${datasetId}/compare/${otherDatasetId}`);
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatBytes(bytes: number | null): string {
		if (!bytes) return '—';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}
</script>

<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
	<div class="flex items-start justify-between">
		<div class="flex items-center gap-4">
			<span class="w-12 h-12 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
				<svg class="w-6 h-6 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
				</svg>
			</span>
			<div>
				<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">{dataset.name}</h1>
				{#if dataset.description}
					<p class="text-neutral-600 dark:text-neutral-400 mt-1">{dataset.description}</p>
				{/if}
			</div>
		</div>
		<div class="flex items-center gap-3">
			<!-- Compare Button -->
			<div class="relative">
				<button
					onclick={handleCompareClick}
					class="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-600 transition-colors"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
					</svg>
					Compare
					<svg class="w-4 h-4 transition-transform {showCompareDropdown ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if showCompareDropdown}
					<div class="absolute right-0 mt-2 w-64 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 shadow-lg z-50">
						<div class="p-2 border-b border-neutral-100 dark:border-neutral-700">
							<p class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Compare with</p>
						</div>
						<div class="max-h-64 overflow-y-auto">
							{#if loadingOtherDatasets}
								<div class="p-4 text-center">
									<div class="animate-spin w-5 h-5 border-2 border-neutral-300 border-t-primary-500 rounded-full mx-auto"></div>
								</div>
							{:else if otherDatasets.length === 0}
								<div class="p-4 text-center text-sm text-neutral-500 dark:text-neutral-400">
									No other datasets available
								</div>
							{:else}
								{#each otherDatasets as otherDataset}
									<button
										onclick={() => startComparison(otherDataset.id)}
										class="w-full px-4 py-2 text-left text-sm hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
									>
										<span class="font-medium text-neutral-900 dark:text-neutral-100">{otherDataset.name}</span>
										{#if otherDataset.row_count}
											<span class="text-neutral-500 dark:text-neutral-400 ml-2">({otherDataset.row_count.toLocaleString()} rows)</span>
										{/if}
									</button>
								{/each}
							{/if}
						</div>
					</div>
				{/if}
			</div>
			<span class="px-3 py-1 text-sm font-medium rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400 uppercase">
				{dataset.source_type}
			</span>
		</div>
	</div>

	<!-- Stats Row -->
	<div class="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
		<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-4">
			<div class="text-sm text-neutral-500 dark:text-neutral-400">Rows</div>
			<div class="text-xl font-semibold text-neutral-900 dark:text-white">
				{dataset.row_count?.toLocaleString() || '—'}
			</div>
		</div>
		<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-4">
			<div class="text-sm text-neutral-500 dark:text-neutral-400">Columns</div>
			<div class="text-xl font-semibold text-neutral-900 dark:text-white">
				{dataset.column_count || '—'}
			</div>
		</div>
		<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-4">
			<div class="text-sm text-neutral-500 dark:text-neutral-400">File Size</div>
			<div class="text-xl font-semibold text-neutral-900 dark:text-white">
				{formatBytes(dataset.file_size_bytes ?? null)}
			</div>
		</div>
		<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-4">
			<div class="text-sm text-neutral-500 dark:text-neutral-400">Updated</div>
			<div class="text-sm font-semibold text-neutral-900 dark:text-white">
				{formatDate(dataset.updated_at)}
			</div>
		</div>
	</div>
</div>
