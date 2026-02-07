<script lang="ts">
	/**
	 * Multi-Dataset Analysis Page
	 * Runs cross-dataset anomaly detection on 2-5 selected datasets
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import type { MultiDatasetAnalysisResponse } from '$lib/api/types';
	import { Button } from '$lib/components/ui';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { toast } from '$lib/stores/toast';
	import MultiDatasetAnalysisResults from '$lib/components/dataset/MultiDatasetAnalysisResults.svelte';

	// State
	let datasetIds = $state<string[]>([]);
	let analysis = $state<MultiDatasetAnalysisResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function runAnalysis(ids: string[]) {
		if (ids.length < 2) {
			error = 'At least 2 datasets required';
			loading = false;
			return;
		}
		if (ids.length > 5) {
			error = 'Maximum 5 datasets allowed';
			loading = false;
			return;
		}

		loading = true;
		error = null;

		try {
			const result = await apiClient.runMultiDatasetAnalysis(ids);
			analysis = result;
		} catch (err) {
			console.error('Multi-dataset analysis failed:', err);
			error = err instanceof Error ? err.message : 'Analysis failed';
			toast.error('Failed to run analysis');
		} finally {
			loading = false;
		}
	}

	function handleClose() {
		goto('/advisor/analyze');
	}

	onMount(() => {
		const idsParam = $page.url.searchParams.get('ids');
		if (idsParam) {
			datasetIds = idsParam.split(',').filter((id) => id.trim());
			runAnalysis(datasetIds);
		} else {
			error = 'No datasets selected';
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>Multi-Dataset Analysis | Board of One</title>
	<meta name="description" content="Cross-dataset anomaly detection and comparison" />
</svelte:head>

<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-6">
	<!-- Header -->
	<div class="mb-6 flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">Multi-Dataset Analysis</h1>
			<p class="mt-1 text-neutral-600 dark:text-neutral-400">
				Cross-dataset anomaly detection and comparison
			</p>
		</div>
		<Button variant="outline" onclick={handleClose}>
			Back to Datasets
		</Button>
	</div>

	<!-- Results -->
	<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
		<MultiDatasetAnalysisResults
			{analysis}
			{loading}
			{error}
			onClose={handleClose}
		/>
	</div>
</div>
