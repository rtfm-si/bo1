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
	$effect(() => {
		if (browser && plotlyLoaded && Plotly && chartContainer && viewMode === 'detail' && figureJson?.data) {
			const isDark = document.documentElement.classList.contains('dark');
			const chartData = figureJson.data as import('plotly.js-basic-dist').Data[];

			const layoutDefaults = {
				paper_bgcolor: 'transparent',
				plot_bgcolor: 'transparent',
				margin: { l: 50, r: 20, t: title ? 40 : 20, b: 50, pad: 4 },
				font: {
					family: 'Inter, system-ui, sans-serif',
					size: 12,
					color: isDark ? '#e5e7eb' : '#374151'
				},
				autosize: true,
				showlegend: chartData.length > 1,
				xaxis: {
					gridcolor: isDark ? '#374151' : '#e5e7eb',
					zerolinecolor: isDark ? '#4b5563' : '#d1d5db'
				},
				yaxis: {
					gridcolor: isDark ? '#374151' : '#e5e7eb',
					zerolinecolor: isDark ? '#4b5563' : '#d1d5db'
				}
			};

			const mergedLayout = { ...layoutDefaults, ...figureJson.layout, width, height, title: title || undefined };

			Plotly.react(chartContainer, chartData, mergedLayout, {
				displayModeBar: true,
				displaylogo: false,
				responsive: true,
				scrollZoom: false
			});
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

	function formatNumber(n: number): string {
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
