<script lang="ts">
	/**
	 * BenchmarkHistory - Shows sparkline/list of historical benchmark values
	 *
	 * Displays up to 6 monthly historical values as:
	 * - Sparkline for 3+ data points
	 * - Simple list for 1-2 data points
	 */
	import type { BenchmarkHistoryEntry } from '$lib/api/types';

	import { formatDate } from '$lib/utils/time-formatting';
	interface Props {
		history: BenchmarkHistoryEntry[];
		unit?: string;
	}

	let { history = [], unit = '' }: Props = $props();

	// Format date as "Jan 15" or "Jan '25"

	// Calculate sparkline points
	function getSparklinePoints(): string {
		if (history.length < 2) return '';

		// Reverse to show oldest first (left to right)
		const reversed = [...history].reverse();
		const values = reversed.map((h) => h.value);
		const min = Math.min(...values);
		const max = Math.max(...values);
		const range = max - min || 1;

		const width = 100;
		const height = 24;
		const padding = 2;

		const points = reversed.map((h, i) => {
			const x = padding + (i * (width - 2 * padding)) / (reversed.length - 1);
			const y = padding + ((max - h.value) / range) * (height - 2 * padding);
			return `${x},${y}`;
		});

		return points.join(' ');
	}

	// Get trend indicator
	function getTrend(): 'up' | 'down' | 'stable' | null {
		if (history.length < 2) return null;
		const newest = history[0].value;
		const oldest = history[history.length - 1].value;
		const diff = newest - oldest;
		const pctChange = (diff / oldest) * 100;

		if (pctChange > 5) return 'up';
		if (pctChange < -5) return 'down';
		return 'stable';
	}

	const sparklinePoints = $derived(getSparklinePoints());
	const trend = $derived(getTrend());
</script>

{#if history.length === 0}
	<div class="text-xs text-neutral-400 dark:text-neutral-500 italic">No history yet</div>
{:else if history.length === 1}
	<!-- Single entry - just show as text -->
	<div class="text-xs text-neutral-500 dark:text-neutral-400">
		<span class="font-medium">{history[0].value}{unit === '%' ? '%' : ''}</span>
		<span class="text-neutral-400 dark:text-neutral-500 ml-1">({formatDate(history[0].date)})</span>
	</div>
{:else if history.length === 2}
	<!-- Two entries - show as compact list -->
	<div class="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
		{#each history as entry, i}
			<span>
				<span class="font-medium">{entry.value}{unit === '%' ? '%' : ''}</span>
				<span class="text-neutral-400 dark:text-neutral-500">({formatDate(entry.date)})</span>
			</span>
			{#if i < history.length - 1}
				<span class="text-neutral-300 dark:text-neutral-600">→</span>
			{/if}
		{/each}
	</div>
{:else}
	<!-- 3+ entries - show sparkline -->
	<div class="flex items-center gap-2">
		<svg viewBox="0 0 100 24" class="w-20 h-6 flex-shrink-0">
			<!-- Sparkline -->
			<polyline
				points={sparklinePoints}
				fill="none"
				stroke={trend === 'up' ? '#10b981' : trend === 'down' ? '#ef4444' : '#6b7280'}
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			/>
			<!-- End dot -->
			{#if history.length > 0}
				{@const lastPoint = sparklinePoints.split(' ').pop()?.split(',')}
				{#if lastPoint}
					<circle
						cx={lastPoint[0]}
						cy={lastPoint[1]}
						r="3"
						fill={trend === 'up' ? '#10b981' : trend === 'down' ? '#ef4444' : '#6b7280'}
					/>
				{/if}
			{/if}
		</svg>

		<!-- Trend indicator -->
		{#if trend === 'up'}
			<span class="text-success-600 dark:text-success-400 text-xs font-medium flex items-center gap-0.5">
				<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
				</svg>
				Up
			</span>
		{:else if trend === 'down'}
			<span class="text-error-600 dark:text-error-400 text-xs font-medium flex items-center gap-0.5">
				<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
				Down
			</span>
		{:else}
			<span class="text-neutral-500 dark:text-neutral-400 text-xs font-medium">Stable</span>
		{/if}

		<!-- Count indicator -->
		<span class="text-xs text-neutral-400 dark:text-neutral-500">
			({history.length} check-ins)
		</span>
	</div>
{/if}
