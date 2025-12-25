<script lang="ts">
	/**
	 * DailyActivities - Today's Focus panel with smart ordering
	 * Orders by: 1) Overdue high-priority, 2) Due today high-priority, 3) Overdue med/low, 4) Due today med/low
	 * Shows max 5 actions, includes time-of-day hint
	 */
	import type { AllActionsResponse, TaskWithSessionContext } from '$lib/api/types';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { getDueDateStatus, getDueDateLabel, getDueDateBadgeClasses } from '$lib/utils/due-dates';

	interface Props {
		actionsData: AllActionsResponse | null | undefined;
	}

	let { actionsData }: Props = $props();

	// Get current hour for time-of-day hint
	const currentHour = $derived(new Date().getHours());
	const timeHint = $derived(getTimeHint(currentHour));

	function getTimeHint(hour: number): { message: string; icon: string } {
		if (hour < 12) {
			return {
				message: 'Morning is ideal for complex, high-focus tasks',
				icon: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z' // Sun
			};
		} else if (hour < 17) {
			return {
				message: 'Afternoon is good for routine tasks and collaboration',
				icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' // Clock
			};
		} else {
			return {
				message: 'Evening is best for light tasks and planning',
				icon: 'M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z' // Moon
			};
		}
	}

	// Get today's date string for comparison
	function getTodayStr(): string {
		return new Date().toISOString().split('T')[0];
	}

	// Sort and filter actions for today's focus
	const focusActions = $derived.by<TaskWithSessionContext[]>(() => {
		if (!actionsData?.sessions) return [];

		const todayStr = getTodayStr();
		const allTasks = actionsData.sessions.flatMap((s) => s.tasks as TaskWithSessionContext[]);

		// Filter to active tasks (todo + in_progress)
		const activeTasks = allTasks.filter((t) => t.status === 'todo' || t.status === 'in_progress');

		// Score function: lower score = higher priority
		// Overdue high: 0-10, Due today high: 10-20, Overdue med/low: 20-40, Due today med/low: 40-60, Other: 100+
		function getScore(task: TaskWithSessionContext): number {
			const status = task.suggested_completion_date ? getDueDateStatus(task.suggested_completion_date) : 'none';
			const isOverdue = status === 'overdue';
			const isDueToday = status === 'due-today';
			const priority = task.priority || 'low';
			const priorityScore = priority === 'high' ? 0 : priority === 'medium' ? 1 : 2;

			if (isOverdue) {
				return priorityScore; // 0-2 for overdue
			}
			if (isDueToday) {
				return 10 + priorityScore; // 10-12 for due today
			}
			// Other tasks get lower priority
			return 100 + priorityScore;
		}

		// Sort by score and take top 5
		return activeTasks
			.filter((t) => {
				const status = t.suggested_completion_date ? getDueDateStatus(t.suggested_completion_date) : 'none';
				// Only include overdue, due-today, or high priority tasks
				return status === 'overdue' || status === 'due-today' || t.priority === 'high';
			})
			.sort((a, b) => getScore(a) - getScore(b))
			.slice(0, 5);
	});

	const hasFocusItems = $derived(focusActions.length > 0);

	// Truncate text helper
	function truncate(text: string, maxLength: number = 50): string {
		if (text.length <= maxLength) return text;
		return text.substring(0, maxLength) + '...';
	}
</script>

{#if hasFocusItems}
	<div class="mb-8 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg">
		<div class="p-4 border-b border-neutral-200 dark:border-neutral-700">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
					</svg>
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Today's Focus</h2>
					<span class="px-2 py-0.5 text-xs font-medium bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-full">
						{focusActions.length}
					</span>
				</div>
				<a
					href="/actions"
					class="text-xs text-neutral-500 dark:text-neutral-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
				>
					View all
				</a>
			</div>

			<!-- Time of day hint -->
			<div class="mt-2 flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={timeHint.icon} />
				</svg>
				<span>{timeHint.message}</span>
			</div>
		</div>

		<div class="divide-y divide-neutral-200 dark:divide-neutral-700">
			{#each focusActions as action, idx (action.id)}
				{@const dueDateStatus = getDueDateStatus(action.suggested_completion_date)}
				<a
					href="/actions/{action.id}"
					class="flex items-center gap-3 p-3 hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors"
				>
					<!-- Priority number -->
					<div class="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-neutral-100 dark:bg-neutral-700 text-xs font-medium text-neutral-600 dark:text-neutral-300">
						{idx + 1}
					</div>

					<!-- Content -->
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<span class="font-medium text-neutral-900 dark:text-white truncate text-sm">
								{truncate(action.title)}
							</span>
							<Badge variant={action.priority === 'high' ? 'error' : action.priority === 'medium' ? 'warning' : 'success'}>
								{action.priority}
							</Badge>
							{#if dueDateStatus === 'overdue' || dueDateStatus === 'due-today'}
								<span class={`inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded ${getDueDateBadgeClasses(dueDateStatus)}`}>
									{getDueDateLabel(dueDateStatus)}
								</span>
							{/if}
						</div>
						{#if action.status === 'in_progress'}
							<span class="text-xs text-warning-600 dark:text-warning-400 flex items-center gap-1 mt-0.5">
								<svg class="w-3 h-3 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
								</svg>
								In Progress
							</span>
						{/if}
					</div>

					<!-- Arrow -->
					<svg class="w-4 h-4 text-neutral-400 dark:text-neutral-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</a>
			{/each}
		</div>
	</div>
{/if}
