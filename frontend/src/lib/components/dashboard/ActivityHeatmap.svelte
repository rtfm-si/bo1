<script lang="ts">
	import { goto } from '$app/navigation';
	import type { DailyActionStat } from '$lib/api/types';
	import { apiClient } from '$lib/api/client';
	import ShareButton from '$lib/components/ui/ShareButton.svelte';
	import HeatmapTooltip from '$lib/components/dashboard/HeatmapTooltip.svelte';
	import type { ActivityStats } from '$lib/utils/share-content';

	interface Props {
		data: DailyActionStat[];
		/** Working days as ISO weekday numbers (1=Mon, 7=Sun). Default: Mon-Fri */
		workingDays?: number[];
		/** History depth in months (1, 3, or 6). Default: 3 */
		historyMonths?: 1 | 3 | 6;
	}

	let { data, workingDays = [1, 2, 3, 4, 5], historyMonths = 3 }: Props = $props();

	// Fixed cell dimensions (no dynamic sizing)
	const CELL_PX = 14;
	const GAP_PX = 3;

	function isWorkingDay(jsWeekday: number): boolean {
		const isoWeekday = jsWeekday === 0 ? 7 : jsWeekday;
		return workingDays.includes(isoWeekday);
	}

	// Reference to heatmap container for image export
	let heatmapContainer: HTMLElement | null = $state(null);

	// Scroll container ref for auto-scroll
	let scrollContainer: HTMLElement | null = $state(null);

	// Tooltip state
	let tooltipVisible = $state(false);
	let tooltipX = $state(0);
	let tooltipY = $state(0);
	let tooltipDate = $state('');
	let tooltipStat = $state<DailyActionStat | null>(null);
	let tooltipIsFuture = $state(false);
	let tooltipTitles = $state<{ id: string; type: string; title: string }[] | null>(null);
	let tooltipLoading = $state(false);

	// Title cache
	const titleCache = new Map<string, { id: string; type: string; title: string }[]>();
	let fetchTimeout: ReturnType<typeof setTimeout> | null = null;

	function onCellEnter(
		e: MouseEvent,
		cell: { date: Date; stat: DailyActionStat | null },
		isFuture: boolean
	) {
		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		tooltipX = rect.left + rect.width / 2;
		tooltipY = rect.top;
		const dateStr = cell.date.toISOString().split('T')[0];
		tooltipDate = dateStr;
		tooltipStat = cell.stat;
		tooltipIsFuture = isFuture;
		tooltipVisible = true;

		// Check cache
		if (titleCache.has(dateStr)) {
			tooltipTitles = titleCache.get(dateStr)!;
			tooltipLoading = false;
		} else {
			tooltipTitles = null;
			tooltipLoading = true;
			// Debounced fetch
			if (fetchTimeout) clearTimeout(fetchTimeout);
			fetchTimeout = setTimeout(async () => {
				try {
					const res = await apiClient.getActivitiesByDate(dateStr);
					const items = res.activities.map((a: { id: string; type: string; title: string }) => ({
						id: a.id,
						type: a.type,
						title: a.title
					}));
					titleCache.set(dateStr, items);
					// Only update if still showing same date
					if (tooltipDate === dateStr) {
						tooltipTitles = items;
						tooltipLoading = false;
					}
				} catch {
					if (tooltipDate === dateStr) {
						tooltipLoading = false;
					}
				}
			}, 300);
		}
	}

	function onCellLeave() {
		tooltipVisible = false;
		if (fetchTimeout) {
			clearTimeout(fetchTimeout);
			fetchTimeout = null;
		}
	}

	function onCellClick(cell: { date: Date; stat: DailyActionStat | null }) {
		const dateStr = cell.date.toISOString().split('T')[0];
		goto(`/dashboard/${dateStr}`);
	}

	// Find last date with planned actions
	function getLastPlannedDate(activityData: DailyActionStat[], today: Date): Date {
		let lastPlanned = new Date(today);
		for (const stat of activityData) {
			const statDate = new Date(stat.date);
			if (statDate > today && ((stat.estimated_starts ?? 0) > 0 || (stat.estimated_completions ?? 0) > 0)) {
				if (statDate > lastPlanned) lastPlanned = statDate;
			}
		}
		return lastPlanned;
	}

	// Count helpers
	function getPastCount(stat: DailyActionStat | null): number {
		if (!stat) return 0;
		return stat.sessions_run + stat.completed_count + stat.in_progress_count + stat.mentor_sessions;
	}

	function getFutureCount(stat: DailyActionStat | null): number {
		if (!stat) return 0;
		return (stat.estimated_starts ?? 0) + (stat.estimated_completions ?? 0);
	}

	function getTotal(stat: DailyActionStat | null): number {
		return getPastCount(stat) + getFutureCount(stat);
	}

	// 5-step intensity: 1→30%, 2→50%, 3→70%, 4→85%, 5+=100%
	function getOpacity(count: number): number {
		if (count <= 0) return 0;
		if (count === 1) return 0.3;
		if (count === 2) return 0.5;
		if (count === 3) return 0.7;
		if (count === 4) return 0.85;
		return 1;
	}

	function getColor(stat: DailyActionStat | null, isFuture: boolean, isNonWorkingDay: boolean): string {
		const count = isFuture ? getFutureCount(stat) : getPastCount(stat);

		if (isNonWorkingDay) {
			if (count === 0) return 'bg-neutral-50 dark:bg-neutral-900 opacity-20';
			// Non-working day with activity
			const base = isFuture ? 'bg-accent-500 dark:bg-accent-400' : 'bg-brand-500 dark:bg-brand-400';
			return `${base} opacity-20`;
		}

		if (isFuture && count === 0) {
			return 'bg-neutral-50 dark:bg-neutral-900 border border-dashed border-neutral-200 dark:border-neutral-700';
		}

		if (count === 0) return 'bg-neutral-200 dark:bg-neutral-700';

		const base = isFuture ? 'bg-accent-500 dark:bg-accent-400' : 'bg-brand-500 dark:bg-brand-400';
		const op = getOpacity(count);
		// Map opacity to Tailwind classes
		if (op <= 0.3) return `${base} opacity-30`;
		if (op <= 0.5) return `${base} opacity-50`;
		if (op <= 0.7) return `${base} opacity-70`;
		if (op <= 0.85) return `${base} opacity-85`;
		return base;
	}

	// Date range: history + 2 months future minimum
	const dateRange = $derived.by(() => {
		const today = new Date();
		today.setHours(12, 0, 0, 0);

		const start = new Date(today);
		start.setMonth(start.getMonth() - historyMonths);
		start.setHours(0, 0, 0, 0);

		const lastPlanned = getLastPlannedDate(data, today);
		const buffer = new Date(lastPlanned);
		buffer.setDate(buffer.getDate() + 7);

		const minFuture = new Date(today);
		minFuture.setMonth(minFuture.getMonth() + 2);

		const maxFuture = new Date(today);
		maxFuture.setMonth(maxFuture.getMonth() + historyMonths);

		const end = new Date(Math.min(
			Math.max(minFuture.getTime(), buffer.getTime()),
			maxFuture.getTime()
		));
		end.setHours(23, 59, 59, 999);

		const days = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
		const hasPlannedActions = lastPlanned > today;

		return { start, end, today, days, hasPlannedActions };
	});

	const filteredData = $derived.by(() => {
		const { start, end } = dateRange;
		return data.filter((d) => {
			const date = new Date(d.date);
			return date >= start && date <= end;
		});
	});

	const weekCount = $derived.by(() => Math.ceil(dateRange.days / 7) + 1);

	const gridData = $derived.by(() => {
		const { start, end } = dateRange;
		const statMap = new Map<string, DailyActionStat>();
		filteredData.forEach((stat) => statMap.set(stat.date, stat));

		const rangeStart = new Date(start);
		const startDayOfWeek = rangeStart.getDay();
		const daysToMonday = (startDayOfWeek + 6) % 7;
		rangeStart.setDate(rangeStart.getDate() - daysToMonday);

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

	const monthLabelsWithPositions = $derived.by(() => {
		const labels: { month: string; weekIdx: number }[] = [];
		let lastMonth = -1;
		gridData.forEach((week, weekIdx) => {
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

	function isInRange(cell: { date: Date; stat: DailyActionStat | null }): boolean {
		return cell.date >= dateRange.start && cell.date <= dateRange.end;
	}

	function isFutureDate(date: Date): boolean {
		return date > dateRange.today;
	}

	function isCurrentWeek(week: { date: Date; stat: DailyActionStat | null }[]): boolean {
		return week.some(cell => cell.date.toDateString() === dateRange.today.toDateString());
	}

	const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

	// 7-day rolling average sparkline
	const sparklineData = $derived.by(() => {
		const { start, end, today } = dateRange;
		const result: { date: Date; avg: number }[] = [];
		const sparkEnd = today < end ? today : end;
		const current = new Date(start);
		current.setDate(current.getDate() + 6);

		const totalMap = new Map<string, number>();
		filteredData.forEach((stat) => {
			totalMap.set(stat.date, getTotal(stat));
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

	// Auto-scroll to current week on mount
	$effect(() => {
		if (!scrollContainer) return;
		const currentWeekEl = scrollContainer.querySelector('[data-current-week]');
		if (currentWeekEl) {
			currentWeekEl.scrollIntoView({ inline: 'center', behavior: 'instant' });
		}
	});

	// Activity stats for sharing
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
		return { ...totals, period: 'this year' };
	});
</script>

<div class="w-full space-y-3">
	<!-- Header with share button only -->
	<div class="flex items-center justify-end">
		<ShareButton targetElement={heatmapContainer} stats={activityStats} compact={true} />
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
					<svg class="w-3.5 h-3.5 text-warning-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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

	<!-- Heatmap grid - horizontal scroll with fixed cell size -->
	<div class="relative">
		<div bind:this={heatmapContainer}>
			{#if data.length === 0}
				<div class="flex items-center justify-center h-32 text-neutral-500 dark:text-neutral-400 text-sm">
					No activity data available
				</div>
			{:else}
				<div class="overflow-x-auto scrollbar-thin" bind:this={scrollContainer}>
					<div style="min-width: max-content">
						<!-- Month labels -->
						<div class="relative mb-1.5 h-4" style="margin-left: {32 + GAP_PX}px">
							{#each monthLabelsWithPositions as label (label.weekIdx)}
								<div
									style="position: absolute; left: {label.weekIdx * (CELL_PX + GAP_PX)}px"
									class="text-xs font-medium text-neutral-600 dark:text-neutral-400"
								>
									{label.month}
								</div>
							{/each}
						</div>

						<!-- Day labels and heatmap -->
						<div class="flex" style="gap: {GAP_PX}px">
							<!-- Day labels -->
							<div class="flex flex-col" style="gap: {GAP_PX}px">
								{#each dayLabels as day (day)}
									<div
										class="w-8 text-xs font-medium text-neutral-600 dark:text-neutral-400 flex items-center"
										style="height: {CELL_PX}px"
									>
										{day}
									</div>
								{/each}
							</div>

							<!-- Heatmap cells -->
							<div class="flex" style="gap: {GAP_PX}px">
								{#each gridData as week, weekIdx (weekIdx)}
									<div
										class="flex flex-col {isCurrentWeek(week) ? 'ring-1 ring-brand-400/50 rounded' : ''}"
										style="gap: {GAP_PX}px"
										data-current-week={isCurrentWeek(week) ? '' : undefined}
									>
										{#each week as cell, dayIdx (dayIdx)}
											{@const inRange = isInRange(cell)}
											{@const isFuture = isFutureDate(cell.date)}
											{@const isNonWorking = !isWorkingDay(cell.date.getDay())}
											<!-- svelte-ignore a11y_no_static_element_interactions -->
											<div
												class:opacity-20={!inRange}
												class="rounded-sm cursor-pointer transition-opacity hover:opacity-80 {getColor(cell.stat, isFuture, isNonWorking)}"
												style="width: {CELL_PX}px; height: {CELL_PX}px"
												onmouseenter={(e) => inRange && onCellEnter(e, cell, isFuture)}
												onmouseleave={onCellLeave}
												onclick={() => inRange && onCellClick(cell)}
											></div>
										{/each}
									</div>
								{/each}
							</div>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>

	<!-- Tooltip (outside scroll container to avoid clipping) -->
	<HeatmapTooltip
		visible={tooltipVisible}
		x={tooltipX}
		y={tooltipY}
		date={tooltipDate}
		stat={tooltipStat}
		isFuture={tooltipIsFuture}
		titles={tooltipTitles}
		loading={tooltipLoading}
	/>
</div>
