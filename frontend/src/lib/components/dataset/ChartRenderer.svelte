<script lang="ts">
	/**
	 * ChartRenderer - Renders Plotly charts with detail/simple dual-view modes
	 *
	 * Detail mode: Full interactive Plotly chart
	 * Simple mode: Static SVG sparkline with key stats
	 */
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import type { ChartSpec } from '$lib/api/types';

	// FigureJson can be the typed structure or a loose API response
	interface FigureJsonData {
		type?: string;
		x?: (string | number)[];
		y?: (string | number)[];
		values?: number[];
		labels?: string[];
		name?: string;
		[key: string]: unknown;
	}

	// Accept loose figure_json from API - we cast internally
	type FigureJsonInput = { data?: unknown[]; layout?: Record<string, unknown>; [key: string]: unknown } | null;

	interface Props {
		figureJson: FigureJsonInput;
		chartSpec?: ChartSpec | null;
		viewMode?: 'detail' | 'simple';
		title?: string;
		width?: number;
		height?: number;
		onModeChange?: (mode: 'detail' | 'simple') => void;
		onExpand?: () => void;
	}

	let {
		figureJson,
		chartSpec = null,
		viewMode = $bindable('simple'),
		title = '',
		width = 400,
		height = 250,
		onModeChange,
		onExpand
	}: Props = $props();

	let chartContainer: HTMLDivElement;
	let Plotly: typeof import('plotly.js-basic-dist') | null = null;
	let plotlyLoaded = $state(false);

	// Stats types
	interface NumericStats {
		type: 'numeric';
		min: number;
		max: number;
		mean: number;
		latest: number;
		count: number;
		trend: 'up' | 'down' | 'flat';
	}

	interface CategoricalStats {
		type: 'categorical';
		total: number;
		count: number;
		topCategory: string;
		topValue: number;
		topPercent: number;
	}

	type ChartStats = NumericStats | CategoricalStats;

	// Extended insights derived from data
	interface ChartInsight {
		type: 'highlight' | 'warning' | 'info';
		text: string;
		detail?: string;
	}

	// Compute stats from data
	const stats = $derived.by((): ChartStats | null => {
		if (!figureJson?.data?.[0]) return null;
		const trace = figureJson.data[0] as FigureJsonData;

		// For pie/donut charts, use values and labels
		if (trace.values && trace.labels) {
			const total = trace.values.reduce((a, b) => a + b, 0);
			const maxIdx = trace.values.indexOf(Math.max(...trace.values));
			return {
				type: 'categorical',
				total,
				count: trace.values.length,
				topCategory: trace.labels[maxIdx] as string,
				topValue: trace.values[maxIdx],
				topPercent: Math.round((trace.values[maxIdx] / total) * 100)
			};
		}

		// For numeric data (line, bar, scatter)
		const yData = (trace.y as number[] | undefined)?.filter(
			(v) => typeof v === 'number' && !isNaN(v)
		);
		if (!yData?.length) return null;

		const min = Math.min(...yData);
		const max = Math.max(...yData);
		const sum = yData.reduce((a, b) => a + b, 0);
		const mean = sum / yData.length;
		const latest = yData[yData.length - 1];

		return {
			type: 'numeric',
			min,
			max,
			mean,
			latest,
			count: yData.length,
			trend: yData.length > 1 ? (latest > yData[0] ? 'up' : latest < yData[0] ? 'down' : 'flat') : 'flat'
		};
	});

	// Derive insights from chart data
	const insights = $derived.by((): ChartInsight[] => {
		if (!figureJson?.data?.[0]) return [];
		const trace = figureJson.data[0] as FigureJsonData;
		const result: ChartInsight[] = [];

		// Categorical insights (bar charts with x categories)
		if (trace.x && trace.y && Array.isArray(trace.y)) {
			const xLabels = trace.x as string[];
			const yValues = (trace.y as number[]).filter((v) => typeof v === 'number');
			if (yValues.length > 0) {
				const total = yValues.reduce((a, b) => a + b, 0);
				const max = Math.max(...yValues);
				const maxIdx = yValues.indexOf(max);
				const min = Math.min(...yValues);
				const minIdx = yValues.indexOf(min);
				const mean = total / yValues.length;

				// Top performer
				if (xLabels[maxIdx] && total > 0) {
					const pct = Math.round((max / total) * 100);
					result.push({
						type: 'highlight',
						text: `${xLabels[maxIdx]} leads`,
						detail: `${formatNumber(max)} (${pct}% of total)`
					});
				}

				// Concentration check (Pareto-like)
				const sorted = [...yValues].sort((a, b) => b - a);
				const top2Sum = sorted.slice(0, 2).reduce((a, b) => a + b, 0);
				const top2Pct = Math.round((top2Sum / total) * 100);
				if (top2Pct >= 60 && yValues.length > 3) {
					result.push({
						type: 'info',
						text: 'Concentrated distribution',
						detail: `Top 2 categories = ${top2Pct}% of total`
					});
				}

				// Large gap between max and runner-up
				if (sorted.length > 1 && sorted[0] > sorted[1] * 2) {
					result.push({
						type: 'highlight',
						text: 'Clear leader',
						detail: `${formatNumber(sorted[0])} vs ${formatNumber(sorted[1])} (2nd place)`
					});
				}

				// Low performer warning
				if (xLabels[minIdx] && min < mean * 0.25 && yValues.length > 2) {
					result.push({
						type: 'warning',
						text: `${xLabels[minIdx]} underperforming`,
						detail: `Only ${formatNumber(min)} (${Math.round((min / mean) * 100)}% of avg)`
					});
				}
			}
		}

		// Pie chart insights
		if (trace.values && trace.labels) {
			const total = trace.values.reduce((a, b) => a + b, 0);
			const sorted = [...trace.values].sort((a, b) => b - a);
			const topPct = Math.round((sorted[0] / total) * 100);

			if (topPct >= 50) {
				const topIdx = trace.values.indexOf(sorted[0]);
				result.push({
					type: 'highlight',
					text: `${trace.labels[topIdx]} dominates`,
					detail: `${topPct}% of total`
				});
			}
		}

		return result.slice(0, 3); // Max 3 insights
	});

	// Generate SVG sparkline path
	const sparklinePath = $derived.by(() => {
		if (!figureJson?.data?.[0]) return '';
		const trace = figureJson.data[0] as FigureJsonData;

		// For pie charts, skip sparkline
		if (trace.values && trace.labels) return '';

		const yData = (trace.y as number[] | undefined)?.filter(
			(v) => typeof v === 'number' && !isNaN(v)
		);
		if (!yData?.length || yData.length < 2) return '';

		const min = Math.min(...yData);
		const max = Math.max(...yData);
		const range = max - min || 1;

		const sparkWidth = 120;
		const sparkHeight = 40;
		const xStep = sparkWidth / (yData.length - 1);

		const points = yData.map((val, i) => {
			const x = i * xStep;
			const y = sparkHeight - ((val - min) / range) * sparkHeight;
			return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
		});

		return points.join(' ');
	});

	// Load Plotly dynamically to avoid SSR issues
	onMount(async () => {
		if (browser) {
			Plotly = await import('plotly.js-basic-dist');
			plotlyLoaded = true;
		}
	});

	// Render chart when in detail mode
	// CRITICAL: Use structuredClone to break reactivity - Plotly mutates layout/data
	// which triggers Svelte's proxy and causes effect_update_depth_exceeded
	$effect(() => {
		if (browser && plotlyLoaded && Plotly && chartContainer && viewMode === 'detail' && figureJson?.data) {
			const isDark = document.documentElement.classList.contains('dark');

			// Deep clone to prevent Plotly mutations from triggering Svelte reactivity
			const chartData = structuredClone(figureJson.data) as import('plotly.js-basic-dist').Data[];
			const inputLayout = figureJson.layout ? structuredClone(figureJson.layout) : {};

			// Stephen Few-inspired defaults: maximize data-ink ratio, minimize chartjunk
			const layoutDefaults = {
				paper_bgcolor: 'transparent',
				plot_bgcolor: 'transparent',
				margin: { l: 60, r: 20, t: title ? 40 : 20, b: 60, pad: 4 },
				font: {
					family: 'Inter, system-ui, sans-serif',
					size: 11,
					color: isDark ? '#9ca3af' : '#6b7280'
				},
				autosize: true,
				showlegend: chartData.length > 1,
				legend: {
					orientation: 'h',
					yanchor: 'bottom',
					y: 1.02,
					xanchor: 'right',
					x: 1,
					bgcolor: 'transparent'
				},
				xaxis: {
					gridcolor: isDark ? '#374151' : '#f3f4f6',
					gridwidth: 1,
					zerolinecolor: isDark ? '#4b5563' : '#e5e7eb',
					zerolinewidth: 1,
					tickfont: { size: 10, color: isDark ? '#9ca3af' : '#6b7280' },
					title: { font: { size: 11, color: isDark ? '#d1d5db' : '#374151' } }
				},
				yaxis: {
					gridcolor: isDark ? '#374151' : '#f3f4f6',
					gridwidth: 1,
					zerolinecolor: isDark ? '#4b5563' : '#e5e7eb',
					zerolinewidth: 1,
					tickfont: { size: 10, color: isDark ? '#9ca3af' : '#6b7280' },
					title: { font: { size: 11, color: isDark ? '#d1d5db' : '#374151' } }
				},
				hoverlabel: {
					bgcolor: isDark ? '#1f2937' : '#ffffff',
					bordercolor: isDark ? '#374151' : '#e5e7eb',
					font: { size: 11, color: isDark ? '#f3f4f6' : '#111827' }
				}
			};

			// Apply Stephen Few styling and enhanced tooltips
			const annotations: Record<string, unknown>[] = [];

			for (const trace of chartData as Record<string, unknown>[]) {
				const traceData = trace as FigureJsonData;

				if (trace.type === 'bar' && traceData.x && traceData.y) {
					const yValues = traceData.y as number[];
					const xLabels = traceData.x as string[];
					const total = yValues.reduce((a: number, b: number) => a + (typeof b === 'number' ? b : 0), 0);
					const mean = total / yValues.length;
					const max = Math.max(...yValues.filter((v): v is number => typeof v === 'number'));
					const maxIdx = yValues.indexOf(max);

					// Use single solid color (no gradients/patterns)
					trace.marker = {
						...((trace.marker as Record<string, unknown>) || {}),
						color: isDark ? '#60a5fa' : '#3b82f6',
						line: { width: 0 }
					};

					// Rich hover template with context
					trace.hovertemplate =
						'<b>%{x}</b><br>' +
						'Value: <b>%{y:,.0f}</b><br>' +
						`% of Total: <b>%{customdata:.1f}%</b><br>` +
						'<extra></extra>';

					// Add custom data for % of total
					trace.customdata = yValues.map((v) => (typeof v === 'number' ? (v / total) * 100 : 0));

					// Add data labels on top of bars for values > 5% of max
					trace.text = yValues.map((v) => {
						if (typeof v === 'number' && v > max * 0.05) {
							return formatNumber(v);
						}
						return '';
					});
					trace.textposition = 'outside';
					trace.textfont = {
						size: 9,
						color: isDark ? '#9ca3af' : '#6b7280'
					};
					trace.cliponaxis = false;

					// Annotation for max value
					if (xLabels[maxIdx] && max > 0) {
						annotations.push({
							x: xLabels[maxIdx],
							y: max,
							xref: 'x',
							yref: 'y',
							text: '▲ Highest',
							showarrow: true,
							arrowhead: 0,
							arrowsize: 0.5,
							arrowwidth: 1,
							arrowcolor: isDark ? '#22c55e' : '#16a34a',
							ax: 30,
							ay: -25,
							font: {
								size: 9,
								color: isDark ? '#22c55e' : '#16a34a'
							},
							bgcolor: isDark ? '#1f2937' : '#ffffff',
							bordercolor: isDark ? '#22c55e' : '#16a34a',
							borderwidth: 1,
							borderpad: 3
						});
					}

					// Add reference line for average
					if (yValues.length > 2) {
						(layoutDefaults as Record<string, unknown>).shapes = [
							{
								type: 'line',
								x0: 0,
								x1: 1,
								xref: 'paper',
								y0: mean,
								y1: mean,
								yref: 'y',
								line: {
									color: isDark ? '#f59e0b' : '#d97706',
									width: 1,
									dash: 'dot'
								}
							}
						];
						// Average label
						annotations.push({
							x: 1,
							y: mean,
							xref: 'paper',
							yref: 'y',
							text: `Avg: ${formatNumber(mean)}`,
							showarrow: false,
							xanchor: 'left',
							font: {
								size: 9,
								color: isDark ? '#f59e0b' : '#d97706'
							}
						});
					}
				} else if (trace.type === 'pie' && traceData.values && traceData.labels) {
					// Enhanced pie chart hover
					trace.hovertemplate =
						'<b>%{label}</b><br>' +
						'Value: <b>%{value:,.0f}</b><br>' +
						'Share: <b>%{percent}</b><br>' +
						'<extra></extra>';
					trace.textinfo = 'percent';
					trace.textfont = { size: 10 };
				} else if ((trace.type === 'scatter' || trace.type === 'line') && traceData.x && traceData.y) {
					// Line/scatter hover
					trace.hovertemplate =
						'<b>%{x}</b><br>' +
						'Value: <b>%{y:,.2f}</b><br>' +
						'<extra></extra>';
				}
			}

			const mergedLayout = {
				...layoutDefaults,
				...inputLayout,
				width,
				height,
				title: title || undefined,
				annotations: [...annotations, ...((inputLayout as Record<string, unknown>).annotations || []) as Record<string, unknown>[]]
			};

			Plotly.react(
				chartContainer,
				chartData,
				mergedLayout as unknown as import('plotly.js-basic-dist').Layout,
				{
					displayModeBar: true,
					displaylogo: false,
					responsive: true,
					scrollZoom: false,
					modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d']
				} as import('plotly.js-basic-dist').Config
			);
		}
	});

	// Cleanup on unmount
	onDestroy(() => {
		if (browser && Plotly && chartContainer) {
			Plotly.purge(chartContainer);
		}
	});

	function toggleMode() {
		const newMode = viewMode === 'detail' ? 'simple' : 'detail';
		viewMode = newMode;
		onModeChange?.(newMode);
	}

	function formatNumber(n: number | undefined | null): string {
		if (n === undefined || n === null || isNaN(n)) return '—';
		if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
		if (Math.abs(n) >= 1_000) return (n / 1_000).toFixed(1) + 'K';
		return n.toFixed(n % 1 === 0 ? 0 : 1);
	}
</script>

<div class="chart-renderer">
	{#if !figureJson}
		<div class="flex items-center justify-center h-32 text-neutral-400 dark:text-neutral-500 text-sm">
			No chart data available
		</div>
	{:else}
		<!-- Controls -->
		<div class="flex items-center justify-between mb-2">
			{#if title}
				<h4 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 truncate">{title}</h4>
			{:else}
				<span></span>
			{/if}
			<div class="flex items-center gap-1">
				<button
					type="button"
					onclick={toggleMode}
					class="p-1.5 rounded text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
					title={viewMode === 'detail' ? 'Switch to simple view' : 'Switch to detail view'}
				>
					{#if viewMode === 'detail'}
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
						</svg>
					{:else}
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
						</svg>
					{/if}
				</button>
				{#if onExpand}
					<button
						type="button"
						onclick={onExpand}
						class="p-1.5 rounded text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
						title="Expand chart"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
						</svg>
					</button>
				{/if}
			</div>
		</div>

		<!-- Chart or Stats View -->
		{#if viewMode === 'detail'}
			<div
				bind:this={chartContainer}
				class="w-full rounded-lg bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700"
				style="height: {height}px;"
			></div>

			<!-- Insights Panel (below chart in detail mode) -->
			{#if insights.length > 0}
				<div class="mt-2 flex flex-wrap gap-2">
					{#each insights as insight, i (i)}
						<div
							class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
								{insight.type === 'highlight'
									? 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300'
									: insight.type === 'warning'
										? 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300'
										: 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300'}"
							title={insight.detail}
						>
							{#if insight.type === 'highlight'}
								<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
									<path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
								</svg>
							{:else if insight.type === 'warning'}
								<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
								</svg>
							{:else}
								<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
								</svg>
							{/if}
							<span>{insight.text}</span>
							{#if insight.detail}
								<span class="opacity-70">· {insight.detail}</span>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		{:else}
			<!-- Simple view with sparkline and stats -->
			<div class="p-4 rounded-lg bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-4">
					<!-- Sparkline (if numeric data) -->
					{#if sparklinePath}
						<svg class="w-[120px] h-[40px] flex-shrink-0" viewBox="0 0 120 40" fill="none">
							<path d={sparklinePath} stroke="currentColor" class="text-brand-500" stroke-width="2" fill="none" />
						</svg>
					{/if}

					<!-- Stats -->
					{#if stats}
						<div class="flex-1 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
							{#if stats.type === 'numeric'}
								<div>
									<div class="text-xs text-neutral-500 dark:text-neutral-400">Latest</div>
									<div class="font-semibold text-neutral-900 dark:text-white flex items-center gap-1">
										{formatNumber(stats.latest)}
										{#if stats.trend === 'up'}
											<svg class="w-3 h-3 text-success-500" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
											</svg>
										{:else if stats.trend === 'down'}
											<svg class="w-3 h-3 text-error-500" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clip-rule="evenodd" />
											</svg>
										{/if}
									</div>
								</div>
								<div>
									<div class="text-xs text-neutral-500 dark:text-neutral-400">Average</div>
									<div class="font-semibold text-neutral-900 dark:text-white">{formatNumber(stats.mean)}</div>
								</div>
								<div>
									<div class="text-xs text-neutral-500 dark:text-neutral-400">Min</div>
									<div class="font-semibold text-neutral-900 dark:text-white">{formatNumber(stats.min)}</div>
								</div>
								<div>
									<div class="text-xs text-neutral-500 dark:text-neutral-400">Max</div>
									<div class="font-semibold text-neutral-900 dark:text-white">{formatNumber(stats.max)}</div>
								</div>
							{:else if stats.type === 'categorical'}
								<div>
									<div class="text-xs text-neutral-500 dark:text-neutral-400">Total</div>
									<div class="font-semibold text-neutral-900 dark:text-white">{formatNumber(stats.total)}</div>
								</div>
								<div>
									<div class="text-xs text-neutral-500 dark:text-neutral-400">Categories</div>
									<div class="font-semibold text-neutral-900 dark:text-white">{stats.count}</div>
								</div>
								<div class="col-span-2">
									<div class="text-xs text-neutral-500 dark:text-neutral-400">Top</div>
									<div class="font-semibold text-neutral-900 dark:text-white truncate">
										{stats.topCategory} ({stats.topPercent}%)
									</div>
								</div>
							{/if}
						</div>
					{:else}
						<div class="text-sm text-neutral-500 dark:text-neutral-400">
							Click to view interactive chart
						</div>
					{/if}
				</div>
			</div>
		{/if}
	{/if}
</div>
