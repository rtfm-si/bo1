<script lang="ts">
	/**
	 * Plotly chart wrapper for analytics chat.
	 * Dynamically imports Plotly to avoid SSR issues.
	 */
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';

	interface Props {
		figureJson: { data?: unknown[]; layout?: Record<string, unknown> } | null;
		height?: number;
	}

	let { figureJson, height = 300 }: Props = $props();

	let chartEl: HTMLDivElement = $state(null!);
	let Plotly: typeof import('plotly.js-basic-dist') | null = null;

	onMount(async () => {
		if (!browser || !figureJson) return;
		try {
			Plotly = await import('plotly.js-basic-dist');
			renderChart();
		} catch (e) {
			console.warn('Failed to load Plotly:', e);
		}
	});

	function renderChart() {
		if (!Plotly || !chartEl || !figureJson?.data) return;

		const data = JSON.parse(JSON.stringify(figureJson.data));
		const layout = {
			...JSON.parse(JSON.stringify(figureJson.layout || {})),
			height,
			autosize: true,
		};

		// Dark mode adaptation
		if (document.documentElement.classList.contains('dark')) {
			layout.font = { ...layout.font, color: '#D1D5DB' };
			if (layout.xaxis) {
				layout.xaxis.linecolor = '#374151';
				layout.xaxis.tickfont = { ...layout.xaxis.tickfont, color: '#9CA3AF' };
			}
			if (layout.yaxis) {
				layout.yaxis.gridcolor = '#1F2937';
				layout.yaxis.tickfont = { ...layout.yaxis.tickfont, color: '#9CA3AF' };
			}
		}

		Plotly.newPlot(chartEl, data, layout, {
			responsive: true,
			displayModeBar: false,
		});
	}

	// Re-render when figureJson changes
	$effect(() => {
		if (figureJson && Plotly && chartEl) {
			renderChart();
		}
	});

	onDestroy(() => {
		if (browser && Plotly && chartEl) {
			try {
				Plotly.purge(chartEl);
			} catch {
				// ignore
			}
		}
	});
</script>

{#if figureJson}
	<div
		bind:this={chartEl}
		class="w-full rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-2"
		style="min-height: {height}px"
	></div>
{/if}
