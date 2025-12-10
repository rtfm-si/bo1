<script lang="ts">
	import type { DailyActionStat } from '$lib/api/types';

	interface Props {
		data: DailyActionStat[];
		days?: number;
	}

	let { data, days = 14 }: Props = $props();

	// Take only the last N days and reverse for chronological order
	const chartData = $derived(() => {
		const sliced = data.slice(0, days).reverse();
		return sliced;
	});

	// Calculate max value for scaling
	const maxValue = $derived(() => {
		const values = chartData().flatMap(d => [d.completed_count, d.created_count]);
		return Math.max(...values, 1); // Minimum 1 to avoid division by zero
	});

	// Chart dimensions
	const chartHeight = 120;
	const barWidth = 16;
	const barGap = 4;
	const labelHeight = 24;
	const chartWidth = $derived(() => chartData().length * (barWidth * 2 + barGap * 2 + 8));

	// Scale value to chart height
	function scaleY(value: number): number {
		return (value / maxValue()) * (chartHeight - labelHeight);
	}

	// Format date for label (e.g., "Mon", "Tue")
	function formatDayLabel(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', { weekday: 'short' }).slice(0, 2);
	}
</script>

<div class="w-full overflow-x-auto">
	{#if chartData().length === 0}
		<div class="flex items-center justify-center h-32 text-neutral-500 dark:text-neutral-400 text-sm">
			No activity data yet
		</div>
	{:else}
		<svg
			class="w-full"
			viewBox="0 0 {chartWidth()} {chartHeight}"
			preserveAspectRatio="xMinYMax meet"
			style="min-width: {Math.min(chartWidth(), 400)}px; height: {chartHeight}px;"
		>
			<!-- Bars for each day -->
			{#each chartData() as day, i}
				{@const x = i * (barWidth * 2 + barGap * 2 + 8) + 4}
				{@const completedHeight = scaleY(day.completed_count)}
				{@const createdHeight = scaleY(day.created_count)}

				<!-- Created bar (left, neutral) -->
				<rect
					x={x}
					y={chartHeight - labelHeight - createdHeight}
					width={barWidth}
					height={Math.max(createdHeight, 1)}
					class="fill-neutral-300 dark:fill-neutral-600"
					rx="2"
				>
					<title>Created: {day.created_count} on {day.date}</title>
				</rect>

				<!-- Completed bar (right, brand) -->
				<rect
					x={x + barWidth + barGap}
					y={chartHeight - labelHeight - completedHeight}
					width={barWidth}
					height={Math.max(completedHeight, 1)}
					class="fill-brand-500 dark:fill-brand-400"
					rx="2"
				>
					<title>Completed: {day.completed_count} on {day.date}</title>
				</rect>

				<!-- Day label -->
				<text
					x={x + barWidth + barGap / 2}
					y={chartHeight - 4}
					text-anchor="middle"
					class="fill-neutral-500 dark:fill-neutral-400 text-[10px]"
				>
					{formatDayLabel(day.date)}
				</text>
			{/each}
		</svg>

		<!-- Legend -->
		<div class="flex items-center justify-center gap-6 mt-2 text-xs text-neutral-600 dark:text-neutral-400">
			<div class="flex items-center gap-1.5">
				<span class="w-3 h-3 rounded-sm bg-neutral-300 dark:bg-neutral-600"></span>
				<span>Created</span>
			</div>
			<div class="flex items-center gap-1.5">
				<span class="w-3 h-3 rounded-sm bg-brand-500 dark:bg-brand-400"></span>
				<span>Completed</span>
			</div>
		</div>
	{/if}
</div>
