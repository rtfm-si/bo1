<script lang="ts">
	/**
	 * Reports > Data Page - Shows all data analysis reports across datasets
	 *
	 * Lists generated reports from data analysis across all user datasets.
	 * Supports orphaned reports where the dataset has been deleted.
	 * Click-through to view full report.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { AllReportItem } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { formatCompactRelativeTime } from '$lib/utils/time-formatting';
	import { toast } from '$lib/stores/toast';
	import { FileBarChart, Database, ChevronRight, AlertTriangle } from 'lucide-svelte';

	/**
	 * Get the appropriate URL for viewing a report.
	 * Uses standalone route for orphaned reports (where dataset was deleted).
	 */
	function getReportUrl(report: AllReportItem): string {
		if (report.dataset_id) {
			return `/datasets/${report.dataset_id}/report/${report.id}`;
		}
		// Orphaned report - use standalone route
		return `/reports/data/${report.id}`;
	}

	let isLoading = $state(true);
	let reports = $state<AllReportItem[]>([]);

	async function fetchReports() {
		isLoading = true;
		try {
			const response = await apiClient.listAllReports();
			reports = response.reports || [];
		} catch (err) {
			console.error('Failed to fetch reports:', err);
			toast.error(err instanceof Error ? err.message : 'Failed to load data reports');
		} finally {
			isLoading = false;
		}
	}

	onMount(() => {
		fetchReports();
	});

	function truncateSummary(summary: string | null | undefined, maxLength: number = 120): string {
		if (!summary) return 'No summary available';
		if (summary.length <= maxLength) return summary;
		return summary.substring(0, maxLength) + '...';
	}
</script>

<svelte:head>
	<title>Data Reports - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Header -->
		<div class="flex items-center justify-between mb-6">
			<div>
				<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">Data Reports</h1>
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
					Generated reports from your data analysis
				</p>
			</div>
		</div>

		{#if isLoading}
			<div class="space-y-4">
				{#each Array(3) as _, i (i)}
					<ShimmerSkeleton type="card" />
				{/each}
			</div>
		{:else if reports.length === 0}
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-12 text-center">
				<FileBarChart class="w-16 h-16 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" />
				<h2 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-2">No data reports yet</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-md mx-auto">
					Generate reports from your data analysis to see them here. Start by analyzing a dataset in the Advisor section.
				</p>
				<a
					href="/advisor/analyze"
					class="inline-flex items-center gap-2 text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 font-medium"
				>
					Go to Advisor &gt; Analyze
					<ChevronRight class="w-4 h-4" />
				</a>
			</div>
		{:else}
			<div class="space-y-4">
				{#each reports as report (report.id)}
					<a
						href={getReportUrl(report)}
						class="block bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-200"
					>
						<div class="flex items-start justify-between gap-4">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-3 mb-2">
									{#if report.dataset_name}
										<span class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400">
											<Database class="w-3 h-3" />
											{report.dataset_name}
										</span>
									{:else}
										<span class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
											<AlertTriangle class="w-3 h-3" />
											Dataset Deleted
										</span>
									{/if}
									<span class="text-xs text-neutral-500 dark:text-neutral-400">
										{formatCompactRelativeTime(report.created_at)}
									</span>
								</div>

								<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
									{report.title}
								</h3>

								<p class="text-sm text-neutral-600 dark:text-neutral-400">
									{truncateSummary(report.executive_summary)}
								</p>
							</div>

							<div class="flex items-center gap-2 flex-shrink-0">
								<ChevronRight class="w-5 h-5 text-neutral-400 dark:text-neutral-500" />
							</div>
						</div>
					</a>
				{/each}
			</div>
		{/if}
	</main>
</div>
