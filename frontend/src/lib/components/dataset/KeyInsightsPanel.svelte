<script lang="ts">
	/**
	 * KeyInsightsPanel - Displays 8 deterministic analyses as Key Insights
	 *
	 * Shows analysis results in collapsible sections with visual indicators.
	 */
	import type { DatasetInvestigation } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { SvelteSet } from 'svelte/reactivity';

	interface Props {
		investigation: DatasetInvestigation | null;
		loading?: boolean;
		error?: string | null;
		onRefresh?: () => void;
		onUpdateColumnRole?: (columnName: string, newRole: string) => Promise<void>;
	}

	let { investigation, loading = false, error = null, onRefresh, onUpdateColumnRole }: Props = $props();

	// Role editing state
	let editingRole = $state<string | null>(null);
	let savingRole = $state(false);

	const roleOptions = ['metric', 'dimension', 'id', 'timestamp', 'unknown'] as const;

	async function handleRoleChange(columnName: string, newRole: string) {
		if (!onUpdateColumnRole || savingRole) return;
		savingRole = true;
		try {
			await onUpdateColumnRole(columnName, newRole);
		} finally {
			savingRole = false;
			editingRole = null;
		}
	}

	// Track expanded sections
	let expandedSections = new SvelteSet(['column_roles', 'data_quality']);

	function toggleSection(section: string) {
		if (expandedSections.has(section)) {
			expandedSections.delete(section);
		} else {
			expandedSections.add(section);
		}
	}

	function getRoleColor(role: string): string {
		switch (role) {
			case 'id':
				return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300';
			case 'timestamp':
				return 'bg-info-100 text-info-700 dark:bg-info-900/30 dark:text-info-300';
			case 'metric':
				return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300';
			case 'dimension':
				return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300';
			default:
				return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400';
		}
	}

	function getSeverityColor(severity: string): string {
		switch (severity) {
			case 'high':
				return 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300';
			case 'medium':
				return 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300';
			case 'low':
				return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400';
			default:
				return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400';
		}
	}

	function getScoreColor(score: number): string {
		if (score >= 80) return 'text-success-600 dark:text-success-400';
		if (score >= 60) return 'text-warning-600 dark:text-warning-400';
		return 'text-error-600 dark:text-error-400';
	}

	function getScoreBg(score: number): string {
		if (score >= 80) return 'bg-success-500';
		if (score >= 60) return 'bg-warning-500';
		return 'bg-error-500';
	}

	function formatPercent(value: number): string {
		return `${value.toFixed(1)}%`;
	}

	function formatCorrelation(value: number): string {
		return value.toFixed(3);
	}

	// Derived stats
	const totalColumns = $derived(investigation?.column_roles?.roles?.length ?? 0);
	const metricsCount = $derived(investigation?.column_roles?.metric_columns?.length ?? 0);
	const dimensionsCount = $derived(investigation?.column_roles?.dimension_columns?.length ?? 0);
	const columnsWithNulls = $derived(investigation?.missingness?.columns_with_nulls ?? 0);
	const outlierColumns = $derived(investigation?.outliers?.columns_with_outliers ?? 0);
	const qualityScore = $derived(investigation?.data_quality?.overall_score ?? 0);

	// Normalized data with safe defaults to prevent undefined errors
	const safeData = $derived({
		columnRoles: investigation?.column_roles?.roles ?? [],
		missingnessColumns: investigation?.missingness?.columns ?? [],
		highNullColumns: investigation?.missingness?.high_null_columns ?? [],
		numericColumns: investigation?.descriptive_stats?.numeric_columns ?? [],
		categoricalColumns: investigation?.descriptive_stats?.categorical_columns ?? [],
		outliers: investigation?.outliers?.outliers ?? [],
		potentialLeakage: investigation?.correlations?.potential_leakage ?? [],
		topPositive: investigation?.correlations?.top_positive ?? [],
		topNegative: investigation?.correlations?.top_negative ?? [],
		tsReady: investigation?.time_series_readiness?.is_ready ?? false,
		tsTimestampColumn: investigation?.time_series_readiness?.timestamp_column ?? null,
		tsFrequency: investigation?.time_series_readiness?.detected_frequency ?? null,
		tsDateRange: investigation?.time_series_readiness?.date_range ?? null,
		tsGapCount: investigation?.time_series_readiness?.gap_count ?? 0,
		tsRecommendations: investigation?.time_series_readiness?.recommendations ?? [],
		segmentationOpportunities: investigation?.segmentation_suggestions?.opportunities ?? [],
		bestDimensions: investigation?.segmentation_suggestions?.best_dimensions ?? [],
		qualityIssues: investigation?.data_quality?.issues ?? [],
		completenessScore: investigation?.data_quality?.completeness_score ?? 0,
		consistencyScore: investigation?.data_quality?.consistency_score ?? 0,
		validityScore: investigation?.data_quality?.validity_score ?? 0,
	});
</script>

{#if loading}
	<div class="space-y-4">
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
				<h3 class="font-semibold text-error-900 dark:text-error-200">Failed to load investigation</h3>
				<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
			</div>
		</div>
		{#if onRefresh}
			<button
				onclick={onRefresh}
				class="mt-4 px-4 py-2 bg-error-600 hover:bg-error-700 text-white rounded-lg text-sm font-medium transition-colors"
			>
				Try Again
			</button>
		{/if}
	</div>
{:else if investigation}
	<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
		<!-- Header -->
		<div class="p-6 border-b border-neutral-200 dark:border-neutral-700">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<span class="p-2 rounded-lg bg-brand-100 dark:bg-brand-900/30">
						<svg class="w-5 h-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
						</svg>
					</span>
					<div>
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Key Insights</h2>
						<p class="text-sm text-neutral-500 dark:text-neutral-400">8 automated analyses of your dataset</p>
					</div>
				</div>
				<!-- Quick stats -->
				<div class="flex items-center gap-4 text-sm">
					<div class="text-center">
						<div class="font-semibold text-neutral-900 dark:text-white">{totalColumns}</div>
						<div class="text-xs text-neutral-500">Columns</div>
					</div>
					<div class="text-center">
						<div class="font-semibold text-success-600 dark:text-success-400">{metricsCount}</div>
						<div class="text-xs text-neutral-500">Metrics</div>
					</div>
					<div class="text-center">
						<div class="font-semibold text-orange-600 dark:text-orange-400">{dimensionsCount}</div>
						<div class="text-xs text-neutral-500">Dimensions</div>
					</div>
					<div class="text-center">
						<div class="font-semibold {getScoreColor(qualityScore)}">{qualityScore}%</div>
						<div class="text-xs text-neutral-500">Quality</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Analysis Sections -->
		<div class="divide-y divide-neutral-200 dark:divide-neutral-700">
			<!-- 1. Column Roles -->
			<div class="p-4">
				<button
					onclick={() => toggleSection('column_roles')}
					class="w-full flex items-center justify-between text-left"
				>
					<div class="flex items-center gap-3">
						<span class="p-1.5 rounded bg-purple-100 dark:bg-purple-900/30">
							<svg class="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
							</svg>
						</span>
						<span class="font-medium text-neutral-900 dark:text-white">Column Roles</span>
						<span class="text-xs text-neutral-500">({investigation.column_roles?.roles?.length ?? 0} columns classified)</span>
					</div>
					<svg class="w-5 h-5 text-neutral-400 transition-transform {expandedSections.has('column_roles') ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if expandedSections.has('column_roles')}
					<div class="mt-3 pl-10">
						<div class="flex flex-wrap gap-2">
							{#each safeData.columnRoles as col}
								{#if editingRole === col.column}
									<!-- Editing mode -->
									<div class="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium bg-white dark:bg-neutral-700 border border-brand-300 dark:border-brand-600 shadow-sm">
										<span class="text-neutral-700 dark:text-neutral-200">{col.column}:</span>
										<select
											class="bg-transparent text-xs font-medium focus:outline-none cursor-pointer"
											value={col.role}
											disabled={savingRole}
											onchange={(e) => handleRoleChange(col.column, e.currentTarget.value)}
										>
											{#each roleOptions as opt}
												<option value={opt}>{opt}</option>
											{/each}
										</select>
										<button
											onclick={() => editingRole = null}
											class="ml-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
											title="Cancel"
										>
											<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
											</svg>
										</button>
									</div>
								{:else}
									<!-- Display mode - clickable to edit -->
									<button
										onclick={() => onUpdateColumnRole && (editingRole = col.column)}
										class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium {getRoleColor(col.role)} {onUpdateColumnRole ? 'hover:ring-2 hover:ring-brand-300 dark:hover:ring-brand-600 cursor-pointer' : ''} transition-all"
										title={onUpdateColumnRole ? 'Click to change role' : undefined}
										disabled={!onUpdateColumnRole}
									>
										<span>{col.column}</span>
										<span class="opacity-70">({col.role})</span>
										{#if col.role === 'unknown' && onUpdateColumnRole}
											<svg class="w-3 h-3 text-warning-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
											</svg>
										{/if}
									</button>
								{/if}
							{/each}
						</div>
						{#if onUpdateColumnRole}
							<p class="mt-2 text-xs text-neutral-500 dark:text-neutral-400">Click a column to change its role</p>
						{/if}
					</div>
				{/if}
			</div>

			<!-- 2. Missingness & Cardinality -->
			<div class="p-4">
				<button
					onclick={() => toggleSection('missingness')}
					class="w-full flex items-center justify-between text-left"
				>
					<div class="flex items-center gap-3">
						<span class="p-1.5 rounded bg-warning-100 dark:bg-warning-900/30">
							<svg class="w-4 h-4 text-warning-600 dark:text-warning-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
						</span>
						<span class="font-medium text-neutral-900 dark:text-white">Missingness & Cardinality</span>
						{#if columnsWithNulls > 0}
							<span class="text-xs px-2 py-0.5 rounded-full bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300">
								{columnsWithNulls} columns with nulls
							</span>
						{:else}
							<span class="text-xs text-success-600 dark:text-success-400">No missing data</span>
						{/if}
					</div>
					<svg class="w-5 h-5 text-neutral-400 transition-transform {expandedSections.has('missingness') ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if expandedSections.has('missingness')}
					<div class="mt-3 pl-10">
						<!-- Contextual explanation -->
						<p class="text-xs text-neutral-500 dark:text-neutral-400 mb-3">
							<strong>Null %</strong> = missing values that may need filling or handling.
							<strong>Cardinality</strong> = unique value count (low = good for grouping, high = identifiers).
						</p>
						{#if safeData.highNullColumns.length > 0}
							<div class="mb-3 p-3 bg-warning-50 dark:bg-warning-900/20 rounded-lg">
								<div class="text-sm font-medium text-warning-700 dark:text-warning-300">High null columns need attention:</div>
								<div class="text-sm text-warning-600 dark:text-warning-400">{safeData.highNullColumns.join(', ')}</div>
								<p class="text-xs text-warning-500 dark:text-warning-400 mt-1">Consider: fill with defaults, exclude from analysis, or investigate why data is missing.</p>
							</div>
						{/if}
						<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 text-xs">
							{#each safeData.missingnessColumns.slice(0, 12) as col}
								<div class="p-2 bg-neutral-50 dark:bg-neutral-700/50 rounded">
									<div class="font-medium text-neutral-700 dark:text-neutral-300 truncate" title={col.column}>{col.column}</div>
									<div class="text-neutral-500 dark:text-neutral-400">
										{formatPercent(col.null_percent)} null | {col.cardinality_category}
									</div>
								</div>
							{/each}
						</div>
						{#if safeData.missingnessColumns.length > 12}
							<div class="mt-2 text-xs text-neutral-500">+{safeData.missingnessColumns.length - 12} more columns</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- 3. Descriptive Stats -->
			<div class="p-4">
				<button
					onclick={() => toggleSection('descriptive_stats')}
					class="w-full flex items-center justify-between text-left"
				>
					<div class="flex items-center gap-3">
						<span class="p-1.5 rounded bg-info-100 dark:bg-info-900/30">
							<svg class="w-4 h-4 text-info-600 dark:text-info-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
							</svg>
						</span>
						<span class="font-medium text-neutral-900 dark:text-white">Descriptive Statistics</span>
						<span class="text-xs text-neutral-500">
							({safeData.numericColumns.length} numeric, {safeData.categoricalColumns.length} categorical)
						</span>
					</div>
					<svg class="w-5 h-5 text-neutral-400 transition-transform {expandedSections.has('descriptive_stats') ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if expandedSections.has('descriptive_stats')}
					<div class="mt-3 pl-10 space-y-4">
						{#if safeData.numericColumns.length > 0}
							<div>
								<div class="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-2">Numeric Columns</div>
								<div class="overflow-x-auto">
									<table class="min-w-full text-xs">
										<thead>
											<tr class="text-left text-neutral-500 dark:text-neutral-400">
												<th class="pr-4 py-1">Column</th>
												<th class="pr-4 py-1">Mean</th>
												<th class="pr-4 py-1">Median</th>
												<th class="pr-4 py-1">Min</th>
												<th class="pr-4 py-1">Max</th>
											</tr>
										</thead>
										<tbody class="text-neutral-700 dark:text-neutral-300">
											{#each safeData.numericColumns.slice(0, 8) as col}
												<tr>
													<td class="pr-4 py-1 font-medium">{col.column}</td>
													<td class="pr-4 py-1">{col.mean?.toFixed(2) ?? '-'}</td>
													<td class="pr-4 py-1">{col.median?.toFixed(2) ?? '-'}</td>
													<td class="pr-4 py-1">{col.min ?? '-'}</td>
													<td class="pr-4 py-1">{col.max ?? '-'}</td>
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							</div>
						{/if}
						{#if safeData.categoricalColumns.length > 0}
							<div>
								<div class="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-2">Top Categorical Values</div>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
									{#each safeData.categoricalColumns.slice(0, 4) as col}
										<div class="p-2 bg-neutral-50 dark:bg-neutral-700/50 rounded">
											<div class="font-medium text-neutral-700 dark:text-neutral-300 mb-1">{col.column}</div>
											{#if col.top_values}
												<div class="space-y-1">
													{#each col.top_values.slice(0, 3) as tv}
														<div class="flex justify-between text-neutral-500 dark:text-neutral-400">
															<span class="truncate">{tv.value}</span>
															<span>{formatPercent(tv.percent)}</span>
														</div>
													{/each}
												</div>
											{/if}
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- 4. Outliers -->
			<div class="p-4">
				<button
					onclick={() => toggleSection('outliers')}
					class="w-full flex items-center justify-between text-left"
				>
					<div class="flex items-center gap-3">
						<span class="p-1.5 rounded bg-error-100 dark:bg-error-900/30">
							<svg class="w-4 h-4 text-error-600 dark:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
							</svg>
						</span>
						<span class="font-medium text-neutral-900 dark:text-white">Outliers</span>
						{#if outlierColumns > 0}
							<span class="text-xs px-2 py-0.5 rounded-full bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300">
								{outlierColumns} columns affected
							</span>
						{:else}
							<span class="text-xs text-success-600 dark:text-success-400">No outliers detected</span>
						{/if}
					</div>
					<svg class="w-5 h-5 text-neutral-400 transition-transform {expandedSections.has('outliers') ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if expandedSections.has('outliers')}
					<div class="mt-3 pl-10">
						<!-- Contextual explanation -->
						<p class="text-xs text-neutral-500 dark:text-neutral-400 mb-3">
							Outliers are values far from typical ranges. They may be data entry errors, special cases, or genuine extremes worth investigating.
						</p>
						{#if safeData.outliers.length > 0}
							<div class="space-y-2">
								{#each safeData.outliers as o}
									<div class="p-2 bg-orange-50 dark:bg-orange-900/20 rounded text-sm border border-orange-200 dark:border-orange-800">
										<span class="font-medium text-orange-700 dark:text-orange-300">{o.column}</span>
										<span class="text-orange-600 dark:text-orange-400">: {o.outlier_count} outliers ({formatPercent(o.outlier_percent)})</span>
										{#if o.lower_bound !== null && o.upper_bound !== null}
											<span class="text-xs text-orange-500 dark:text-orange-400"> | normal range: [{o.lower_bound?.toFixed(2)}, {o.upper_bound?.toFixed(2)}]</span>
										{/if}
									</div>
								{/each}
							</div>
							<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-2">
								Consider: verify data accuracy, filter outliers for analysis, or investigate what caused extreme values.
							</p>
						{:else}
							<div class="text-sm text-neutral-500 dark:text-neutral-400">No significant outliers detected in numeric columns.</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- 5. Correlations -->
			<div class="p-4">
				<button
					onclick={() => toggleSection('correlations')}
					class="w-full flex items-center justify-between text-left"
				>
					<div class="flex items-center gap-3">
						<span class="p-1.5 rounded bg-indigo-100 dark:bg-indigo-900/30">
							<svg class="w-4 h-4 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
							</svg>
						</span>
						<span class="font-medium text-neutral-900 dark:text-white">Correlations</span>
						{#if safeData.potentialLeakage.length > 0}
							<span class="text-xs px-2 py-0.5 rounded-full bg-info-100 text-info-700 dark:bg-info-900/30 dark:text-info-300">
								{safeData.potentialLeakage.length} highly correlated
							</span>
						{/if}
					</div>
					<svg class="w-5 h-5 text-neutral-400 transition-transform {expandedSections.has('correlations') ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if expandedSections.has('correlations')}
					<div class="mt-3 pl-10 space-y-3">
						<!-- Contextual explanation -->
						<p class="text-xs text-neutral-500 dark:text-neutral-400">
							Correlation measures how closely two columns move together (1.0 = perfect positive, -1.0 = perfect negative, 0 = no relationship).
						</p>
						{#if safeData.potentialLeakage.length > 0}
							<div class="p-3 bg-info-50 dark:bg-info-900/20 rounded-lg border border-info-200 dark:border-info-800">
								<div class="text-sm font-medium text-info-700 dark:text-info-300 mb-1 flex items-center gap-2">
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
									Highly Correlated Pairs
								</div>
								<div class="text-xs text-info-600 dark:text-info-400 space-y-1">
									{#each safeData.potentialLeakage as pair}
										<div>{pair.column_a} ↔ {pair.column_b}: {formatCorrelation(pair.correlation)}</div>
									{/each}
								</div>
								<p class="text-xs text-info-500 dark:text-info-400 mt-2">
									<strong>Review needed:</strong> High correlation may be expected (e.g., Gross Sales ↔ Net Sales) or indicate redundant columns.
									If using for ML, consider if one column derives from another.
								</p>
							</div>
						{/if}
						<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
							{#if safeData.topPositive.length > 0}
								<div>
									<div class="text-xs font-medium text-success-600 dark:text-success-400 mb-1">Top Positive</div>
									<div class="space-y-1 text-xs">
										{#each safeData.topPositive.slice(0, 5) as pair}
											<div class="flex justify-between text-neutral-600 dark:text-neutral-400">
												<span>{pair.column_a} ↔ {pair.column_b}</span>
												<span class="text-success-600 dark:text-success-400">+{formatCorrelation(pair.correlation)}</span>
											</div>
										{/each}
									</div>
								</div>
							{/if}
							{#if safeData.topNegative.length > 0}
								<div>
									<div class="text-xs font-medium text-error-600 dark:text-error-400 mb-1">Top Negative</div>
									<div class="space-y-1 text-xs">
										{#each safeData.topNegative.slice(0, 5) as pair}
											<div class="flex justify-between text-neutral-600 dark:text-neutral-400">
												<span>{pair.column_a} ↔ {pair.column_b}</span>
												<span class="text-error-600 dark:text-error-400">{formatCorrelation(pair.correlation)}</span>
											</div>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>

			<!-- 6. Time Series Readiness -->
			<div class="p-4">
				<button
					onclick={() => toggleSection('time_series')}
					class="w-full flex items-center justify-between text-left"
				>
					<div class="flex items-center gap-3">
						<span class="p-1.5 rounded bg-cyan-100 dark:bg-cyan-900/30">
							<svg class="w-4 h-4 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
						</span>
						<span class="font-medium text-neutral-900 dark:text-white">Time Series Readiness</span>
						{#if safeData.tsReady}
							<span class="text-xs px-2 py-0.5 rounded-full bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300">Ready</span>
						{:else}
							<span class="text-xs px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400">Not time-series</span>
						{/if}
					</div>
					<svg class="w-5 h-5 text-neutral-400 transition-transform {expandedSections.has('time_series') ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if expandedSections.has('time_series')}
					<div class="mt-3 pl-10">
						{#if safeData.tsReady}
							<div class="space-y-2 text-sm">
								<div><span class="text-neutral-500 dark:text-neutral-400">Timestamp column:</span> <span class="font-medium text-neutral-700 dark:text-neutral-300">{safeData.tsTimestampColumn}</span></div>
								{#if safeData.tsFrequency}
									<div><span class="text-neutral-500 dark:text-neutral-400">Frequency:</span> <span class="font-medium text-neutral-700 dark:text-neutral-300">{safeData.tsFrequency}</span></div>
								{/if}
								{#if safeData.tsDateRange}
									<div><span class="text-neutral-500 dark:text-neutral-400">Date range:</span> <span class="font-medium text-neutral-700 dark:text-neutral-300">{safeData.tsDateRange.start} to {safeData.tsDateRange.end}</span></div>
								{/if}
								{#if safeData.tsGapCount > 0}
									<div class="text-warning-600 dark:text-warning-400">{safeData.tsGapCount} gaps detected in time series</div>
								{/if}
							</div>
						{:else}
							<div class="text-sm text-neutral-500 dark:text-neutral-400">
								{#if safeData.tsRecommendations.length > 0}
									<ul class="list-disc pl-4 space-y-1">
										{#each safeData.tsRecommendations as rec}
											<li>{rec}</li>
										{/each}
									</ul>
								{:else}
									No timestamp column detected for time series analysis.
								{/if}
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- 7. Segmentation Builder -->
			<div class="p-4">
				<button
					onclick={() => toggleSection('segmentation')}
					class="w-full flex items-center justify-between text-left"
				>
					<div class="flex items-center gap-3">
						<span class="p-1.5 rounded bg-pink-100 dark:bg-pink-900/30">
							<svg class="w-4 h-4 text-pink-600 dark:text-pink-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
							</svg>
						</span>
						<span class="font-medium text-neutral-900 dark:text-white">Segmentation Opportunities</span>
						{#if safeData.segmentationOpportunities.length > 0}
							<span class="text-xs text-neutral-500">({safeData.segmentationOpportunities.length} found)</span>
						{/if}
					</div>
					<svg class="w-5 h-5 text-neutral-400 transition-transform {expandedSections.has('segmentation') ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if expandedSections.has('segmentation')}
					<div class="mt-3 pl-10">
						{#if safeData.segmentationOpportunities.length > 0}
							<div class="space-y-2">
								{#each safeData.segmentationOpportunities.slice(0, 5) as opp}
									<div class="p-2 bg-pink-50 dark:bg-pink-900/20 rounded text-sm">
										<div class="font-medium text-pink-700 dark:text-pink-300">{opp.dimension} x {opp.metric}</div>
										<div class="text-xs text-pink-600 dark:text-pink-400">{opp.recommendation}</div>
									</div>
								{/each}
							</div>
						{:else}
							<div class="text-sm text-neutral-500 dark:text-neutral-400">
								No strong segmentation opportunities found. Try adding dimension columns.
							</div>
						{/if}
						{#if safeData.bestDimensions.length > 0}
							<div class="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
								<span class="font-medium">Best dimensions:</span> {safeData.bestDimensions.join(', ')}
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- 8. Data Quality -->
			<div class="p-4">
				<button
					onclick={() => toggleSection('data_quality')}
					class="w-full flex items-center justify-between text-left"
				>
					<div class="flex items-center gap-3">
						<span class="p-1.5 rounded bg-success-100 dark:bg-success-900/30">
							<svg class="w-4 h-4 text-success-600 dark:text-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
							</svg>
						</span>
						<span class="font-medium text-neutral-900 dark:text-white">Data Quality</span>
						<span class="text-xs px-2 py-0.5 rounded-full {qualityScore >= 80 ? 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300' : qualityScore >= 60 ? 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300' : 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300'}">
							{qualityScore}% overall
						</span>
					</div>
					<svg class="w-5 h-5 text-neutral-400 transition-transform {expandedSections.has('data_quality') ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>
				{#if expandedSections.has('data_quality')}
					<div class="mt-3 pl-10">
						<!-- Score breakdown -->
						<div class="grid grid-cols-3 gap-4 mb-4">
							<div class="text-center">
								<div class="text-lg font-semibold {getScoreColor(safeData.completenessScore)}">{safeData.completenessScore}%</div>
								<div class="text-xs text-neutral-500">Completeness</div>
							</div>
							<div class="text-center">
								<div class="text-lg font-semibold {getScoreColor(safeData.consistencyScore)}">{safeData.consistencyScore}%</div>
								<div class="text-xs text-neutral-500">Consistency</div>
							</div>
							<div class="text-center">
								<div class="text-lg font-semibold {getScoreColor(safeData.validityScore)}">{safeData.validityScore}%</div>
								<div class="text-xs text-neutral-500">Validity</div>
							</div>
						</div>
						<!-- Issues -->
						{#if safeData.qualityIssues.length > 0}
							<div class="space-y-2">
								{#each safeData.qualityIssues as issue}
									<div class="p-2 rounded text-sm {getSeverityColor(issue.severity)}">
										<div class="flex items-center gap-2">
											<span class="font-medium">{issue.column}</span>
											<span class="text-xs opacity-70">{issue.issue_type}</span>
										</div>
										<div class="text-xs mt-1">{issue.description}</div>
									</div>
								{/each}
							</div>
						{:else}
							<div class="text-sm text-success-600 dark:text-success-400">No data quality issues detected.</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>
{:else}
	<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
		<svg class="w-12 h-12 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
		</svg>
		<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">No Investigation Yet</h3>
		<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
			Run an investigation to get detailed insights about your dataset.
		</p>
		{#if onRefresh}
			<button
				onclick={onRefresh}
				class="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-medium transition-colors"
			>
				Run Investigation
			</button>
		{/if}
	</div>
{/if}
