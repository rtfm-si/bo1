<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import type { DailyActionStat } from '$lib/api/types';

	interface Props {
		data: DailyActionStat[];
	}

	let { data }: Props = $props();

	// Activity types for filtering
	type ActivityType = 'sessions_run' | 'sessions_completed' | 'created_count' | 'completed_count';

	// Activity type colours - using design system tokens
	const ACTIVITY_COLORS: Record<ActivityType, { light: string; dark: string; label: string }> = {
		sessions_run: { light: 'bg-brand-500', dark: 'dark:bg-brand-400', label: 'Meetings run' },
		sessions_completed: { light: 'bg-success-500', dark: 'dark:bg-success-400', label: 'Meetings completed' },
		created_count: { light: 'bg-warning-500', dark: 'dark:bg-warning-400', label: 'Actions created' },
		completed_count: { light: 'bg-info-500', dark: 'dark:bg-info-400', label: 'Actions completed' }
	};

	// Enabled activity types (all enabled by default) - SvelteSet for reactive mutations
	let enabledTypes = new SvelteSet<ActivityType>([
		'sessions_run', 'sessions_completed', 'created_count', 'completed_count'
	]);

	// Toggle an activity type
	function toggleType(type: ActivityType) {
		if (enabledTypes.has(type)) {
			// Don't allow disabling all types
			if (enabledTypes.size > 1) {
				enabledTypes.delete(type);
			}
		} else {
			enabledTypes.add(type);
		}
	}

	// Rolling 12-month view: 6 months back + 6 months forward = ~365 days
	const dateRange = $derived.by(() => {
		const today = new Date();
		today.setHours(12, 0, 0, 0); // Noon to avoid DST issues

		// 6 months back
		const start = new Date(today);
		start.setMonth(start.getMonth() - 6);
		start.setHours(0, 0, 0, 0);

		// 6 months forward
		const end = new Date(today);
		end.setMonth(end.getMonth() + 6);
		end.setHours(23, 59, 59, 999);

		const days = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
		return { start, end, today, days };
	});

	// Filter data by actual date range
	const filteredData = $derived.by(() => {
		const { start, end } = dateRange;
		return data.filter((d) => {
			const date = new Date(d.date);
			return date >= start && date <= end;
		});
	});

	// Calculate number of weeks to display
	const weekCount = $derived.by(() => {
		return Math.ceil(dateRange.days / 7) + 1;
	});

	// Build complete grid with all dates in range
	const gridData = $derived.by(() => {
		const { start, end, days: rangeDays } = dateRange;

		// Create a map of date string -> stat for quick lookup
		const statMap = new Map<string, DailyActionStat>();
		filteredData.forEach((stat) => {
			statMap.set(stat.date, stat);
		});

		// Find the Sunday on or before the start date (week boundary)
		const rangeStart = new Date(start);
		const startDayOfWeek = rangeStart.getDay();
		rangeStart.setDate(rangeStart.getDate() - startDayOfWeek);

		// Build weeks array
		const weeks: { date: Date; stat: DailyActionStat | null }[][] = [];
		const currentDate = new Date(rangeStart);

		for (let w = 0; w < weekCount; w++) {
			const week: { date: Date; stat: DailyActionStat | null }[] = [];
			for (let d = 0; d < 7; d++) {
				const dateStr = currentDate.toISOString().split('T')[0];
				const isInRange = currentDate >= start && currentDate <= end;
				week.push({
					date: new Date(currentDate),
					stat: isInRange ? (statMap.get(dateStr) || null) : null
				});
				currentDate.setDate(currentDate.getDate() + 1);
			}
			weeks.push(week);
		}

		return weeks;
	});

	// Calculate month labels with positions dynamically
	const monthLabelsWithPositions = $derived.by(() => {
		const labels: { month: string; weekIdx: number }[] = [];
		let lastMonth = -1;

		gridData.forEach((week, weekIdx) => {
			// Check first day of week that's in range
			const firstValidDay = week.find((d) => d.stat !== null || d.date >= dateRange.start);
			if (firstValidDay) {
				const month = firstValidDay.date.getMonth();
				if (month !== lastMonth) {
					labels.push({
						month: firstValidDay.date.toLocaleDateString('en-US', { month: 'short' }),
						weekIdx
					});
					lastMonth = month;
				}
			}
		});

		return labels;
	});

	// Get total for a stat respecting enabled types filter
	function getFilteredTotal(stat: DailyActionStat | null): number {
		if (!stat) return 0;
		let total = 0;
		if (enabledTypes.has('sessions_run')) total += stat.sessions_run;
		if (enabledTypes.has('sessions_completed')) total += stat.sessions_completed;
		if (enabledTypes.has('created_count')) total += stat.created_count;
		if (enabledTypes.has('completed_count')) total += stat.completed_count;
		return total;
	}

	// Calculate max activity for color scaling (respecting enabled types)
	const maxActivity = $derived.by(() => {
		return Math.max(...filteredData.map((d) => getFilteredTotal(d)), 1);
	});

	// Get color intensity (0-1)
	function getIntensity(stat: DailyActionStat | null): number {
		if (!stat) return 0;
		return getFilteredTotal(stat) / maxActivity;
	}

	// Get dominant activity type for a stat
	function getDominantType(stat: DailyActionStat | null): ActivityType | null {
		if (!stat) return null;

		const types: { type: ActivityType; count: number }[] = [
			{ type: 'sessions_run', count: enabledTypes.has('sessions_run') ? stat.sessions_run : 0 },
			{ type: 'sessions_completed', count: enabledTypes.has('sessions_completed') ? stat.sessions_completed : 0 },
			{ type: 'created_count', count: enabledTypes.has('created_count') ? stat.created_count : 0 },
			{ type: 'completed_count', count: enabledTypes.has('completed_count') ? stat.completed_count : 0 }
		];

		const dominant = types.reduce((max, curr) => (curr.count > max.count ? curr : max), types[0]);
		return dominant.count > 0 ? dominant.type : null;
	}

	// Get background color based on dominant activity type and intensity
	function getColor(stat: DailyActionStat | null, isFuture: boolean): string {
		const intensity = getIntensity(stat);

		// Future dates with no data - show subtle pattern
		if (isFuture && intensity === 0) {
			return 'bg-neutral-50 dark:bg-neutral-900 border border-dashed border-neutral-200 dark:border-neutral-700';
		}

		if (intensity === 0) {
			return 'bg-neutral-100 dark:bg-neutral-800';
		}

		const dominant = getDominantType(stat);
		if (!dominant) return 'bg-neutral-100 dark:bg-neutral-800';

		// Apply intensity via opacity classes
		const color = ACTIVITY_COLORS[dominant];
		if (intensity <= 0.25) {
			return `${color.light}/40 ${color.dark}/40`;
		}
		if (intensity <= 0.5) {
			return `${color.light}/60 ${color.dark}/60`;
		}
		if (intensity <= 0.75) {
			return `${color.light}/80 ${color.dark}/80`;
		}
		return `${color.light} ${color.dark}`;
	}

	// Format tooltip text
	function formatTooltip(cell: { date: Date; stat: DailyActionStat | null }, isFuture: boolean): string {
		const dateStr = cell.date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

		if (isFuture) {
			return `${dateStr}\n(Future date)`;
		}

		if (!cell.stat) {
			return `${dateStr}\nNo activity`;
		}

		const lines = [dateStr];

		// Show all activity types, mark filtered ones
		const showItem = (type: ActivityType, count: number, label: string) => {
			const isFiltered = !enabledTypes.has(type);
			if (count > 0) {
				lines.push(`${label}: ${count}${isFiltered ? ' (hidden)' : ''}`);
			}
		};

		showItem('sessions_run', cell.stat.sessions_run, 'Meetings run');
		showItem('sessions_completed', cell.stat.sessions_completed, 'Meetings completed');
		showItem('created_count', cell.stat.created_count, 'Actions created');
		showItem('completed_count', cell.stat.completed_count, 'Actions completed');

		if (lines.length === 1) lines.push('No activity');

		return lines.join('\n');
	}

	// Check if a cell is within the selected date range
	function isInRange(cell: { date: Date; stat: DailyActionStat | null }): boolean {
		return cell.date >= dateRange.start && cell.date <= dateRange.end;
	}

	// Check if a date is in the future
	function isFutureDate(date: Date): boolean {
		return date > dateRange.today;
	}

	// Day labels
	const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

	// Activity types as array for iteration
	const activityTypes: ActivityType[] = ['sessions_run', 'sessions_completed', 'created_count', 'completed_count'];
</script>

<div class="w-full space-y-4">
	<!-- Header with title -->
	<div class="flex items-center justify-between">
		<h3 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Activity Heatmap</h3>
		<span class="text-xs text-neutral-500 dark:text-neutral-400">Rolling 12 months</span>
	</div>

	<!-- Activity type toggles -->
	<div class="flex flex-wrap gap-2">
		{#each activityTypes as type (type)}
			{@const isEnabled = enabledTypes.has(type)}
			{@const colors = ACTIVITY_COLORS[type]}
			<button
				onclick={() => toggleType(type)}
				class="flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded-full transition-all
					{isEnabled
					? `${colors.light} ${colors.dark} text-white`
					: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400'}"
				title={isEnabled ? `Click to hide ${colors.label}` : `Click to show ${colors.label}`}
			>
				<span class="w-2 h-2 rounded-full {isEnabled ? 'bg-white/80' : 'bg-neutral-400 dark:bg-neutral-600'}"></span>
				{colors.label}
			</button>
		{/each}
	</div>

	<!-- Heatmap grid -->
	<div class="overflow-x-auto">
		{#if data.length === 0}
			<div class="flex items-center justify-center h-32 text-neutral-500 dark:text-neutral-400 text-sm">
				No activity data available
			</div>
		{:else}
			<div class="inline-block min-w-full">
				<!-- Month labels -->
				<div class="flex mb-2 pl-8 relative h-4">
					{#each monthLabelsWithPositions as label (label.weekIdx)}
						<div
							style="position: absolute; left: {label.weekIdx * 18}px"
							class="text-xs font-medium text-neutral-600 dark:text-neutral-400"
						>
							{label.month}
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
								{#each week as cell, dayIdx (dayIdx)}
									{@const inRange = isInRange(cell)}
									{@const isFuture = isFutureDate(cell.date)}
									{@const intensity = inRange ? getIntensity(cell.stat) : 0}
									<div
										class:opacity-20={!inRange}
										class="w-3.5 h-3.5 rounded-sm cursor-pointer transition-opacity hover:opacity-80 {getColor(cell.stat, isFuture)}"
										title={inRange ? formatTooltip(cell, isFuture) : ''}
									></div>
								{/each}
							</div>
						{/each}
					</div>
				</div>
			</div>

			<!-- Legend: activity type colours (clickable) -->
			<div class="flex flex-wrap items-center gap-4 mt-4 text-xs text-neutral-600 dark:text-neutral-400">
				<span class="font-medium">Legend:</span>
				{#each activityTypes as type (type)}
					{@const isEnabled = enabledTypes.has(type)}
					{@const colors = ACTIVITY_COLORS[type]}
					<button
						onclick={() => toggleType(type)}
						class="flex items-center gap-1.5 transition-opacity {isEnabled ? '' : 'opacity-40'}"
						title={isEnabled ? `Click to hide ${colors.label}` : `Click to show ${colors.label}`}
					>
						<div class="w-3 h-3 rounded-sm {colors.light} {colors.dark}"></div>
						<span>{colors.label}</span>
					</button>
				{/each}
				<div class="flex items-center gap-1.5 ml-2 border-l border-neutral-200 dark:border-neutral-700 pl-4">
					<div class="w-3 h-3 rounded-sm border border-dashed border-neutral-300 dark:border-neutral-600 bg-neutral-50 dark:bg-neutral-900"></div>
					<span>Future</span>
				</div>
			</div>
		{/if}
	</div>
</div>
