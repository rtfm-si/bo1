<script lang="ts">
	/**
	 * DatasetComparison - Side-by-side comparison of two datasets
	 *
	 * Displays schema, statistics, and key metrics differences.
	 */
	import type {
		DatasetComparison,
		SchemaComparison,
		StatisticsComparison,
		KeyMetricsComparison
	} from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';

	interface Props {
		comparison: DatasetComparison | null;
		loading?: boolean;
		error?: string | null;
		onClose?: () => void;
	}

	let { comparison, loading = false, error = null, onClose }: Props = $props();

	// Expand/collapse sections
	let schemaExpanded = $state(true);
	let statsExpanded = $state(true);
	let metricsExpanded = $state(true);
	let insightsExpanded = $state(true);

	// Format percent change with +/- sign
	function formatPercent(value: number | null): string {
		if (value === null) return 'N/A';
		const sign = value > 0 ? '+' : '';
		return `${sign}${value.toFixed(1)}%`;
	}

	// Format delta with +/- sign
	function formatDelta(value: number | null): string {
		if (value === null) return 'N/A';
		const sign = value > 0 ? '+' : '';
		return `${sign}${value.toLocaleString()}`;
	}

	// Get color class for percent change
	function getChangeColor(value: number | null, higherIsBetter = true): string {
		if (value === null) return 'text-neutral-500';
		const isPositive = higherIsBetter ? value > 0 : value < 0;
		const isNegative = higherIsBetter ? value < 0 : value > 0;
		if (isPositive) return 'text-success-600 dark:text-success-400';
		if (isNegative) return 'text-error-600 dark:text-error-400';
		return 'text-neutral-500';
	}
</script>

{#if loading}
	<div class="space-y-4">
		<ShimmerSkeleton class="h-8 w-48" />
		<ShimmerSkeleton class="h-32 w-full" />
		<ShimmerSkeleton class="h-48 w-full" />
	</div>
{:else if error}
	<div class="rounded-lg border border-error-200 bg-error-50 p-4 dark:border-error-800 dark:bg-error-900/20">
		<p class="text-error-700 dark:text-error-300">{error}</p>
	</div>
{:else if comparison}
	<div class="space-y-6">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<div>
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
					{#if comparison.name}
						{comparison.name}
					{:else}
						Dataset Comparison
					{/if}
				</h2>
				<p class="mt-1 text-sm text-neutral-500">
					<span class="font-medium">{comparison.dataset_a_name ?? 'Dataset A'}</span>
					vs
					<span class="font-medium">{comparison.dataset_b_name ?? 'Dataset B'}</span>
				</p>
			</div>
			{#if onClose}
				<button
					onclick={onClose}
					aria-label="Close comparison"
					class="rounded-md p-2 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-500 dark:hover:bg-neutral-800"
				>
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			{/if}
		</div>

		<!-- Insights Summary -->
		{#if comparison.insights && comparison.insights.length > 0}
			<div class="rounded-lg border border-primary-200 bg-primary-50 p-4 dark:border-primary-800 dark:bg-primary-900/20">
				<button
					onclick={() => (insightsExpanded = !insightsExpanded)}
					class="flex w-full items-center justify-between text-left"
				>
					<h3 class="text-sm font-medium text-primary-900 dark:text-primary-100">Key Findings</h3>
					<svg
						class="h-5 w-5 transform text-primary-500 transition-transform {insightsExpanded ? 'rotate-180' : ''}"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if insightsExpanded}
					<ul class="mt-3 space-y-2">
						{#each comparison.insights as insight}
							<li class="flex items-start gap-2 text-sm text-primary-800 dark:text-primary-200">
								<svg class="mt-0.5 h-4 w-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
										clip-rule="evenodd"
									/>
								</svg>
								{insight}
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		{/if}

		<!-- Row Count Summary -->
		<div class="grid grid-cols-3 gap-4">
			<div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-700 dark:bg-neutral-800">
				<p class="text-xs font-medium uppercase tracking-wide text-neutral-500">
					{comparison.dataset_a_name ?? 'Dataset A'}
				</p>
				<p class="mt-1 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
					{comparison.statistics_comparison.row_count_a.toLocaleString()}
				</p>
				<p class="text-xs text-neutral-500">rows</p>
			</div>
			<div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-700 dark:bg-neutral-800">
				<p class="text-xs font-medium uppercase tracking-wide text-neutral-500">
					{comparison.dataset_b_name ?? 'Dataset B'}
				</p>
				<p class="mt-1 text-2xl font-semibold text-neutral-900 dark:text-neutral-100">
					{comparison.statistics_comparison.row_count_b.toLocaleString()}
				</p>
				<p class="text-xs text-neutral-500">rows</p>
			</div>
			<div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-700 dark:bg-neutral-800">
				<p class="text-xs font-medium uppercase tracking-wide text-neutral-500">Change</p>
				<p class="mt-1 text-2xl font-semibold {getChangeColor(comparison.statistics_comparison.row_count_percent_change)}">
					{formatDelta(comparison.statistics_comparison.row_count_delta)}
				</p>
				<p class="text-xs {getChangeColor(comparison.statistics_comparison.row_count_percent_change)}">
					{formatPercent(comparison.statistics_comparison.row_count_percent_change)}
				</p>
			</div>
		</div>

		<!-- Schema Comparison -->
		<div class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900">
			<button
				onclick={() => (schemaExpanded = !schemaExpanded)}
				class="flex w-full items-center justify-between text-left"
			>
				<h3 class="text-sm font-medium text-neutral-900 dark:text-neutral-100">Schema Comparison</h3>
				<svg
					class="h-5 w-5 transform text-neutral-400 transition-transform {schemaExpanded ? 'rotate-180' : ''}"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
			</button>
			{#if schemaExpanded}
				<div class="mt-4 grid gap-4 md:grid-cols-3">
					<!-- Common Columns -->
					<div>
						<p class="text-xs font-medium uppercase tracking-wide text-neutral-500">
							Common ({comparison.schema_comparison.common_columns.length})
						</p>
						<ul class="mt-2 space-y-1">
							{#each comparison.schema_comparison.common_columns.slice(0, 10) as col}
								<li class="text-sm text-neutral-600 dark:text-neutral-400">{col}</li>
							{/each}
							{#if comparison.schema_comparison.common_columns.length > 10}
								<li class="text-xs text-neutral-400">
									+{comparison.schema_comparison.common_columns.length - 10} more
								</li>
							{/if}
						</ul>
					</div>
					<!-- Only in A -->
					<div>
						<p class="text-xs font-medium uppercase tracking-wide text-warning-600 dark:text-warning-400">
							Only in {comparison.dataset_a_name ?? 'A'} ({comparison.schema_comparison.only_in_a.length})
						</p>
						{#if comparison.schema_comparison.only_in_a.length > 0}
							<ul class="mt-2 space-y-1">
								{#each comparison.schema_comparison.only_in_a.slice(0, 10) as col}
									<li class="text-sm text-warning-600 dark:text-warning-400">{col}</li>
								{/each}
								{#if comparison.schema_comparison.only_in_a.length > 10}
									<li class="text-xs text-neutral-400">
										+{comparison.schema_comparison.only_in_a.length - 10} more
									</li>
								{/if}
							</ul>
						{:else}
							<p class="mt-2 text-sm text-neutral-400">None</p>
						{/if}
					</div>
					<!-- Only in B -->
					<div>
						<p class="text-xs font-medium uppercase tracking-wide text-warning-600 dark:text-warning-400">
							Only in {comparison.dataset_b_name ?? 'B'} ({comparison.schema_comparison.only_in_b.length})
						</p>
						{#if comparison.schema_comparison.only_in_b.length > 0}
							<ul class="mt-2 space-y-1">
								{#each comparison.schema_comparison.only_in_b.slice(0, 10) as col}
									<li class="text-sm text-warning-600 dark:text-warning-400">{col}</li>
								{/each}
								{#if comparison.schema_comparison.only_in_b.length > 10}
									<li class="text-xs text-neutral-400">
										+{comparison.schema_comparison.only_in_b.length - 10} more
									</li>
								{/if}
							</ul>
						{:else}
							<p class="mt-2 text-sm text-neutral-400">None</p>
						{/if}
					</div>
				</div>
				<!-- Type Mismatches -->
				{#if comparison.schema_comparison.type_mismatches.length > 0}
					<div class="mt-4 border-t border-neutral-200 pt-4 dark:border-neutral-700">
						<p class="text-xs font-medium uppercase tracking-wide text-error-600 dark:text-error-400">
							Type Mismatches ({comparison.schema_comparison.type_mismatches.length})
						</p>
						<ul class="mt-2 space-y-1">
							{#each comparison.schema_comparison.type_mismatches as mismatch}
								<li class="text-sm text-error-600 dark:text-error-400">
									<span class="font-medium">{mismatch.column}</span>: {mismatch.type_a} vs {mismatch.type_b}
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			{/if}
		</div>

		<!-- Key Metrics Comparison -->
		{#if comparison.key_metrics_comparison.metrics.length > 0}
			<div class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900">
				<button
					onclick={() => (metricsExpanded = !metricsExpanded)}
					class="flex w-full items-center justify-between text-left"
				>
					<h3 class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
						Key Metrics
						{#if comparison.key_metrics_comparison.significant_changes > 0}
							<span class="ml-2 rounded-full bg-warning-100 px-2 py-0.5 text-xs text-warning-700 dark:bg-warning-900/30 dark:text-warning-300">
								{comparison.key_metrics_comparison.significant_changes} significant
							</span>
						{/if}
					</h3>
					<svg
						class="h-5 w-5 transform text-neutral-400 transition-transform {metricsExpanded ? 'rotate-180' : ''}"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if metricsExpanded}
					<div class="mt-4 overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b border-neutral-200 dark:border-neutral-700">
									<th class="pb-2 text-left font-medium text-neutral-500">Metric</th>
									<th class="pb-2 text-right font-medium text-neutral-500">{comparison.dataset_a_name ?? 'A'}</th>
									<th class="pb-2 text-right font-medium text-neutral-500">{comparison.dataset_b_name ?? 'B'}</th>
									<th class="pb-2 text-right font-medium text-neutral-500">Change</th>
								</tr>
							</thead>
							<tbody>
								{#each comparison.key_metrics_comparison.metrics as metric}
									<tr class="border-b border-neutral-100 dark:border-neutral-800">
										<td class="py-2 text-neutral-900 dark:text-neutral-100">
											{metric.metric_name}
											{#if metric.is_significant}
												<span class="ml-1 text-warning-500" title="Significant change">*</span>
											{/if}
										</td>
										<td class="py-2 text-right text-neutral-600 dark:text-neutral-400">
											{metric.value_a.toLocaleString(undefined, { maximumFractionDigits: 2 })}
										</td>
										<td class="py-2 text-right text-neutral-600 dark:text-neutral-400">
											{metric.value_b.toLocaleString(undefined, { maximumFractionDigits: 2 })}
										</td>
										<td class="py-2 text-right {getChangeColor(metric.percent_change)}">
											{formatPercent(metric.percent_change)}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Statistics Deltas -->
		{#if comparison.statistics_comparison.column_deltas.length > 0}
			<div class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900">
				<button
					onclick={() => (statsExpanded = !statsExpanded)}
					class="flex w-full items-center justify-between text-left"
				>
					<h3 class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
						Column Statistics
					</h3>
					<svg
						class="h-5 w-5 transform text-neutral-400 transition-transform {statsExpanded ? 'rotate-180' : ''}"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if statsExpanded}
					<div class="mt-4 space-y-4">
						{#each comparison.statistics_comparison.column_deltas.slice(0, 10) as colDelta}
							<div class="rounded-md border border-neutral-100 p-3 dark:border-neutral-800">
								<p class="font-medium text-neutral-900 dark:text-neutral-100">
									{colDelta.column}
									<span class="ml-2 text-xs font-normal text-neutral-500">{colDelta.dtype}</span>
								</p>
								<div class="mt-2 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
									{#each Object.entries(colDelta.stat_deltas) as [statName, statDelta]}
										<div class="rounded bg-neutral-50 px-2 py-1 dark:bg-neutral-800">
											<span class="text-neutral-500">{statName}:</span>
											{#if statDelta.percent_change !== null && statDelta.percent_change !== undefined}
												<span class={getChangeColor(statDelta.percent_change)}>
													{formatPercent(statDelta.percent_change)}
												</span>
											{:else if statDelta.delta !== null && statDelta.delta !== undefined}
												<span class={getChangeColor(statDelta.delta)}>
													{formatDelta(statDelta.delta)}
												</span>
											{:else}
												<span class="text-neutral-400">-</span>
											{/if}
										</div>
									{/each}
								</div>
							</div>
						{/each}
						{#if comparison.statistics_comparison.column_deltas.length > 10}
							<p class="text-center text-sm text-neutral-500">
								+{comparison.statistics_comparison.column_deltas.length - 10} more columns
							</p>
						{/if}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Timestamp -->
		<p class="text-right text-xs text-neutral-400">
			Compared at {new Date(comparison.created_at).toLocaleString()}
		</p>
	</div>
{:else}
	<div class="rounded-lg border border-neutral-200 bg-neutral-50 p-8 text-center dark:border-neutral-700 dark:bg-neutral-800">
		<svg class="mx-auto h-12 w-12 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
			/>
		</svg>
		<p class="mt-4 text-neutral-600 dark:text-neutral-400">No comparison data</p>
	</div>
{/if}
