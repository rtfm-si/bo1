<script lang="ts">
	/**
	 * WeeklyPlanView - Week Planner for workload rebalancing
	 * Rolling -2/+4 days view centered on today.
	 * Color coded: overdue (red), busy (amber), normal, empty (grey).
	 * Non-working days greyed out based on user's working pattern.
	 */
	import type { AllActionsResponse, TaskWithSessionContext } from '$lib/api/types';

	interface Props {
		actionsData: AllActionsResponse | null | undefined;
		/** ISO weekdays (1=Mon, 7=Sun) when user works. Default: Mon-Fri */
		workingPattern?: number[];
	}

	let { actionsData, workingPattern = [1, 2, 3, 4, 5] }: Props = $props();

	// Check if a date is a working day based on user's pattern
	function isWorkingDay(date: Date): boolean {
		// JS getDay: 0=Sun, 1=Mon... ISO: 1=Mon, 7=Sun
		const jsDay = date.getDay();
		const isoDay = jsDay === 0 ? 7 : jsDay;
		return workingPattern.includes(isoDay);
	}

	// Get rolling 7-day window: -2 past days + today + 4 future days
	// Today is at index 2 for workload rebalancing focus
	function getWeekDays(): Date[] {
		const today = new Date();
		today.setHours(0, 0, 0, 0);

		const days: Date[] = [];
		for (let i = -2; i <= 4; i++) {
			const d = new Date(today);
			d.setDate(today.getDate() + i);
			days.push(d);
		}
		return days;
	}

	const weekDays = $derived(getWeekDays());
	const today = $derived(new Date());

	// Count actions per day
	function countActionsForDay(date: Date): number {
		if (!actionsData?.sessions) return 0;
		const dateStr = formatDateKey(date);
		let count = 0;
		for (const session of actionsData.sessions) {
			for (const task of session.tasks as TaskWithSessionContext[]) {
				if (task.status === 'todo' || task.status === 'in_progress') {
					if (task.suggested_completion_date) {
						const taskDate = task.suggested_completion_date.split('T')[0];
						if (taskDate === dateStr) {
							count++;
						}
					}
				}
			}
		}
		return count;
	}

	// Format date as YYYY-MM-DD
	function formatDateKey(date: Date): string {
		return date.toISOString().split('T')[0];
	}

	// Format day name (Mon, Tue, etc.)
	function formatDayName(date: Date): string {
		return date.toLocaleDateString('en-US', { weekday: 'short' });
	}

	// Format day number (1, 2, etc.)
	function formatDayNumber(date: Date): number {
		return date.getDate();
	}

	// Check if date is today
	function isToday(date: Date): boolean {
		const todayStr = formatDateKey(today);
		return formatDateKey(date) === todayStr;
	}

	// Check if date is in the past
	function isPast(date: Date): boolean {
		const dateOnly = new Date(date);
		dateOnly.setHours(0, 0, 0, 0);
		const todayOnly = new Date(today);
		todayOnly.setHours(0, 0, 0, 0);
		return dateOnly < todayOnly;
	}

	// Get day status based on action count and date
	// Simplified: 0=grey, 1-3=normal, 4+=busy, past+incomplete=overdue
	function getDayStatus(date: Date, count: number): 'overdue' | 'busy' | 'normal' | 'empty' {
		if (count === 0) return 'empty';
		if (isPast(date) && count > 0) return 'overdue';
		if (count >= 4) return 'busy';
		return 'normal';
	}

	// Get classes for day card - subtle backgrounds, non-working days greyed out
	function getDayClasses(date: Date, count: number): string {
		const status = getDayStatus(date, count);
		const nonWorking = !isWorkingDay(date);
		const base = 'flex flex-col items-center p-2 sm:p-3 rounded-lg border transition-all cursor-pointer hover:shadow-md';
		const todayRing = isToday(date) ? 'ring-2 ring-brand-500 ring-offset-2 dark:ring-offset-neutral-900' : '';
		// Non-working days are greyed out (but still clickable in case user has actions on weekends)
		const nonWorkingStyle = nonWorking ? 'opacity-40' : '';

		switch (status) {
			case 'overdue':
				return `${base} ${todayRing} ${nonWorkingStyle} bg-error-50/50 dark:bg-error-900/10 border-error-200/50 dark:border-error-800/50 hover:bg-error-100/50 dark:hover:bg-error-900/20`;
			case 'busy':
				return `${base} ${todayRing} ${nonWorkingStyle} bg-warning-50/50 dark:bg-warning-900/10 border-warning-200/50 dark:border-warning-800/50 hover:bg-warning-100/50 dark:hover:bg-warning-900/20`;
			case 'normal':
				return `${base} ${todayRing} ${nonWorkingStyle} bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-700`;
			default:
				return `${base} ${todayRing} ${nonWorkingStyle} bg-neutral-100/50 dark:bg-neutral-800/50 border-neutral-200/50 dark:border-neutral-700/50 hover:bg-neutral-100 dark:hover:bg-neutral-700`;
		}
	}

	// Get badge classes for count - simpler, less colorful
	function getBadgeClasses(status: 'overdue' | 'busy' | 'normal' | 'empty'): string {
		switch (status) {
			case 'overdue':
				return 'bg-error-500 text-white';
			case 'busy':
				return 'bg-warning-500 text-white';
			case 'normal':
				return 'bg-neutral-500 text-white';
			default:
				return 'bg-neutral-300 dark:bg-neutral-600 text-neutral-600 dark:text-neutral-300';
		}
	}

	// Navigate to actions with date filter
	function getDateFilterUrl(date: Date): string {
		return `/actions?due_date=${formatDateKey(date)}`;
	}

	// Check if we have any actions to display
	const hasActions = $derived(
		actionsData?.sessions?.some(s =>
			(s.tasks as TaskWithSessionContext[]).some(t =>
				(t.status === 'todo' || t.status === 'in_progress') && t.suggested_completion_date
			)
		) ?? false
	);
</script>

<div class="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg">
	<div class="p-4 border-b border-neutral-200 dark:border-neutral-700">
		<div class="flex items-center justify-between">
			<div>
				<div class="flex items-center gap-2">
					<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
					</svg>
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Week Planner</h2>
				</div>
				<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 ml-7">Plan and rebalance your actions</p>
			</div>
			<a
				href="/actions"
				class="text-xs text-neutral-500 dark:text-neutral-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
			>
				View all actions
			</a>
		</div>
	</div>

	<div class="p-4">
		<div class="grid grid-cols-7 gap-2">
			{#each weekDays as day, idx (idx)}
				{@const count = countActionsForDay(day)}
				{@const status = getDayStatus(day, count)}
				<a
					href={getDateFilterUrl(day)}
					class={getDayClasses(day, count)}
					title="{count} action{count !== 1 ? 's' : ''} due"
				>
					<!-- Day name or "Today" -->
					<span class="text-xs font-medium {isToday(day) ? 'text-brand-600 dark:text-brand-400 font-bold' : 'text-neutral-500 dark:text-neutral-400'}">
						{isToday(day) ? 'Today' : formatDayName(day)}
					</span>

					<!-- Day number -->
					<span class="text-lg font-semibold {isToday(day) ? 'text-brand-600 dark:text-brand-400' : 'text-neutral-900 dark:text-white'}">
						{formatDayNumber(day)}
					</span>

					<!-- Action count badge (hidden when 0) -->
					{#if count > 0}
						<span class={`mt-1 px-1.5 py-0.5 text-xs font-medium rounded-full min-w-[1.25rem] text-center ${getBadgeClasses(status)}`}>
							{count}
						</span>
					{:else}
						<!-- Empty spacer to maintain layout -->
						<span class="mt-1 h-5"></span>
					{/if}
				</a>
			{/each}
		</div>

		<!-- Legend - simplified -->
		<div class="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-700 flex flex-wrap items-center gap-4 text-xs text-neutral-500 dark:text-neutral-400">
			<span class="flex items-center gap-1.5">
				<span class="w-2.5 h-2.5 rounded-full bg-error-500"></span>
				Overdue
			</span>
			<span class="flex items-center gap-1.5">
				<span class="w-2.5 h-2.5 rounded-full bg-warning-500"></span>
				Busy (4+)
			</span>
			<span class="text-neutral-400 dark:text-neutral-500">Click any day to see actions</span>
		</div>
	</div>
</div>
