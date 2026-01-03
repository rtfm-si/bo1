<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import type { DailyActionStat } from '$lib/api/types';
	import ShareButton from '$lib/components/ui/ShareButton.svelte';
	import type { ActivityStats } from '$lib/utils/share-content';

	interface Props {
		data: DailyActionStat[];
		/** Working days as ISO weekday numbers (1=Mon, 7=Sun). Default: Mon-Fri */
		workingDays?: number[];
		/** History depth in months (1, 3, or 6). Default: 3 */
		historyMonths?: 1 | 3 | 6;
	}

	let { data, workingDays = [1, 2, 3, 4, 5], historyMonths = 3 }: Props = $props();

	// Convert ISO weekday (1=Mon) to JS weekday (0=Sun) for comparison
	// ISO: 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun
	// JS:  0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
	function isWorkingDay(jsWeekday: number): boolean {
		// Convert JS weekday to ISO weekday
		const isoWeekday = jsWeekday === 0 ? 7 : jsWeekday;
		return workingDays.includes(isoWeekday);
	}

	// Reference to heatmap container for image export
	let heatmapContainer: HTMLElement | null = $state(null);

	// Container width for responsive sizing
	let containerWidth = $state(0);

	// Activity types for filtering
	type ActivityType = 'sessions_run' | 'completed_count' | 'in_progress_count' | 'mentor_sessions' | 'estimated_starts' | 'estimated_completions';

	// Activity type colours - using design system tokens with WCAG AA contrast (4.5:1+)
	// Estimated types use lighter (300) variants for better visibility
	const ACTIVITY_COLORS: Record<ActivityType, { light: string; dark: string; label: string; shortLabel: string; group: 'actual' | 'planned' }> = {
		sessions_run: { light: 'bg-brand-600', dark: 'dark:bg-brand-400', label: 'Meetings', shortLabel: 'Meet', group: 'actual' },
		completed_count: { light: 'bg-success-600', dark: 'dark:bg-success-400', label: 'Actions completed', shortLabel: 'Done', group: 'actual' },
		in_progress_count: { light: 'bg-amber-600', dark: 'dark:bg-amber-400', label: 'Actions started', shortLabel: 'Started', group: 'actual' },
		mentor_sessions: { light: 'bg-purple-600', dark: 'dark:bg-purple-400', label: 'Mentor sessions', shortLabel: 'Mentor', group: 'actual' },
		estimated_starts: { light: 'bg-amber-300', dark: 'dark:bg-amber-500', label: 'Planned starts', shortLabel: 'Plan', group: 'planned' },
		estimated_completions: { light: 'bg-success-300', dark: 'dark:bg-success-500', label: 'Due dates', shortLabel: 'Due', group: 'planned' }
	};

	// Group types for toggle UI
	const actualTypes: ActivityType[] = ['sessions_run', 'completed_count', 'in_progress_count', 'mentor_sessions'];
	const plannedTypes: ActivityType[] = ['estimated_starts', 'estimated_completions'];

	// Enabled activity types (all enabled by default) - SvelteSet for reactive mutations
	let enabledTypes = new SvelteSet<ActivityType>([
		'sessions_run', 'completed_count', 'in_progress_count', 'mentor_sessions', 'estimated_starts', 'estimated_completions'
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

	// Find last date with planned actions (estimated_starts or estimated_completions > 0)
	function getLastPlannedDate(activityData: DailyActionStat[], today: Date): Date {
		let lastPlanned = new Date(today);

		for (const stat of activityData) {
			const statDate = new Date(stat.date);
			// Only consider future dates with planned actions
			if (statDate > today && ((stat.estimated_starts ?? 0) > 0 || (stat.estimated_completions ?? 0) > 0)) {
				if (statDate > lastPlanned) {
					lastPlanned = statDate;
				}
			}
		}

		return lastPlanned;
	}

	// History depth + future limited to planned actions
	const dateRange = $derived.by(() => {
		const today = new Date();
		today.setHours(12, 0, 0, 0); // Noon to avoid DST issues

		// Use historyMonths prop for history depth (default 3)
		const start = new Date(today);
		start.setMonth(start.getMonth() - historyMonths);
		start.setHours(0, 0, 0, 0);

		// Future: last planned action + 7 days buffer, capped at historyMonths forward
		const lastPlanned = getLastPlannedDate(data, today);
		const buffer = new Date(lastPlanned);
		buffer.setDate(buffer.getDate() + 7);

		// Cap at historyMonths from today
		const maxFuture = new Date(today);
		maxFuture.setMonth(maxFuture.getMonth() + historyMonths);

		const end = new Date(Math.min(buffer.getTime(), maxFuture.getTime()));
		end.setHours(23, 59, 59, 999);

		const days = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));

		// Track if we have planned actions for header label
		const hasPlannedActions = lastPlanned > today;

		return { start, end, today, days, hasPlannedActions };
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

	// Dynamic cell size based on container width and week count
	const cellSize = $derived.by(() => {
		if (containerWidth === 0) return { cell: 14, gap: 4 }; // default fallback

		const dayLabelWidth = 32; // ~w-8
		const availableWidth = containerWidth - dayLabelWidth - 16; // padding

		// Calculate max cell size to fill available space
		const maxCellWithGap = availableWidth / weekCount;
		const gap = Math.min(4, Math.max(2, maxCellWithGap * 0.15)); // 15% gap, clamped
		const cell = Math.min(24, Math.max(12, maxCellWithGap - gap)); // clamp 12-24px

		return { cell: Math.floor(cell), gap: Math.floor(gap) };
	});

	// Build complete grid with all dates in range
	const gridData = $derived.by(() => {
		const { start, end, days: rangeDays } = dateRange;

		// Create a map of date string -> stat for quick lookup
		const statMap = new Map<string, DailyActionStat>();
		filteredData.forEach((stat) => {
			statMap.set(stat.date, stat);
		});

		// Find the Monday on or before the start date (week boundary)
		const rangeStart = new Date(start);
		const startDayOfWeek = rangeStart.getDay();
		// Days since last Monday: Sun(0)→6, Mon(1)→0, Tue(2)→1, etc.
		const daysToMonday = (startDayOfWeek + 6) % 7;
		rangeStart.setDate(rangeStart.getDate() - daysToMonday);

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
		if (enabledTypes.has('completed_count')) total += stat.completed_count;
		if (enabledTypes.has('in_progress_count')) total += stat.in_progress_count;
		if (enabledTypes.has('mentor_sessions')) total += stat.mentor_sessions;
		if (enabledTypes.has('estimated_starts')) total += stat.estimated_starts ?? 0;
		if (enabledTypes.has('estimated_completions')) total += stat.estimated_completions ?? 0;
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
			{ type: 'completed_count', count: enabledTypes.has('completed_count') ? stat.completed_count : 0 },
			{ type: 'in_progress_count', count: enabledTypes.has('in_progress_count') ? stat.in_progress_count : 0 },
			{ type: 'mentor_sessions', count: enabledTypes.has('mentor_sessions') ? stat.mentor_sessions : 0 },
			{ type: 'estimated_starts', count: enabledTypes.has('estimated_starts') ? (stat.estimated_starts ?? 0) : 0 },
			{ type: 'estimated_completions', count: enabledTypes.has('estimated_completions') ? (stat.estimated_completions ?? 0) : 0 }
		];

		const dominant = types.reduce((max, curr) => (curr.count > max.count ? curr : max), types[0]);
		return dominant.count > 0 ? dominant.type : null;
	}

	// Get background color based on dominant activity type and intensity
	function getColor(stat: DailyActionStat | null, isFuture: boolean, isNonWorkingDay: boolean): string {
		const intensity = getIntensity(stat);

		// Non-working days: subtle striped pattern, greyed out
		if (isNonWorkingDay) {
			if (intensity === 0) {
				return 'bg-neutral-50 dark:bg-neutral-900 opacity-30';
			}
			// Non-working day with activity - show muted color
			const dominant = getDominantType(stat);
			if (!dominant) return 'bg-neutral-50 dark:bg-neutral-900 opacity-30';
			const color = ACTIVITY_COLORS[dominant];
			return `${color.light}/30 ${color.dark}/30`;
		}

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
	function formatTooltip(cell: { date: Date; stat: DailyActionStat | null }, isFuture: boolean, isNonWorkingDay: boolean): string {
		const dateStr = cell.date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
		const nonWorkingNote = isNonWorkingDay ? ' (non-working day)' : '';

		if (!cell.stat) {
			if (isFuture) {
				return `${dateStr}${nonWorkingNote}\n(Future date - no planned activity)`;
			}
			return `${dateStr}${nonWorkingNote}\nNo activity`;
		}

		const lines = [dateStr + nonWorkingNote];

		// Show all activity types, mark filtered ones
		const showItem = (type: ActivityType, count: number, label: string) => {
			const isFiltered = !enabledTypes.has(type);
			if (count > 0) {
				lines.push(`${label}: ${count}${isFiltered ? ' (hidden)' : ''}`);
			}
		};

		// Past/actual activities
		showItem('sessions_run', cell.stat.sessions_run, 'Meetings');
		showItem('completed_count', cell.stat.completed_count, 'Actions completed');
		showItem('in_progress_count', cell.stat.in_progress_count, 'Actions started');
		showItem('mentor_sessions', cell.stat.mentor_sessions, 'Mentor sessions');

		// Future/estimated activities
		showItem('estimated_starts', cell.stat.estimated_starts ?? 0, 'Planned starts');
		showItem('estimated_completions', cell.stat.estimated_completions ?? 0, 'Due dates');

		if (lines.length === 1) {
			lines.push(isFuture ? 'No planned activity' : 'No activity');
		}

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

	// Day labels (Monday first) - short for mobile
	const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
	const dayLabelsShort = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

	// Activity types as array for iteration - actual types first, then estimates
	const activityTypes: ActivityType[] = ['sessions_run', 'completed_count', 'in_progress_count', 'mentor_sessions', 'estimated_starts', 'estimated_completions'];

	// Calculate 7-day rolling average for sparkline
	const sparklineData = $derived.by(() => {
		const { start, end, today } = dateRange;
		const result: { date: Date; avg: number }[] = [];

		// Get days from start to min(end, today)
		const sparkEnd = today < end ? today : end;
		const current = new Date(start);
		current.setDate(current.getDate() + 6); // Start after first 7 days

		// Create date->total map
		const totalMap = new Map<string, number>();
		filteredData.forEach((stat) => {
			totalMap.set(stat.date, getFilteredTotal(stat));
		});

		while (current <= sparkEnd) {
			let sum = 0;
			for (let i = 0; i < 7; i++) {
				const d = new Date(current);
				d.setDate(d.getDate() - i);
				const dateStr = d.toISOString().split('T')[0];
				sum += totalMap.get(dateStr) ?? 0;
			}
			result.push({ date: new Date(current), avg: sum / 7 });
			current.setDate(current.getDate() + 1);
		}

		return result;
	});

	// Sparkline SVG path
	const sparklinePath = $derived.by(() => {
		if (sparklineData.length < 2) return '';

		const maxVal = Math.max(...sparklineData.map((d) => d.avg), 0.1);
		const width = 100;
		const height = 20;

		const points = sparklineData.map((d, i) => {
			const x = (i / (sparklineData.length - 1)) * width;
			const y = height - (d.avg / maxVal) * (height - 2);
			return `${x},${y}`;
		});

		return `M${points.join(' L')}`;
	});

	// Trend direction
	const trendDirection = $derived.by(() => {
		if (sparklineData.length < 7) return 'neutral';
		const recent = sparklineData.slice(-7);
		const older = sparklineData.slice(-14, -7);
		if (older.length === 0) return 'neutral';

		const recentAvg = recent.reduce((sum, d) => sum + d.avg, 0) / recent.length;
		const olderAvg = older.reduce((sum, d) => sum + d.avg, 0) / older.length;

		if (recentAvg > olderAvg * 1.1) return 'up';
		if (recentAvg < olderAvg * 0.9) return 'down';
		return 'neutral';
	});

	// Show help tooltip
	let showHelp = $state(false);

	// Resize observer for responsive sizing
	let gridContainer: HTMLElement | null = $state(null);
	$effect(() => {
		if (!gridContainer) return;
		const observer = new ResizeObserver((entries) => {
			containerWidth = entries[0].contentRect.width;
		});
		observer.observe(gridContainer);
		return () => observer.disconnect();
	});

	// Calculate activity stats for sharing (only past data within range)
	const activityStats = $derived.by((): ActivityStats => {
		const { start, today } = dateRange;
		const pastData = data.filter((d) => {
			const date = new Date(d.date);
			return date >= start && date <= today;
		});

		const totals = pastData.reduce(
			(acc, stat) => ({
				meetings: acc.meetings + stat.sessions_run,
				actionsCompleted: acc.actionsCompleted + stat.completed_count,
				mentorSessions: acc.mentorSessions + stat.mentor_sessions
			}),
			{ meetings: 0, actionsCompleted: 0, mentorSessions: 0 }
		);

		return {
			...totals,
			period: 'this year'
		};
	});
</script>

<div class="w-full space-y-3">
	<!-- Header with title and share button -->
	<div class="flex items-center justify-between">
		<h3 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Activity Heatmap</h3>
		<div class="flex items-center gap-2">
			<span class="text-xs text-neutral-500 dark:text-neutral-400 hidden sm:inline">
				{dateRange.hasPlannedActions ? `${historyMonths}mo + planned` : `${historyMonths}mo`}
			</span>
			<ShareButton targetElement={heatmapContainer} stats={activityStats} compact={true} />
		</div>
	</div>

	<!-- Sparkline trend summary -->
	{#if sparklineData.length >= 7}
		<div class="flex items-center gap-3 px-3 py-2 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
			<svg viewBox="0 0 100 20" class="w-24 h-5 flex-shrink-0">
				<path
					d={sparklinePath}
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					class="text-brand-500 dark:text-brand-400"
				/>
			</svg>
			<div class="flex items-center gap-1.5 text-xs text-neutral-600 dark:text-neutral-400">
				{#if trendDirection === 'up'}
					<svg class="w-3.5 h-3.5 text-success-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
					</svg>
					<span>Trending up</span>
				{:else if trendDirection === 'down'}
					<svg class="w-3.5 h-3.5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
					</svg>
					<span>Trending down</span>
				{:else}
					<svg class="w-3.5 h-3.5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14" />
					</svg>
					<span>Steady</span>
				{/if}
				<span class="text-neutral-400 dark:text-neutral-500">7-day avg</span>
			</div>
		</div>
	{/if}

	<!-- Grouped activity type toggles -->
	<div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
		<!-- Actual activities group -->
		<div class="flex items-center gap-1">
			<span class="text-neutral-500 dark:text-neutral-400 mr-1 hidden sm:inline">Actual:</span>
			{#each actualTypes as type (type)}
				{@const isEnabled = enabledTypes.has(type)}
				{@const colors = ACTIVITY_COLORS[type]}
				<button
					onclick={() => toggleType(type)}
					class="flex items-center gap-1 px-1.5 py-0.5 rounded transition-all
						{isEnabled
						? `${colors.light} ${colors.dark} text-white`
						: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 dark:text-neutral-500'}"
					title={colors.label}
				>
					<span class="w-1.5 h-1.5 rounded-full {isEnabled ? 'bg-white/80' : 'bg-neutral-300 dark:bg-neutral-600'}"></span>
					<span class="hidden sm:inline">{colors.shortLabel}</span>
				</button>
			{/each}
		</div>

		<span class="hidden sm:inline text-neutral-300 dark:text-neutral-600">|</span>

		<!-- Planned activities group -->
		<div class="flex items-center gap-1">
			<span class="text-neutral-500 dark:text-neutral-400 mr-1 hidden sm:inline">Planned:</span>
			{#each plannedTypes as type (type)}
				{@const isEnabled = enabledTypes.has(type)}
				{@const colors = ACTIVITY_COLORS[type]}
				<button
					onclick={() => toggleType(type)}
					class="flex items-center gap-1 px-1.5 py-0.5 rounded transition-all
						{isEnabled
						? `${colors.light} ${colors.dark} text-neutral-900`
						: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 dark:text-neutral-500'}"
					title={colors.label}
				>
					<span class="w-1.5 h-1.5 rounded-full {isEnabled ? 'bg-neutral-700/60' : 'bg-neutral-300 dark:bg-neutral-600'}"></span>
					<span class="hidden sm:inline">{colors.shortLabel}</span>
				</button>
			{/each}
		</div>

		<!-- Help icon for legend explanation -->
		<div class="relative ml-auto">
			<button
				onclick={() => showHelp = !showHelp}
				class="p-1 rounded-full text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
				title="Legend help"
				aria-label="Show legend help"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
			</button>
			{#if showHelp}
				<div class="absolute right-0 top-full mt-1 z-10 w-56 p-3 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 text-xs">
					<div class="space-y-2">
						<div class="flex items-center gap-2">
							<div class="w-3 h-3 rounded-sm border border-dashed border-neutral-300 dark:border-neutral-600 bg-neutral-50 dark:bg-neutral-900"></div>
							<span class="text-neutral-600 dark:text-neutral-400">Future (no activity)</span>
						</div>
						<div class="flex items-center gap-2">
							<div class="w-3 h-3 rounded-sm bg-neutral-100 dark:bg-neutral-800 opacity-30"></div>
							<span class="text-neutral-600 dark:text-neutral-400">Non-working day</span>
						</div>
						<p class="text-neutral-500 dark:text-neutral-400 pt-1 border-t border-neutral-200 dark:border-neutral-700">
							Click type chips above to show/hide activities
						</p>
					</div>
					<button
						onclick={() => showHelp = false}
						class="absolute top-1 right-1 p-1 text-neutral-400 hover:text-neutral-600"
						aria-label="Close help"
					>
						<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			{/if}
		</div>
	</div>

	<!-- Heatmap grid - responsive sizing -->
	<div class="relative" bind:this={gridContainer}>
		<div bind:this={heatmapContainer}>
			{#if data.length === 0}
				<div class="flex items-center justify-center h-32 text-neutral-500 dark:text-neutral-400 text-sm">
					No activity data available
				</div>
			{:else}
				<div class="w-full">
					<!-- Month labels - dynamic positioning -->
					<div class="relative mb-1.5 h-4" style="margin-left: {32 + cellSize.gap}px">
						{#each monthLabelsWithPositions as label (label.weekIdx)}
							<div
								style="position: absolute; left: {label.weekIdx * (cellSize.cell + cellSize.gap)}px"
								class="text-xs font-medium text-neutral-600 dark:text-neutral-400"
							>
								{label.month}
							</div>
						{/each}
					</div>

					<!-- Day labels and heatmap -->
					<div class="flex" style="gap: {cellSize.gap}px">
						<!-- Day labels -->
						<div class="flex flex-col" style="gap: {cellSize.gap}px">
							{#each dayLabels as day, i (day)}
								<div
									class="w-8 text-xs font-medium text-neutral-600 dark:text-neutral-400 flex items-center"
									style="height: {cellSize.cell}px"
								>
									{day}
								</div>
							{/each}
						</div>

						<!-- Heatmap cells - dynamic sizing -->
						<div class="flex flex-1" style="gap: {cellSize.gap}px">
							{#each gridData as week, weekIdx (weekIdx)}
								<div class="flex flex-col" style="gap: {cellSize.gap}px">
									{#each week as cell, dayIdx (dayIdx)}
										{@const inRange = isInRange(cell)}
										{@const isFuture = isFutureDate(cell.date)}
										{@const isNonWorking = !isWorkingDay(cell.date.getDay())}
										<div
											class:opacity-20={!inRange}
											class="rounded-sm cursor-pointer transition-opacity hover:opacity-80 {getColor(cell.stat, isFuture, isNonWorking)}"
											style="width: {cellSize.cell}px; height: {cellSize.cell}px"
											title={inRange ? formatTooltip(cell, isFuture, isNonWorking) : ''}
										></div>
									{/each}
								</div>
							{/each}
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
