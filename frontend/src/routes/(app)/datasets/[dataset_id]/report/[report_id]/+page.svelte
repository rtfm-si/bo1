<script lang="ts">
	/**
	 * Report View Page - Displays a generated report for a dataset
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { apiClient } from '$lib/api/client';
	import type { DatasetReportResponse, DatasetFavourite, DatasetDetailResponse } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import DatasetReportRenderer from '$lib/components/dataset/DatasetReport.svelte';
	import { setBreadcrumbLabel, clearBreadcrumbLabel } from '$lib/stores/breadcrumbLabels';

	const datasetId = $derived(page.params.dataset_id || '');
	const reportId = $derived(page.params.report_id || '');

	// Data state
	let report = $state<DatasetReportResponse | null>(null);
	let favourites = $state<DatasetFavourite[]>([]);
	let dataset = $state<DatasetDetailResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function fetchData() {
		loading = true;
		error = null;
		try {
			// Fetch report, favourites, and dataset in parallel
			const [reportData, favouritesData, datasetData] = await Promise.all([
				apiClient.getReport(datasetId, reportId),
				apiClient.listFavourites(datasetId),
				apiClient.getDataset(datasetId)
			]);
			report = reportData;
			favourites = favouritesData.favourites;
			dataset = datasetData;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load report';
		} finally {
			loading = false;
		}
	}

	async function handleDelete() {
		if (!confirm('Are you sure you want to delete this report?')) return;
		try {
			await apiClient.deleteReport(datasetId, reportId);
			window.location.href = `/datasets/${datasetId}`;
		} catch (err) {
			console.error('Failed to delete report:', err);
		}
	}

	function handlePrint() {
		window.print();
	}

	onMount(() => {
		fetchData();
	});

	// Set breadcrumb labels
	$effect(() => {
		if (dataset?.name) {
			setBreadcrumbLabel(`/datasets/${datasetId}`, dataset.name);
		}
		if (report?.title) {
			setBreadcrumbLabel(`/datasets/${datasetId}/report/${reportId}`, report.title);
		}
		return () => {
			clearBreadcrumbLabel(`/datasets/${datasetId}`);
			clearBreadcrumbLabel(`/datasets/${datasetId}/report/${reportId}`);
		};
	});
</script>

<svelte:head>
	<title>{report?.title || 'Report'} - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">
	<main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if loading}
			<div class="space-y-6">
				<ShimmerSkeleton type="card" />
				<ShimmerSkeleton type="card" />
				<ShimmerSkeleton type="card" />
			</div>
		{:else if error}
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-6">
				<div class="flex items-center gap-3">
					<svg class="w-6 h-6 text-error-600 dark:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<div>
						<h3 class="text-lg font-semibold text-error-900 dark:text-error-200">Error Loading Report</h3>
						<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
					</div>
				</div>
				<div class="mt-4 flex gap-3">
					<Button variant="danger" size="md" onclick={fetchData}>
						{#snippet children()}
							Retry
						{/snippet}
					</Button>
					<Button variant="secondary" size="md" onclick={() => window.location.href = `/datasets/${datasetId}`}>
						{#snippet children()}
							Back to Dataset
						{/snippet}
					</Button>
				</div>
			</div>
		{:else if report}
			<!-- Action Bar -->
			<div class="flex items-center justify-between mb-6 print:hidden">
				<a
					href="/datasets/{datasetId}"
					class="flex items-center gap-2 text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
					</svg>
					Back to Dataset
				</a>
				<div class="flex items-center gap-2">
					<Button variant="secondary" size="sm" onclick={handlePrint}>
						{#snippet children()}
							<svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
							</svg>
							Print
						{/snippet}
					</Button>
					<Button variant="danger" size="sm" onclick={handleDelete}>
						{#snippet children()}
							<svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
							</svg>
							Delete
						{/snippet}
					</Button>
				</div>
			</div>

			<!-- Report Content -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-8">
				<DatasetReportRenderer
					{report}
					{favourites}
					datasetName={dataset?.name || 'Dataset'}
				/>
			</div>
		{/if}
	</main>
</div>

<style>
	@media print {
		:global(body) {
			background: white !important;
		}
		main {
			max-width: 100%;
			padding: 0;
		}
	}
</style>
