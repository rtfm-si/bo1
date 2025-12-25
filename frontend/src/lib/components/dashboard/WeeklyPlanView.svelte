<script lang="ts">
	/**
	 * WeeklyPlanView - Displays current week with action counts per day
	 * Color coded: overdue (red), overloaded (orange), normal (neutral), light (green)
	 */
	import type { AllActionsResponse, TaskWithSessionContext } from '$lib/api/types';

	interface Props {
		actionsData: AllActionsResponse | null | undefined;
	}

	let { actionsData }: Props = $props();

	// Get current week days (Monday to Sunday, ISO standard)
	function getWeekDays(): Date[] {
		const today = new Date();
		const day = today.getDay();
		// JS getDay: 0=Sun, 1=Mon... We want Monday as first day
		const mondayOffset = day === 0 ? -6 : 1 - day;
		const monday = new Date(today);
		monday.setDate(today.getDate() + mondayOffset);
		monday.setHours(0, 0, 0, 0);

		const days: Date[] = [];
		for (let i = 0; i < 7; i++) {
			const d = new Date(monday);
			d.setDate(monday.getDate() + i);
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
	function getDayStatus(date: Date, count: number): 'overdue' | 'overloaded' | 'normal' | 'light' | 'empty' {
		if (count === 0) return 'empty';
		if (isPast(date) && count > 0) return 'overdue';
		if (count > 5) return 'overloaded';
		if (count <= 2) return 'light';
		return 'normal';
	}

	// Get classes for day card
	function getDayClasses(date: Date, count: number): string {
		const status = getDayStatus(date, count);
		const base = 'flex flex-col items-center p-2 sm:p-3 rounded-lg border transition-all cursor-pointer hover:shadow-md';
		const todayRing = isToday(date) ? 'ring-2 ring-brand-500 ring-offset-2 dark:ring-offset-neutral-900' : '';

		switch (status) {
			case 'overdue':
				return `${base} ${todayRing} bg-error-50 dark:bg-error-900/20 border-error-200 dark:border-error-800 hover:bg-error-100 dark:hover:bg-error-900/30`;
			case 'overloaded':
				return `${base} ${todayRing} bg-warning-50 dark:bg-warning-900/20 border-warning-200 dark:border-warning-800 hover:bg-warning-100 dark:hover:bg-warning-900/30`;
			case 'light':
				return `${base} ${todayRing} bg-success-50 dark:bg-success-900/20 border-success-200 dark:border-success-800 hover:bg-success-100 dark:hover:bg-success-900/30`;
			case 'normal':
				return `${base} ${todayRing} bg-brand-50 dark:bg-brand-900/20 border-brand-200 dark:border-brand-800 hover:bg-brand-100 dark:hover:bg-brand-900/30`;
			default:
				return `${base} ${todayRing} bg-neutral-50 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-700`;
		}
	}

	// Get badge classes for count
	function getBadgeClasses(status: 'overdue' | 'overloaded' | 'normal' | 'light' | 'empty'): string {
		switch (status) {
			case 'overdue':
				return 'bg-error-500 text-white';
			case 'overloaded':
				return 'bg-warning-500 text-white';
			case 'light':
				return 'bg-success-500 text-white';
			case 'normal':
				return 'bg-brand-500 text-white';
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
			<div class="flex items-center gap-2">
				<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
				</svg>
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">This Week</h2>
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
				>
					<!-- Day name -->
					<span class="text-xs font-medium text-neutral-500 dark:text-neutral-400 {isToday(day) ? 'text-brand-600 dark:text-brand-400' : ''}">
						{formatDayName(day)}
					</span>

					<!-- Day number -->
					<span class="text-lg font-semibold {isToday(day) ? 'text-brand-600 dark:text-brand-400' : 'text-neutral-900 dark:text-white'}">
						{formatDayNumber(day)}
					</span>

					<!-- Action count badge -->
					<span class={`mt-1 px-1.5 py-0.5 text-xs font-medium rounded-full min-w-[1.25rem] text-center ${getBadgeClasses(status)}`}>
						{count}
					</span>
				</a>
			{/each}
		</div>

		<!-- Legend -->
		<div class="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-700 flex flex-wrap items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
			<span class="flex items-center gap-1.5">
				<span class="w-2.5 h-2.5 rounded-full bg-error-500"></span>
				Overdue
			</span>
			<span class="flex items-center gap-1.5">
				<span class="w-2.5 h-2.5 rounded-full bg-warning-500"></span>
				Overloaded (6+)
			</span>
			<span class="flex items-center gap-1.5">
				<span class="w-2.5 h-2.5 rounded-full bg-brand-500"></span>
				Normal (3-5)
			</span>
			<span class="flex items-center gap-1.5">
				<span class="w-2.5 h-2.5 rounded-full bg-success-500"></span>
				Light (1-2)
			</span>
		</div>
	</div>
</div>
