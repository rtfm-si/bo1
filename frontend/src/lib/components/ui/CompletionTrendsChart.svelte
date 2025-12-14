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

	// Calculate max value for scaling (all 3 metrics)
	const maxValue = $derived(() => {
		const values = chartData().flatMap(d => [d.completed_count, d.sessions_run, d.mentor_sessions]);
		return Math.max(...values, 1); // Minimum 1 to avoid division by zero
	});

	// Chart dimensions (3 bars per day)
	const chartHeight = 120;
	const barWidth = 12;
	const barGap = 2;
	const labelHeight = 24;
	const groupWidth = barWidth * 3 + barGap * 2 + 8; // 3 bars + gaps + spacing
	const chartWidth = $derived(() => chartData().length * groupWidth);

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
				{@const x = i * groupWidth + 4}
				{@const meetingsHeight = scaleY(day.sessions_run)}
				{@const completedHeight = scaleY(day.completed_count)}
				{@const mentorHeight = scaleY(day.mentor_sessions)}

				<!-- Meetings bar (left, neutral) -->
				<rect
					x={x}
					y={chartHeight - labelHeight - meetingsHeight}
					width={barWidth}
					height={Math.max(meetingsHeight, 1)}
					class="fill-neutral-300 dark:fill-neutral-600"
					rx="2"
				>
					<title>Meetings: {day.sessions_run} on {day.date}</title>
				</rect>

				<!-- Completed bar (center, brand) -->
				<rect
					x={x + barWidth + barGap}
					y={chartHeight - labelHeight - completedHeight}
					width={barWidth}
					height={Math.max(completedHeight, 1)}
					class="fill-brand-500 dark:fill-brand-400"
					rx="2"
				>
					<title>Actions completed: {day.completed_count} on {day.date}</title>
				</rect>

				<!-- Mentor bar (right, purple) -->
				<rect
					x={x + (barWidth + barGap) * 2}
					y={chartHeight - labelHeight - mentorHeight}
					width={barWidth}
					height={Math.max(mentorHeight, 1)}
					class="fill-purple-500 dark:fill-purple-400"
					rx="2"
				>
					<title>Mentor sessions: {day.mentor_sessions} on {day.date}</title>
				</rect>

				<!-- Day label -->
				<text
					x={x + barWidth * 1.5 + barGap}
					y={chartHeight - 4}
					text-anchor="middle"
					class="fill-neutral-500 dark:fill-neutral-400 text-[10px]"
				>
					{formatDayLabel(day.date)}
				</text>
			{/each}
		</svg>

		<!-- Legend -->
		<div class="flex items-center justify-center gap-4 mt-2 text-xs text-neutral-600 dark:text-neutral-400">
			<div class="flex items-center gap-1.5">
				<span class="w-3 h-3 rounded-sm bg-neutral-300 dark:bg-neutral-600"></span>
				<span>Meetings</span>
			</div>
			<div class="flex items-center gap-1.5">
				<span class="w-3 h-3 rounded-sm bg-brand-500 dark:bg-brand-400"></span>
				<span>Completed</span>
			</div>
			<div class="flex items-center gap-1.5">
				<span class="w-3 h-3 rounded-sm bg-purple-500 dark:bg-purple-400"></span>
				<span>Mentor</span>
			</div>
		</div>
	{/if}
</div>
