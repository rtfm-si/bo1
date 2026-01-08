<script lang="ts">
	/**
	 * Standalone Report View Page - Displays a report by ID
	 *
	 * Supports orphaned reports where the dataset has been deleted.
	 * For reports with existing datasets, links back to the dataset.
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { apiClient } from '$lib/api/client';
	import type { DatasetReportResponse, DatasetFavourite } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import DatasetReportRenderer from '$lib/components/dataset/DatasetReport.svelte';
	import { setBreadcrumbLabel, clearBreadcrumbLabel } from '$lib/stores/breadcrumbLabels';
	import { AlertTriangle } from 'lucide-svelte';

	const reportId = $derived(page.params.report_id || '');

	// Data state
	let report = $state<DatasetReportResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Derived: Is this an orphaned report (dataset was deleted)?
	const isOrphaned = $derived(!report?.dataset_id);

	async function fetchData() {
		loading = true;
		error = null;
		try {
			report = await apiClient.getReportById(reportId);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load report';
		} finally {
			loading = false;
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
		if (report?.title) {
			setBreadcrumbLabel(`/reports/data/${reportId}`, report.title);
		}
		return () => {
			clearBreadcrumbLabel(`/reports/data/${reportId}`);
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
					<Button variant="secondary" size="md" onclick={() => window.location.href = '/reports/data'}>
						{#snippet children()}
							Back to Reports
						{/snippet}
					</Button>
				</div>
			</div>
		{:else if report}
			<!-- Action Bar -->
			<div class="flex items-center justify-between mb-6 print:hidden">
				<a
					href="/reports/data"
					class="flex items-center gap-2 text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
					</svg>
					Back to Reports
				</a>
				<div class="flex items-center gap-2">
					{#if !isOrphaned && report.dataset_id}
						<Button variant="secondary" size="sm" onclick={() => window.location.href = `/datasets/${report?.dataset_id}`}>
							{#snippet children()}
								<svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
								</svg>
								View Dataset
							{/snippet}
						</Button>
					{/if}
					<Button variant="secondary" size="sm" onclick={handlePrint}>
						{#snippet children()}
							<svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
							</svg>
							Print
						{/snippet}
					</Button>
				</div>
			</div>

			<!-- Orphaned Report Warning -->
			{#if isOrphaned}
				<div class="mb-6 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
					<div class="flex items-start gap-3">
						<AlertTriangle class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
						<div>
							<h3 class="text-sm font-medium text-amber-800 dark:text-amber-200">Dataset Deleted</h3>
							<p class="text-sm text-amber-700 dark:text-amber-300 mt-1">
								The original dataset for this report has been deleted. Charts and visualizations may not render correctly.
							</p>
						</div>
					</div>
				</div>
			{/if}

			<!-- Report Content -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-8">
				<DatasetReportRenderer
					{report}
					favourites={report.favourites || []}
					datasetName={isOrphaned ? 'Deleted Dataset' : 'Dataset'}
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
