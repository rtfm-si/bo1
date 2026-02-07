<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { apiClient } from '$lib/api/client';
	import type { DatasetComparison, DatasetDetailResponse } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import { setBreadcrumbLabel, clearBreadcrumbLabel } from '$lib/stores/breadcrumbLabels';
	import DatasetComparisonComponent from '$lib/components/dataset/DatasetComparison.svelte';

	const datasetId = $derived(page.params.dataset_id || '');
	const otherDatasetId = $derived(page.params.other_dataset_id || '');

	// State
	let comparison = $state<DatasetComparison | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	// Dataset info for breadcrumbs
	let datasetA = $state<DatasetDetailResponse | null>(null);
	let datasetB = $state<DatasetDetailResponse | null>(null);

	// Load comparison on mount
	async function loadComparison() {
		if (!datasetId || !otherDatasetId) {
			error = 'Missing dataset IDs';
			isLoading = false;
			return;
		}

		isLoading = true;
		error = null;

		try {
			// Run comparison (will be cached if already exists)
			comparison = await apiClient.compareDatasets(datasetId, otherDatasetId);
		} catch (err) {
			console.error('Failed to compare datasets:', err);
			error = err instanceof Error ? err.message : 'Failed to compare datasets';
		} finally {
			isLoading = false;
		}
	}

	// Load dataset info for breadcrumbs
	async function loadDatasetInfo() {
		try {
			const [a, b] = await Promise.all([
				apiClient.getDataset(datasetId),
				apiClient.getDataset(otherDatasetId)
			]);
			datasetA = a;
			datasetB = b;

			// Set breadcrumb labels
			if (datasetA?.name) {
				setBreadcrumbLabel('dataset_id', datasetA.name);
			}
		} catch {
			// Non-critical - breadcrumbs will show IDs
		}
	}

	function handleClose() {
		goto(`/datasets/${datasetId}`);
	}

	onMount(() => {
		loadComparison();
		loadDatasetInfo();
		return () => {
			clearBreadcrumbLabel('dataset_id');
		};
	});
</script>

<svelte:head>
	<title>{comparison ? `${comparison.dataset_a_name} vs ${comparison.dataset_b_name}` : 'Dataset Comparison'} | Bo1</title>
</svelte:head>

<div class="mx-auto px-4 py-6 sm:px-6 lg:px-8 xl:px-12">
	<!-- Breadcrumb -->
	<nav class="mb-4">
		<ol class="flex items-center gap-2 text-sm text-neutral-500">
			<li>
				<a href="/datasets" class="hover:text-primary-600">Datasets</a>
			</li>
			<li>/</li>
			<li>
				<a href="/datasets/{datasetId}" class="hover:text-primary-600">
					{datasetA?.name ?? datasetId}
				</a>
			</li>
			<li>/</li>
			<li class="text-neutral-900 dark:text-neutral-100">
				Compare with {datasetB?.name ?? otherDatasetId}
			</li>
		</ol>
	</nav>

	<!-- Main Content -->
	<div class="rounded-lg border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-700 dark:bg-neutral-900">
		{#if isLoading}
			<div class="space-y-4">
				<ShimmerSkeleton class="h-8 w-48" />
				<ShimmerSkeleton class="h-32 w-full" />
				<ShimmerSkeleton class="h-48 w-full" />
				<ShimmerSkeleton class="h-64 w-full" />
			</div>
		{:else if error}
			<div class="rounded-lg border border-error-200 bg-error-50 p-6 text-center dark:border-error-800 dark:bg-error-900/20">
				<svg class="mx-auto h-12 w-12 text-error-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
					/>
				</svg>
				<h3 class="mt-4 text-lg font-medium text-error-800 dark:text-error-200">Comparison Failed</h3>
				<p class="mt-2 text-error-700 dark:text-error-300">{error}</p>
				<div class="mt-6 flex justify-center gap-3">
					<Button variant="outline" onclick={() => loadComparison()}>Retry</Button>
					<Button onclick={() => goto(`/datasets/${datasetId}`)}>Back to Dataset</Button>
				</div>
			</div>
		{:else}
			<DatasetComparisonComponent {comparison} onClose={handleClose} />
		{/if}
	</div>

	<!-- Actions -->
	{#if comparison}
		<div class="mt-6 flex justify-end gap-3">
			<Button variant="outline" onclick={() => goto(`/datasets/${datasetId}`)}>
				Back to {comparison.dataset_a_name ?? 'Dataset A'}
			</Button>
			<Button variant="outline" onclick={() => goto(`/datasets/${otherDatasetId}`)}>
				Go to {comparison.dataset_b_name ?? 'Dataset B'}
			</Button>
		</div>
	{/if}
</div>
