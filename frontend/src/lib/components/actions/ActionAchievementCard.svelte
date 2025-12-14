<script lang="ts">
	/**
	 * ActionAchievementCard - Shareable achievement card for completed actions.
	 * Fixed dimensions for consistent social preview rendering.
	 */
	import { Trophy, CheckCircle2, Calendar, FolderKanban, Timer } from 'lucide-svelte';

	interface Props {
		/** Action title */
		title: string;
		/** Completion date */
		completionDate: string;
		/** Days to complete (actual) */
		daysToComplete?: number;
		/** Project name (optional) */
		projectName?: string;
		/** Priority level */
		priority?: 'high' | 'medium' | 'low';
	}

	let { title, completionDate, daysToComplete, projectName, priority = 'medium' }: Props = $props();

	// Format date for display
	function formatDate(dateStr: string): string {
		try {
			const date = new Date(dateStr);
			return date.toLocaleDateString('en-US', {
				month: 'short',
				day: 'numeric',
				year: 'numeric'
			});
		} catch {
			return dateStr;
		}
	}

	// Get achievement message based on completion speed
	function getAchievementMessage(days: number | undefined): string {
		if (!days) return 'Task Completed';
		if (days <= 1) return 'Lightning Fast!';
		if (days <= 3) return 'Quick Win!';
		if (days <= 7) return 'Solid Progress';
		if (days <= 14) return 'Mission Accomplished';
		return 'Goal Achieved';
	}

	// Truncate text for card
	function truncateText(text: string, maxLength: number): string {
		if (text.length <= maxLength) return text;
		return text.slice(0, maxLength - 3) + '...';
	}

	// Get priority color
	function getPriorityColor(p: string): string {
		switch (p) {
			case 'high': return 'text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30';
			case 'medium': return 'text-warning-600 dark:text-warning-400 bg-warning-50 dark:bg-warning-900/30';
			case 'low': return 'text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800';
			default: return 'text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800';
		}
	}
</script>

<!-- Card container with fixed dimensions for social sharing (1200x630 aspect ratio scaled down) -->
<div class="w-[600px] h-[315px] bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-700 overflow-hidden flex flex-col">
	<!-- Header with achievement badge -->
	<div class="px-6 py-4 bg-gradient-to-r from-success-50 to-brand-50 dark:from-success-900/20 dark:to-brand-900/20 border-b border-neutral-200 dark:border-neutral-700">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-3">
				<div class="w-10 h-10 rounded-full bg-success-500 flex items-center justify-center shadow-md">
					<Trophy class="w-5 h-5 text-white" />
				</div>
				<div>
					<span class="text-lg font-bold text-success-700 dark:text-success-300">
						{getAchievementMessage(daysToComplete)}
					</span>
					{#if daysToComplete}
						<p class="text-xs text-neutral-600 dark:text-neutral-400">
							Completed in {daysToComplete} day{daysToComplete !== 1 ? 's' : ''}
						</p>
					{/if}
				</div>
			</div>
			<div class="flex items-center gap-2">
				<div class="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
					<span class="text-white font-bold text-sm">Bo1</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Main content -->
	<div class="flex-1 px-6 py-5 flex flex-col">
		<!-- Action title -->
		<div class="flex-1 flex items-center">
			<div class="flex items-start gap-3 w-full">
				<div class="flex-shrink-0 w-10 h-10 rounded-full bg-success-100 dark:bg-success-900/30 flex items-center justify-center">
					<CheckCircle2 class="w-5 h-5 text-success-600 dark:text-success-400" />
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 leading-snug line-clamp-3">
						{truncateText(title, 150)}
					</p>
				</div>
			</div>
		</div>

		<!-- Metadata row -->
		<div class="flex items-center justify-between pt-4 border-t border-neutral-100 dark:border-neutral-800 mt-auto">
			<!-- Project (if available) -->
			{#if projectName}
				<div class="flex items-center gap-1.5 text-neutral-600 dark:text-neutral-400">
					<FolderKanban class="w-4 h-4" />
					<span class="text-sm">{truncateText(projectName, 30)}</span>
				</div>
			{:else}
				<div class="flex items-center gap-1.5">
					<span class={`text-xs font-medium px-2 py-0.5 rounded ${getPriorityColor(priority)}`}>
						{priority.charAt(0).toUpperCase() + priority.slice(1)} Priority
					</span>
				</div>
			{/if}

			<!-- Days to complete -->
			{#if daysToComplete}
				<div class="flex items-center gap-1.5 text-neutral-600 dark:text-neutral-400">
					<Timer class="w-4 h-4" />
					<span class="text-sm">{daysToComplete} day{daysToComplete !== 1 ? 's' : ''}</span>
				</div>
			{/if}

			<!-- Completion date -->
			<div class="flex items-center gap-1.5 text-neutral-600 dark:text-neutral-400">
				<Calendar class="w-4 h-4" />
				<span class="text-sm">{formatDate(completionDate)}</span>
			</div>
		</div>
	</div>
</div>
