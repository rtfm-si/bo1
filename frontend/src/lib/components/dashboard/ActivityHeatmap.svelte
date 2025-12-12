<script lang="ts">
	import type { DailyActionStat } from '$lib/api/types';

	interface Props {
		data: DailyActionStat[];
		days?: number;
	}

	let { data, days = 365 }: Props = $props();

	// Date range state
	let selectedRange = $state<'30' | '90' | '365'>('365');

	// Filter data by selected range
	const filteredData = $derived.by(() => {
		const rangeInt = parseInt(selectedRange);
		return data.slice(0, rangeInt);
	});

	// Prepare week grid (52 cols x 7 rows for annual view)
	const gridData = $derived.by(() => {
		const sorted = filteredData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

		// Map to 52-week grid
		const weeks: (DailyActionStat | null)[][] = Array(52)
			.fill(null)
			.map(() => Array(7).fill(null));

		sorted.forEach((stat) => {
			const date = new Date(stat.date);
			const year = date.getFullYear();
			const startOfYear = new Date(year, 0, 1);

			// Find week number (ISO 8601)
			const d = new Date(date);
			d.setHours(0, 0, 0, 0);
			d.setDate(d.getDate() + 4 - (d.getDay() || 7));
			const yearStart = new Date(d.getFullYear(), 0, 1);
			const weekNum = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);

			const dayOfWeek = date.getDay();
			if (weekNum > 0 && weekNum <= 52) {
				weeks[weekNum - 1][dayOfWeek] = stat;
			}
		});

		return weeks;
	});

	// Calculate max activity for color scaling
	const maxActivity = $derived.by(() => {
		return Math.max(
			...filteredData.map((d) => d.completed_count + d.created_count + d.sessions_run + d.sessions_completed),
			1
		);
	});

	// Get color intensity (0-1)
	function getIntensity(stat: DailyActionStat | null): number {
		if (!stat) return 0;
		const total = stat.completed_count + stat.created_count + stat.sessions_run + stat.sessions_completed;
		return total / maxActivity;
	}

	// Get background color based on intensity
	function getColor(intensity: number): string {
		if (intensity === 0) {
			return 'fill-neutral-100 dark:fill-neutral-800';
		}
		if (intensity <= 0.25) {
			return 'fill-brand-200 dark:fill-brand-900';
		}
		if (intensity <= 0.5) {
			return 'fill-brand-400 dark:fill-brand-700';
		}
		if (intensity <= 0.75) {
			return 'fill-brand-500 dark:fill-brand-600';
		}
		return 'fill-brand-600 dark:fill-brand-500';
	}

	// Format tooltip text
	function formatTooltip(stat: DailyActionStat): string {
		const date = new Date(stat.date);
		const dateStr = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

		const lines = [dateStr];
		if (stat.sessions_run > 0) lines.push(`Meetings run: ${stat.sessions_run}`);
		if (stat.sessions_completed > 0) lines.push(`Meetings completed: ${stat.sessions_completed}`);
		if (stat.created_count > 0) lines.push(`Actions created: ${stat.created_count}`);
		if (stat.completed_count > 0) lines.push(`Actions completed: ${stat.completed_count}`);

		if (lines.length === 1) lines.push('No activity');

		return lines.join('\n');
	}

	// Day labels
	const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

	// Month labels (approximate positions for visual reference)
	const monthLabels = [
		'Jan',
		'Feb',
		'Mar',
		'Apr',
		'May',
		'Jun',
		'Jul',
		'Aug',
		'Sep',
		'Oct',
		'Nov',
		'Dec'
	];
	const monthPositions = [0, 4, 9, 13, 18, 22, 27, 31, 35, 40, 44, 49]; // Approximate week positions
</script>

<div class="w-full space-y-4">
	<!-- Range selector -->
	<div class="flex items-center justify-between">
		<h3 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Activity Heatmap</h3>
		<div class="flex gap-2">
			{#each [{ label: '1M', value: '30' }, { label: '3M', value: '90' }, { label: '1Y', value: '365' }] as option (option.value)}
				<button
					onclick={() => {
						selectedRange = option.value as '30' | '90' | '365';
					}}
					class:bg-brand-500={selectedRange === option.value}
					class:text-white={selectedRange === option.value}
					class:bg-neutral-200={selectedRange !== option.value}
					class:text-neutral-700={selectedRange !== option.value}
					class:dark:bg-neutral-700={selectedRange !== option.value}
					class:dark:text-neutral-300={selectedRange !== option.value}
					class="px-2 py-1 text-xs font-medium rounded transition-colors"
				>
					{option.label}
				</button>
			{/each}
		</div>
	</div>

	<!-- Heatmap grid -->
	<div class="overflow-x-auto">
		{#if filteredData.length === 0}
			<div class="flex items-center justify-center h-32 text-neutral-500 dark:text-neutral-400 text-sm">
				No activity data available
			</div>
		{:else}
			<div class="inline-block min-w-full">
				<!-- Month labels -->
				<div class="flex mb-2 pl-8">
					{#each monthLabels as month, idx (idx)}
						<div
							style="margin-left: {monthPositions[idx] * 14 + 4}px"
							class="text-xs font-medium text-neutral-600 dark:text-neutral-400 w-8"
						>
							{month}
						</div>
					{/each}
				</div>

				<!-- Day labels and heatmap -->
				<div class="flex gap-1">
					<!-- Day labels -->
					<div class="flex flex-col gap-1">
						{#each dayLabels as day (day)}
							<div class="w-8 h-3.5 text-xs font-medium text-neutral-600 dark:text-neutral-400 flex items-center">
								{day}
							</div>
						{/each}
					</div>

					<!-- Heatmap cells -->
					<div class="flex gap-1">
						{#each gridData as week, weekIdx (weekIdx)}
							<div class="flex flex-col gap-1">
								{#each week as stat, dayIdx (dayIdx)}
									{@const intensity = getIntensity(stat)}
									<div
										class:ring-2={stat && intensity > 0}
										class:ring-brand-400={stat && intensity > 0}
										class="w-3.5 h-3.5 rounded-sm cursor-pointer transition-opacity hover:opacity-80 {getColor(intensity)}"
										title={stat ? formatTooltip(stat) : 'No data'}
									></div>
								{/each}
							</div>
						{/each}
					</div>
				</div>
			</div>

			<!-- Legend -->
			<div class="flex items-center justify-start gap-3 mt-4 text-xs text-neutral-600 dark:text-neutral-400">
				<span class="font-medium">Less</span>
				<div class="w-3 h-3 rounded-sm bg-neutral-100 dark:bg-neutral-800"></div>
				<div class="w-3 h-3 rounded-sm bg-brand-200 dark:bg-brand-900"></div>
				<div class="w-3 h-3 rounded-sm bg-brand-400 dark:bg-brand-700"></div>
				<div class="w-3 h-3 rounded-sm bg-brand-500 dark:bg-brand-600"></div>
				<div class="w-3 h-3 rounded-sm bg-brand-600 dark:bg-brand-500"></div>
				<span class="font-medium">More</span>
			</div>
		{/if}
	</div>
</div>
