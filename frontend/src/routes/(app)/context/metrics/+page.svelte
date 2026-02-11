<script lang="ts">
	/**
	 * Business Metrics - Layer 3 (KPIs and Performance Data)
	 * Progressive disclosure UI with smart selection:
	 * - Auto-detects business model from user context (API)
	 * - Shows filled metrics first
	 * - Shows top 5 high-priority unfilled templates prominently
	 * - Collapses remaining templates under "Show more metrics"
	 */
	import { onMount } from 'svelte';
	import { apiClient, type UserMetric, type MetricTemplate, type MetricCategory } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import BenchmarkRefreshBanner from '$lib/components/benchmarks/BenchmarkRefreshBanner.svelte';
	import MetricCalculatorModal from '$lib/components/context/MetricCalculatorModal.svelte';
	import BusinessMetricSuggestions from '$lib/components/context/BusinessMetricSuggestions.svelte';
	import { preferredCurrency } from '$lib/stores/preferences';
	import { getCurrencySymbol } from '$lib/utils/currency';

	import { formatDate } from '$lib/utils/time-formatting';
	// Config
	const TOP_UNFILLED_COUNT = 5;

	// State
	let metrics = $state<UserMetric[]>([]);
	let templates = $state<MetricTemplate[]>([]);
	let hiddenMetrics = $state<UserMetric[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let savingMetric = $state<string | null>(null);
	let saveSuccess = $state<string | null>(null);

	// Edit state
	let editingMetric = $state<string | null>(null);
	let editValue = $state<string>('');

	// Dismiss state
	let dismissingMetric = $state<string | null>(null);
	let confirmDismiss = $state<string | null>(null);

	// Hidden metrics section
	let hiddenExpanded = $state(false);
	let restoringMetric = $state<string | null>(null);

	// More metrics section (progressive disclosure)
	let moreMetricsExpanded = $state(false);

	// Calculator modal state
	let calculatorOpen = $state(false);

	// Group metrics by category
	const categoryLabels: Record<MetricCategory, string> = {
		financial: 'Financial',
		growth: 'Growth',
		retention: 'Retention',
		efficiency: 'Efficiency',
		custom: 'Custom'
	};

	const categoryOrder: MetricCategory[] = ['financial', 'growth', 'retention', 'efficiency', 'custom'];

	// Derived: filled metrics (user has saved a value)
	const filledMetrics = $derived(() => {
		return metrics.filter((m) => m.value !== null).sort((a, b) => a.display_order - b.display_order);
	});

	// Derived: unfilled saved metrics (user saved but no value yet)
	const unfilledSavedMetrics = $derived(() => {
		return metrics.filter((m) => m.value === null).sort((a, b) => a.display_order - b.display_order);
	});

	// Derived: top priority unfilled templates (not saved yet)
	// Templates already ordered by priority ASC from API
	const topUnfilledTemplates = $derived(() => {
		const savedKeys = new Set(metrics.map((m) => m.metric_key));
		const unsaved = templates.filter((t) => !savedKeys.has(t.metric_key));
		return unsaved.slice(0, TOP_UNFILLED_COUNT);
	});

	// Derived: remaining unfilled templates (collapsed by default)
	const remainingTemplates = $derived(() => {
		const savedKeys = new Set(metrics.map((m) => m.metric_key));
		const unsaved = templates.filter((t) => !savedKeys.has(t.metric_key));
		return unsaved.slice(TOP_UNFILLED_COUNT);
	});

	// Helper to convert template to UserMetric-like for rendering
	function templateToMetric(t: MetricTemplate): UserMetric {
		return {
			id: '',
			user_id: '',
			metric_key: t.metric_key,
			name: t.name,
			definition: t.definition,
			importance: t.importance,
			category: t.category,
			value: null,
			value_unit: t.value_unit,
			captured_at: null,
			source: 'manual' as const,
			is_predefined: true,
			is_relevant: true,
			display_order: t.display_order,
			created_at: '',
			updated_at: ''
		};
	}

	onMount(async () => {
		await loadMetrics();
	});

	async function loadMetrics() {
		isLoading = true;
		error = null;

		try {
			const response = await apiClient.getMetrics(undefined, true);
			metrics = response.metrics;
			templates = response.templates;
			hiddenMetrics = response.hidden_metrics || [];
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load metrics';
			console.error('Failed to load metrics:', e);
		} finally {
			isLoading = false;
		}
	}

	function startEdit(metric: UserMetric) {
		editingMetric = metric.metric_key;
		editValue = metric.value !== null ? String(metric.value) : '';
	}

	function cancelEdit() {
		editingMetric = null;
		editValue = '';
	}

	async function saveMetric(metric: UserMetric) {
		const key = metric.metric_key;
		savingMetric = key;

		try {
			// Ensure editValue is string (input type="number" may return number in Svelte 5)
			const valueStr = String(editValue ?? '').trim();
			const numValue = valueStr === '' ? null : parseFloat(valueStr);

			if (valueStr !== '' && (numValue === null || isNaN(numValue))) {
				throw new Error('Please enter a valid number');
			}

			await apiClient.updateMetric(key, numValue);

			// Update local state
			const existingIndex = metrics.findIndex((m) => m.metric_key === key);
			if (existingIndex >= 0) {
				metrics[existingIndex].value = numValue;
				metrics[existingIndex].captured_at = new Date().toISOString();
			} else {
				// Need to reload to get the new metric
				await loadMetrics();
			}

			saveSuccess = key;
			setTimeout(() => {
				saveSuccess = null;
			}, 2000);

			editingMetric = null;
			editValue = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save metric';
		} finally {
			savingMetric = null;
		}
	}

	function formatValue(value: number | null, unit: string | null): string {
		if (value === null) return '—';

		const num = typeof value === 'number' ? value : parseFloat(String(value));
		if (isNaN(num)) return '—';

		const currencySymbol = getCurrencySymbol($preferredCurrency);

		switch (unit) {
			case '$':
				return `${currencySymbol}${num.toLocaleString()}`;
			case '%':
				return `${num}%`;
			case 'months':
				return `${num} mo`;
			case 'ratio':
				return `${num}:1`;
			default:
				return num.toLocaleString();
		}
	}


	async function dismissMetric(metricKey: string) {
		dismissingMetric = metricKey;
		try {
			await apiClient.setMetricRelevance(metricKey, false);
			// Move from active to hidden (optimistic UI)
			const dismissed = metrics.find((m) => m.metric_key === metricKey);
			if (dismissed) {
				dismissed.is_relevant = false;
				hiddenMetrics = [...hiddenMetrics, dismissed];
			}
			metrics = metrics.filter((m) => m.metric_key !== metricKey);
			confirmDismiss = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to dismiss metric';
		} finally {
			dismissingMetric = null;
		}
	}

	async function restoreMetric(metricKey: string) {
		restoringMetric = metricKey;
		try {
			await apiClient.setMetricRelevance(metricKey, true);
			// Move from hidden to active (optimistic UI)
			const restored = hiddenMetrics.find((m) => m.metric_key === metricKey);
			if (restored) {
				restored.is_relevant = true;
				metrics = [...metrics, restored].sort((a, b) => a.display_order - b.display_order);
			}
			hiddenMetrics = hiddenMetrics.filter((m) => m.metric_key !== metricKey);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to restore metric';
		} finally {
			restoringMetric = null;
		}
	}

	async function handleCalculated(metricKey: string, value: number, unit: string) {
		// Save the calculated value to the metric
		try {
			await apiClient.updateMetric(metricKey, value);
			// Reload to refresh the display
			await loadMetrics();
			saveSuccess = metricKey;
			setTimeout(() => {
				saveSuccess = null;
			}, 2000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save calculated value';
		}
	}

	async function handleSuggestionApplied(event: { metricKey: string; value: number }) {
		// Reload metrics to show the updated value
		await loadMetrics();
		saveSuccess = event.metricKey;
		setTimeout(() => {
			saveSuccess = null;
		}, 2000);
	}
</script>

{#snippet metricRow(metric: UserMetric, isSaved: boolean)}
	<div
		class="flex items-start justify-between py-3 border-b border-neutral-100 dark:border-neutral-700 last:border-0"
	>
		<div class="flex-1 min-w-0 pr-4">
			<div class="flex items-center gap-2">
				<p class="font-medium text-neutral-900 dark:text-white">
					{metric.name}
				</p>
				{#if saveSuccess === metric.metric_key}
					<span class="text-xs text-success-600 dark:text-success-400">Saved!</span>
				{/if}
				{#if !isSaved}
					<span class="text-xs px-1.5 py-0.5 bg-info-100 dark:bg-info-900/30 text-info-600 dark:text-info-400 rounded">
						{categoryLabels[metric.category || 'custom']}
					</span>
				{/if}
			</div>
			<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
				{metric.definition || 'No description'}
			</p>
			{#if metric.importance}
				<p class="text-xs text-neutral-400 dark:text-neutral-500 mt-1 flex items-center gap-1">
					<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					{metric.importance}
				</p>
			{/if}
			{#if metric.captured_at}
				<p class="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
					Updated: {formatDate(metric.captured_at)}
				</p>
			{/if}
		</div>

		<div class="flex items-center gap-3">
			{#if editingMetric === metric.metric_key}
				<!-- Edit Mode -->
				<div class="flex items-center gap-2">
					{#if metric.value_unit === '$'}
						<span class="text-neutral-400">{getCurrencySymbol($preferredCurrency)}</span>
					{/if}
					<input
						type="number"
						bind:value={editValue}
						class="w-28 px-3 py-1.5 text-sm border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
						placeholder="Enter value"
						onkeydown={(e) => {
							if (e.key === 'Enter') saveMetric(metric);
							if (e.key === 'Escape') cancelEdit();
						}}
					/>
					{#if metric.value_unit && metric.value_unit !== '$'}
						<span class="text-sm text-neutral-400">{metric.value_unit}</span>
					{/if}
					<button
						class="p-1.5 text-success-600 hover:bg-success-50 dark:hover:bg-success-900/20 rounded"
						onclick={() => saveMetric(metric)}
						disabled={savingMetric === metric.metric_key}
					>
						{#if savingMetric === metric.metric_key}
							<div class="w-4 h-4 border-2 border-success-600 border-t-transparent rounded-full animate-spin"></div>
						{:else}
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
							</svg>
						{/if}
					</button>
					<button
						class="p-1.5 text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded"
						onclick={cancelEdit}
						aria-label="Cancel"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			{:else}
				<!-- Display Mode -->
				<div class="flex items-center gap-1 group">
					<button
						class="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
						onclick={() => startEdit(metric)}
					>
						<span
							class={[
								'text-lg font-semibold',
								metric.value !== null
									? 'text-neutral-900 dark:text-white'
									: 'text-neutral-400 dark:text-neutral-500'
							].join(' ')}
						>
							{formatValue(metric.value, metric.value_unit)}
						</span>
						<svg
							class="w-4 h-4 text-neutral-400 opacity-0 group-hover:opacity-100 transition-opacity"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
							/>
						</svg>
					</button>
					<!-- Dismiss button for predefined metrics that are saved -->
					{#if metric.is_predefined && metric.id}
						{#if confirmDismiss === metric.metric_key}
							<!-- Confirmation inline -->
							<div class="flex items-center gap-1 ml-2 px-2 py-1 bg-warning-50 dark:bg-warning-900/20 rounded border border-warning-200 dark:border-warning-800">
								<span class="text-xs text-warning-700 dark:text-warning-300">Hide?</span>
								<button
									class="p-1 text-success-600 hover:bg-success-100 dark:hover:bg-success-900/30 rounded"
									onclick={() => dismissMetric(metric.metric_key)}
									disabled={dismissingMetric === metric.metric_key}
									title="Confirm hide"
								>
									{#if dismissingMetric === metric.metric_key}
										<div class="w-3 h-3 border-2 border-success-600 border-t-transparent rounded-full animate-spin"></div>
									{:else}
										<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
										</svg>
									{/if}
								</button>
								<button
									class="p-1 text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded"
									onclick={() => { confirmDismiss = null; }}
									title="Cancel"
								>
									<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</div>
						{:else}
							<button
								class="p-1.5 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded opacity-0 group-hover:opacity-100 transition-opacity"
								onclick={() => { confirmDismiss = metric.metric_key; }}
								title="Not relevant to me"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
								</svg>
							</button>
						{/if}
					{/if}
				</div>
			{/if}
		</div>
	</div>
{/snippet}

<svelte:head>
	<title>Business Metrics - Board of One</title>
</svelte:head>

<div class="space-y-6">
	<!-- Benchmark Refresh Banner -->
	<BenchmarkRefreshBanner />

	<!-- Header -->
	<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
		<div class="flex items-center justify-between">
			<div>
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
					Business Metrics
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400">
					Track key performance indicators for context-aware recommendations.
				</p>
			</div>
		</div>
	</div>

	<!-- Metric Suggestions from Insights -->
	<BusinessMetricSuggestions onapplied={handleSuggestionApplied} />

	<!-- Error Alert -->
	{#if error}
		<Alert variant="error">
			{error}
			<button
				class="ml-2 underline"
				onclick={() => {
					error = null;
				}}
			>
				Dismiss
			</button>
		</Alert>
	{/if}

	<!-- Loading State -->
	{#if isLoading}
		<div class="flex items-center justify-center py-12">
			<Spinner size="lg" />
		</div>
	{:else}
		<!-- SECTION 1: Your Metrics (filled values) -->
		{#if filledMetrics().length > 0}
			<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
				<h3 class="text-sm font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-4">
					Your Metrics
				</h3>
				<div class="space-y-4">
					{#each filledMetrics() as metric (metric.metric_key)}
						{@render metricRow(metric, true)}
					{/each}
				</div>
			</div>
		{/if}

		<!-- SECTION 2: Recommended Metrics (top unfilled templates) -->
		{#if topUnfilledTemplates().length > 0 || unfilledSavedMetrics().length > 0}
			<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
				<h3 class="text-sm font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-4">
					Recommended Metrics
					<span class="ml-2 text-xs font-normal normal-case text-neutral-400">Click to add a value</span>
				</h3>
				<div class="space-y-4">
					<!-- Unfilled saved metrics first -->
					{#each unfilledSavedMetrics() as metric (metric.metric_key)}
						{@render metricRow(metric, true)}
					{/each}
					<!-- Then top templates -->
					{#each topUnfilledTemplates() as template (template.metric_key)}
						{@render metricRow(templateToMetric(template), false)}
					{/each}
				</div>
			</div>
		{/if}

		<!-- SECTION 3: More Metrics (collapsed remaining templates) -->
		{#if remainingTemplates().length > 0}
			<div class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg border border-neutral-200 dark:border-neutral-700">
				<button
					class="w-full p-4 flex items-center justify-between text-left hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors rounded-lg"
					onclick={() => { moreMetricsExpanded = !moreMetricsExpanded; }}
				>
					<div class="flex items-center gap-3">
						<span class="text-neutral-400">
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
							</svg>
						</span>
						<div>
							<span class="font-medium text-neutral-700 dark:text-neutral-300">More Metrics</span>
							<span class="ml-2 text-xs font-medium px-2 py-0.5 bg-neutral-200 dark:bg-neutral-600 text-neutral-600 dark:text-neutral-300 rounded-full">
								{remainingTemplates().length}
							</span>
						</div>
					</div>
					<svg
						class="w-5 h-5 text-neutral-400 transition-transform {moreMetricsExpanded ? 'rotate-180' : ''}"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>

				{#if moreMetricsExpanded}
					<div class="px-4 pb-4 space-y-3">
						{#each remainingTemplates() as template (template.metric_key)}
							{@render metricRow(templateToMetric(template), false)}
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Hidden Metrics Section (collapsible) -->
		{#if hiddenMetrics.length > 0}
			<div class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg border border-neutral-200 dark:border-neutral-700">
				<button
					class="w-full p-4 flex items-center justify-between text-left hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors rounded-lg"
					onclick={() => { hiddenExpanded = !hiddenExpanded; }}
				>
					<div class="flex items-center gap-3">
						<span class="text-neutral-400">
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
							</svg>
						</span>
						<div>
							<span class="font-medium text-neutral-700 dark:text-neutral-300">Hidden Metrics</span>
							<span class="ml-2 text-xs font-medium px-2 py-0.5 bg-neutral-200 dark:bg-neutral-600 text-neutral-600 dark:text-neutral-300 rounded-full">
								{hiddenMetrics.length}
							</span>
						</div>
					</div>
					<svg
						class="w-5 h-5 text-neutral-400 transition-transform {hiddenExpanded ? 'rotate-180' : ''}"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>

				{#if hiddenExpanded}
					<div class="px-4 pb-4 space-y-2">
						{#each hiddenMetrics as metric (metric.metric_key)}
							<div class="flex items-center justify-between py-2 px-3 bg-white dark:bg-neutral-800 rounded-md border border-neutral-200 dark:border-neutral-600">
								<div class="flex-1 min-w-0">
									<p class="font-medium text-neutral-700 dark:text-neutral-300 text-sm">{metric.name}</p>
									<p class="text-xs text-neutral-500 dark:text-neutral-400 truncate">{metric.definition || 'No description'}</p>
								</div>
								<Button
									variant="ghost"
									size="sm"
									onclick={() => restoreMetric(metric.metric_key)}
									disabled={restoringMetric === metric.metric_key}
								>
									{#if restoringMetric === metric.metric_key}
										<div class="w-4 h-4 border-2 border-brand-600 border-t-transparent rounded-full animate-spin"></div>
									{:else}
										<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
										</svg>
										Restore
									{/if}
								</Button>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Industry Benchmarks Link -->
		<div class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg p-4 flex items-center justify-between">
			<div class="flex items-center gap-3">
				<span class="text-xl">📊</span>
				<div>
					<p class="font-medium text-neutral-900 dark:text-white">Industry Benchmarks</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">Compare your metrics against industry standards</p>
				</div>
			</div>
			<a href="/reports/benchmarks" class="text-sm font-medium text-brand-600 dark:text-brand-400 hover:underline">
				View Benchmarks →
			</a>
		</div>

		<!-- Help Me Calculate CTA -->
		<div class="bg-brand-50 dark:bg-brand-900/20 rounded-lg p-4 flex items-center justify-between border border-brand-200 dark:border-brand-800">
			<div class="flex items-center gap-3">
				<span class="text-xl">🧮</span>
				<div>
					<p class="font-medium text-neutral-900 dark:text-white">Help me calculate</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">Answer a few questions to derive your metric values</p>
				</div>
			</div>
			<Button variant="brand" size="sm" onclick={() => { calculatorOpen = true; }}>
				Calculate
			</Button>
		</div>

		<!-- Request Metric CTA -->
		<div class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg p-4 flex items-center justify-between">
			<div class="flex items-center gap-3">
				<span class="text-xl">💡</span>
				<div>
					<p class="font-medium text-neutral-900 dark:text-white">Need a different metric?</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">Request a metric that's not listed</p>
				</div>
			</div>
			<a
				href="mailto:feedback@boardofone.com?subject=Metric%20Request"
				target="_blank"
				rel="noopener noreferrer"
				class="text-sm font-medium text-brand-600 dark:text-brand-400 hover:underline"
			>
				Request →
			</a>
		</div>

		<!-- Info Box -->
		<div class="bg-info-50 dark:bg-info-900/20 border border-info-200 dark:border-info-800 rounded-lg p-4">
			<div class="flex gap-3">
				<svg
					class="w-5 h-5 text-info-600 dark:text-info-400 flex-shrink-0 mt-0.5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<div class="text-sm text-info-900 dark:text-info-200">
					<p class="font-semibold mb-1">Why track metrics?</p>
					<p class="text-info-800 dark:text-info-300">
						When you provide key metrics, our experts can give data-informed recommendations.
						Instead of generic advice, they can tailor guidance to your specific numbers -
						like suggesting churn reduction strategies when your churn is high.
					</p>
				</div>
			</div>
		</div>
	{/if}
</div>

<!-- Metric Calculator Modal -->
<MetricCalculatorModal
	bind:open={calculatorOpen}
	onClose={() => { calculatorOpen = false; }}
	onCalculated={handleCalculated}
/>
