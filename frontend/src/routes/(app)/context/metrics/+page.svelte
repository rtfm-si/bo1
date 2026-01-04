<script lang="ts">
	/**
	 * Business Metrics - Layer 3 (KPIs and Performance Data)
	 * Full implementation with API integration
	 */
	import { onMount } from 'svelte';
	import { apiClient, type UserMetric, type MetricTemplate, type MetricCategory } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import BenchmarkRefreshBanner from '$lib/components/benchmarks/BenchmarkRefreshBanner.svelte';
	import { preferredCurrency } from '$lib/stores/preferences';
	import { getCurrencySymbol } from '$lib/utils/currency';

	// State
	let metrics = $state<UserMetric[]>([]);
	let templates = $state<MetricTemplate[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let savingMetric = $state<string | null>(null);
	let saveSuccess = $state<string | null>(null);

	// Edit state
	let editingMetric = $state<string | null>(null);
	let editValue = $state<string>('');

	// Group metrics by category
	const categoryLabels: Record<MetricCategory, string> = {
		financial: 'Financial',
		growth: 'Growth',
		retention: 'Retention',
		efficiency: 'Efficiency',
		custom: 'Custom'
	};

	const categoryOrder: MetricCategory[] = ['financial', 'growth', 'retention', 'efficiency', 'custom'];

	// Derived: all metrics (saved + templates)
	const allMetrics = $derived(() => {
		// Combine saved metrics and templates
		const savedKeys = new Set(metrics.map((m) => m.metric_key));
		const unsaved = templates.filter((t) => !savedKeys.has(t.metric_key));

		// Convert templates to UserMetric-like objects
		const templateMetrics: UserMetric[] = unsaved.map((t) => ({
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
			display_order: t.display_order,
			created_at: '',
			updated_at: ''
		}));

		return [...metrics, ...templateMetrics].sort((a, b) => a.display_order - b.display_order);
	});

	// Derived: metrics grouped by category
	const metricsByCategory = $derived(() => {
		const grouped: Record<MetricCategory, UserMetric[]> = {
			financial: [],
			growth: [],
			retention: [],
			efficiency: [],
			custom: []
		};

		for (const metric of allMetrics()) {
			const category = metric.category || 'custom';
			grouped[category].push(metric);
		}

		return grouped;
	});

	onMount(async () => {
		await loadMetrics();
	});

	async function loadMetrics() {
		isLoading = true;
		error = null;

		try {
			const response = await apiClient.getMetrics();
			metrics = response.metrics;
			templates = response.templates;
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

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return 'Never';
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}
</script>

<svelte:head>
	<title>Business Metrics - Board of One</title>
</svelte:head>

<div class="space-y-6">
	<!-- Benchmark Refresh Banner -->
	<BenchmarkRefreshBanner />

	<!-- Header -->
	<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
		<div class="flex items-center justify-between">
			<div>
				<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-2">
					Business Metrics
				</h2>
				<p class="text-slate-600 dark:text-slate-400">
					Track key performance indicators for context-aware recommendations.
				</p>
			</div>
		</div>
	</div>

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
			<div class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"></div>
		</div>
	{:else}
		<!-- Metrics by Category -->
		{#each categoryOrder as category}
			{@const categoryMetrics = metricsByCategory()[category]}
			{#if categoryMetrics.length > 0}
				<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
					<h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-4">
						{categoryLabels[category]}
					</h3>
					<div class="space-y-4">
						{#each categoryMetrics as metric (metric.metric_key)}
							<div
								class="flex items-start justify-between py-3 border-b border-slate-100 dark:border-slate-700 last:border-0"
							>
								<div class="flex-1 min-w-0 pr-4">
									<div class="flex items-center gap-2">
										<p class="font-medium text-slate-900 dark:text-white">
											{metric.name}
										</p>
										{#if saveSuccess === metric.metric_key}
											<span class="text-xs text-green-600 dark:text-green-400">Saved!</span>
										{/if}
									</div>
									<p class="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
										{metric.definition || 'No description'}
									</p>
									{#if metric.importance}
										<p class="text-xs text-slate-400 dark:text-slate-500 mt-1 flex items-center gap-1">
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
									<p class="text-xs text-slate-400 dark:text-slate-500 mt-1">
										Updated: {formatDate(metric.captured_at)}
									</p>
								</div>

								<div class="flex items-center gap-3">
									{#if editingMetric === metric.metric_key}
										<!-- Edit Mode -->
										<div class="flex items-center gap-2">
											{#if metric.value_unit === '$'}
												<span class="text-slate-400">{getCurrencySymbol($preferredCurrency)}</span>
											{/if}
											<input
												type="number"
												bind:value={editValue}
												class="w-28 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
												placeholder="Enter value"
												onkeydown={(e) => {
													if (e.key === 'Enter') saveMetric(metric);
													if (e.key === 'Escape') cancelEdit();
												}}
											/>
											{#if metric.value_unit && metric.value_unit !== '$'}
												<span class="text-sm text-slate-400">{metric.value_unit}</span>
											{/if}
											<button
												class="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
												onclick={() => saveMetric(metric)}
												disabled={savingMetric === metric.metric_key}
											>
												{#if savingMetric === metric.metric_key}
													<div class="w-4 h-4 border-2 border-green-600 border-t-transparent rounded-full animate-spin"></div>
												{:else}
													<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
													</svg>
												{/if}
											</button>
											<button
												class="p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
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
										<button
											class="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors group"
											onclick={() => startEdit(metric)}
										>
											<span
												class={[
													'text-lg font-semibold',
													metric.value !== null
														? 'text-slate-900 dark:text-white'
														: 'text-slate-400 dark:text-slate-500'
												].join(' ')}
											>
												{formatValue(metric.value, metric.value_unit)}
											</span>
											<svg
												class="w-4 h-4 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity"
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
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		{/each}

		<!-- Industry Benchmarks Link -->
		<div class="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4 flex items-center justify-between">
			<div class="flex items-center gap-3">
				<span class="text-xl">📊</span>
				<div>
					<p class="font-medium text-slate-900 dark:text-white">Industry Benchmarks</p>
					<p class="text-sm text-slate-500 dark:text-slate-400">Compare your metrics against industry standards</p>
				</div>
			</div>
			<a href="/reports/benchmarks" class="text-sm font-medium text-brand-600 dark:text-brand-400 hover:underline">
				View Benchmarks →
			</a>
		</div>

		<!-- Info Box -->
		<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
			<div class="flex gap-3">
				<svg
					class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5"
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
				<div class="text-sm text-blue-900 dark:text-blue-200">
					<p class="font-semibold mb-1">Why track metrics?</p>
					<p class="text-blue-800 dark:text-blue-300">
						When you provide key metrics, our experts can give data-informed recommendations.
						Instead of generic advice, they can tailor guidance to your specific numbers -
						like suggesting churn reduction strategies when your churn is high.
					</p>
				</div>
			</div>
		</div>
	{/if}
</div>
