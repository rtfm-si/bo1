<script lang="ts">
	/**
	 * MultiDatasetAnalysisResults - Display cross-dataset anomaly detection results
	 *
	 * Shows schema drift, metric outliers, and pairwise comparisons for 2-5 datasets.
	 */
	import type {
		MultiDatasetAnalysisResponse,
		MultiDatasetAnomaly,
		MultiDatasetSummary,
		MultiDatasetCommonSchema
	} from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		analysis: MultiDatasetAnalysisResponse | null;
		loading?: boolean;
		error?: string | null;
		onClose?: () => void;
	}

	let { analysis, loading = false, error = null, onClose }: Props = $props();

	// Expand/collapse sections
	let anomaliesExpanded = $state(true);
	let schemaExpanded = $state(true);
	let summariesExpanded = $state(false);
	let pairwiseExpanded = $state(false);

	// Get severity badge variant
	function getSeverityVariant(severity: string): 'error' | 'warning' | 'neutral' {
		switch (severity) {
			case 'high':
				return 'error';
			case 'medium':
				return 'warning';
			default:
				return 'neutral';
		}
	}

	// Get anomaly type display name
	function getAnomalyTypeName(type: string): string {
		switch (type) {
			case 'schema_drift':
				return 'Schema Drift';
			case 'metric_outlier':
				return 'Metric Outlier';
			case 'type_mismatch':
				return 'Type Mismatch';
			case 'no_common_columns':
				return 'No Common Columns';
			default:
				return type;
		}
	}

	// Count anomalies by severity
	function countBySeverity(anomalies: MultiDatasetAnomaly[]): { high: number; medium: number; low: number } {
		return anomalies.reduce(
			(acc, a) => {
				acc[a.severity as 'high' | 'medium' | 'low']++;
				return acc;
			},
			{ high: 0, medium: 0, low: 0 }
		);
	}
</script>

{#if loading}
	<div class="space-y-4">
		<ShimmerSkeleton class="h-8 w-64" />
		<ShimmerSkeleton class="h-24 w-full" />
		<ShimmerSkeleton class="h-48 w-full" />
	</div>
{:else if error}
	<div class="rounded-lg border border-error-200 bg-error-50 p-4 dark:border-error-800 dark:bg-error-900/20">
		<p class="text-error-700 dark:text-error-300">{error}</p>
	</div>
{:else if analysis}
	{@const severityCounts = countBySeverity(analysis.anomalies)}
	<div class="space-y-6">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<div>
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
					{#if analysis.name}
						{analysis.name}
					{:else}
						Multi-Dataset Analysis
					{/if}
				</h2>
				<p class="mt-1 text-sm text-neutral-500">
					Analyzing {analysis.dataset_names.length} datasets:
					<span class="font-medium">{analysis.dataset_names.join(', ')}</span>
				</p>
			</div>
			{#if onClose}
				<button
					onclick={onClose}
					aria-label="Close analysis"
					class="rounded-md p-2 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-500 dark:hover:bg-neutral-800"
				>
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			{/if}
		</div>

		<!-- Summary Stats -->
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
			<div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3 dark:border-neutral-700 dark:bg-neutral-800">
				<p class="text-xs text-neutral-500 dark:text-neutral-400">Datasets</p>
				<p class="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{analysis.dataset_names.length}</p>
			</div>
			<div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3 dark:border-neutral-700 dark:bg-neutral-800">
				<p class="text-xs text-neutral-500 dark:text-neutral-400">Common Columns</p>
				<p class="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
					{analysis.common_schema.common_columns.length}
				</p>
			</div>
			<div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3 dark:border-neutral-700 dark:bg-neutral-800">
				<p class="text-xs text-neutral-500 dark:text-neutral-400">Anomalies</p>
				<p class="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{analysis.anomalies.length}</p>
			</div>
			<div class="rounded-lg border border-error-200 bg-error-50 p-3 dark:border-error-700 dark:bg-error-900/20">
				<p class="text-xs text-error-600 dark:text-error-400">High Severity</p>
				<p class="text-xl font-semibold text-error-700 dark:text-error-300">{severityCounts.high}</p>
			</div>
		</div>

		<!-- Anomalies Section -->
		{#if analysis.anomalies.length > 0}
			<div class="rounded-lg border border-neutral-200 dark:border-neutral-700">
				<button
					onclick={() => (anomaliesExpanded = !anomaliesExpanded)}
					class="flex w-full items-center justify-between px-4 py-3 text-left"
				>
					<span class="font-medium text-neutral-900 dark:text-neutral-100">
						Detected Anomalies ({analysis.anomalies.length})
					</span>
					<svg
						class="h-5 w-5 text-neutral-500 transition-transform {anomaliesExpanded ? 'rotate-180' : ''}"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>

				{#if anomaliesExpanded}
					<div class="border-t border-neutral-200 dark:border-neutral-700">
						<ul class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each analysis.anomalies as anomaly}
								<li class="px-4 py-3">
									<div class="flex items-start gap-3">
										<Badge variant={getSeverityVariant(anomaly.severity)}>
											{anomaly.severity}
										</Badge>
										<div class="flex-1">
											<div class="flex items-center gap-2">
												<span class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
													{getAnomalyTypeName(anomaly.anomaly_type)}
												</span>
												{#if anomaly.column}
													<span class="text-xs text-neutral-500">
														Column: <code class="rounded bg-neutral-100 px-1 dark:bg-neutral-800">{anomaly.column}</code>
													</span>
												{/if}
											</div>
											<p class="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
												{anomaly.description}
											</p>
											<p class="mt-1 text-xs text-neutral-500">
												Affected: {anomaly.affected_datasets.join(', ')}
											</p>
										</div>
									</div>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</div>
		{:else}
			<div class="rounded-lg border border-success-200 bg-success-50 p-4 dark:border-success-800 dark:bg-success-900/20">
				<p class="text-success-700 dark:text-success-300">
					No anomalies detected across datasets.
				</p>
			</div>
		{/if}

		<!-- Common Schema Section -->
		<div class="rounded-lg border border-neutral-200 dark:border-neutral-700">
			<button
				onclick={() => (schemaExpanded = !schemaExpanded)}
				class="flex w-full items-center justify-between px-4 py-3 text-left"
			>
				<span class="font-medium text-neutral-900 dark:text-neutral-100">Common Schema</span>
				<svg
					class="h-5 w-5 text-neutral-500 transition-transform {schemaExpanded ? 'rotate-180' : ''}"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
			</button>

			{#if schemaExpanded}
				<div class="border-t border-neutral-200 p-4 dark:border-neutral-700">
					{#if analysis.common_schema.common_columns.length > 0}
						<div class="mb-4">
							<h4 class="mb-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
								Columns in All Datasets ({analysis.common_schema.common_columns.length})
							</h4>
							<div class="flex flex-wrap gap-2">
								{#each analysis.common_schema.common_columns as col}
									<code class="rounded bg-neutral-100 px-2 py-1 text-xs dark:bg-neutral-800">{col}</code>
								{/each}
							</div>
						</div>
					{/if}

					{#if Object.keys(analysis.common_schema.partial_columns).length > 0}
						<div class="mb-4">
							<h4 class="mb-2 text-sm font-medium text-neutral-700 dark:text-neutral-300">
								Columns in Some Datasets
							</h4>
							<div class="space-y-2">
								{#each Object.entries(analysis.common_schema.partial_columns) as [col, datasets]}
									<div class="flex items-center gap-2 text-sm">
										<code class="rounded bg-warning-100 px-2 py-1 text-xs dark:bg-warning-900/30">{col}</code>
										<span class="text-neutral-500">in: {datasets.join(', ')}</span>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					{#if Object.keys(analysis.common_schema.type_conflicts).length > 0}
						<div>
							<h4 class="mb-2 text-sm font-medium text-error-700 dark:text-error-300">
								Type Conflicts
							</h4>
							<div class="space-y-2">
								{#each Object.entries(analysis.common_schema.type_conflicts) as [col, typeMap]}
									<div class="text-sm">
										<code class="rounded bg-error-100 px-2 py-1 text-xs dark:bg-error-900/30">{col}</code>:
										{#each Object.entries(typeMap) as [ds, type], i}
											{#if i > 0}, {/if}
											<span class="text-neutral-600 dark:text-neutral-400">{ds}=<code>{type}</code></span>
										{/each}
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Dataset Summaries Section -->
		<div class="rounded-lg border border-neutral-200 dark:border-neutral-700">
			<button
				onclick={() => (summariesExpanded = !summariesExpanded)}
				class="flex w-full items-center justify-between px-4 py-3 text-left"
			>
				<span class="font-medium text-neutral-900 dark:text-neutral-100">Dataset Summaries</span>
				<svg
					class="h-5 w-5 text-neutral-500 transition-transform {summariesExpanded ? 'rotate-180' : ''}"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
			</button>

			{#if summariesExpanded}
				<div class="border-t border-neutral-200 dark:border-neutral-700">
					<div class="overflow-x-auto">
						<table class="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
							<thead class="bg-neutral-50 dark:bg-neutral-800">
								<tr>
									<th class="px-4 py-2 text-left text-xs font-medium text-neutral-500 uppercase">Dataset</th>
									<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Rows</th>
									<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Columns</th>
									<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Numeric</th>
									<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Categorical</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
								{#each analysis.dataset_summaries as summary}
									<tr>
										<td class="px-4 py-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">{summary.name}</td>
										<td class="px-4 py-2 text-right text-sm text-neutral-600 dark:text-neutral-400">{summary.row_count.toLocaleString()}</td>
										<td class="px-4 py-2 text-right text-sm text-neutral-600 dark:text-neutral-400">{summary.column_count}</td>
										<td class="px-4 py-2 text-right text-sm text-neutral-600 dark:text-neutral-400">{summary.numeric_columns.length}</td>
										<td class="px-4 py-2 text-right text-sm text-neutral-600 dark:text-neutral-400">{summary.categorical_columns.length}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{/if}
		</div>

		<!-- Pairwise Comparisons Section -->
		{#if analysis.pairwise_comparisons.length > 0}
			<div class="rounded-lg border border-neutral-200 dark:border-neutral-700">
				<button
					onclick={() => (pairwiseExpanded = !pairwiseExpanded)}
					class="flex w-full items-center justify-between px-4 py-3 text-left"
				>
					<span class="font-medium text-neutral-900 dark:text-neutral-100">
						Pairwise Comparisons ({analysis.pairwise_comparisons.length})
					</span>
					<svg
						class="h-5 w-5 text-neutral-500 transition-transform {pairwiseExpanded ? 'rotate-180' : ''}"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>

				{#if pairwiseExpanded}
					<div class="border-t border-neutral-200 p-4 dark:border-neutral-700">
						<div class="space-y-4">
							{#each analysis.pairwise_comparisons as comparison}
								{@const result = comparison.result as Record<string, unknown>}
								{@const insights = (result.insights as string[]) || []}
								<div class="rounded border border-neutral-100 p-3 dark:border-neutral-800">
									<h4 class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
										{comparison.dataset_a} vs {comparison.dataset_b}
									</h4>
									{#if insights.length > 0}
										<ul class="mt-2 space-y-1">
											{#each insights.slice(0, 3) as insight}
												<li class="text-sm text-neutral-600 dark:text-neutral-400">{insight}</li>
											{/each}
											{#if insights.length > 3}
												<li class="text-xs text-neutral-500">+{insights.length - 3} more</li>
											{/if}
										</ul>
									{:else}
										<p class="mt-2 text-sm text-neutral-500">No significant differences found.</p>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
{:else}
	<div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-center dark:border-neutral-700 dark:bg-neutral-800">
		<p class="text-neutral-500">Select 2-5 datasets to run multi-dataset analysis.</p>
	</div>
{/if}
