<script lang="ts">
	import type { DailyActionStat } from '$lib/api/types';

	import { formatDate } from '$lib/utils/time-formatting';
	interface Props {
		visible: boolean;
		x: number;
		y: number;
		date: string;
		stat: DailyActionStat | null;
		isFuture: boolean;
		titles: { id: string; type: string; title: string }[] | null;
		loading: boolean;
	}

	let { visible, x, y, date, stat, isFuture, titles, loading }: Props = $props();


	function truncateTitle(title: string, maxWords = 5): string {
		const words = title.split(/\s+/);
		if (words.length <= maxWords) return title;
		return words.slice(0, maxWords).join(' ') + '...';
	}

	const pastCount = $derived(stat
		? stat.sessions_run + stat.completed_count + stat.in_progress_count + stat.mentor_sessions
		: 0);
	const futureCount = $derived(stat
		? (stat.estimated_starts ?? 0) + (stat.estimated_completions ?? 0)
		: 0);
	const totalCount = $derived(pastCount + futureCount);
</script>

<div
	class="fixed z-50 pointer-events-none transition-opacity duration-100"
	style="left: {x}px; top: {y - 8}px; transform: translate(-50%, -100%); opacity: {visible ? 1 : 0}; visibility: {visible ? 'visible' : 'hidden'}"
>
	<div class="bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900 rounded-lg shadow-lg px-3 py-2 text-xs max-w-56">
		<!-- Date -->
		<div class="font-semibold mb-1">{formatDate(date)}</div>

		{#if totalCount === 0}
			<div class="text-neutral-400 dark:text-neutral-500">
				{isFuture ? 'No planned activity' : 'No activity'}
			</div>
		{:else}
			<!-- Count breakdown (non-zero only) -->
			<div class="space-y-0.5 text-neutral-300 dark:text-neutral-600">
				{#if stat && stat.sessions_run > 0}
					<div>Meetings: {stat.sessions_run}</div>
				{/if}
				{#if stat && stat.completed_count > 0}
					<div>Completed: {stat.completed_count}</div>
				{/if}
				{#if stat && stat.in_progress_count > 0}
					<div>Started: {stat.in_progress_count}</div>
				{/if}
				{#if stat && stat.mentor_sessions > 0}
					<div>Advisor: {stat.mentor_sessions}</div>
				{/if}
				{#if stat && (stat.estimated_starts ?? 0) > 0}
					<div>Planned starts: {stat.estimated_starts}</div>
				{/if}
				{#if stat && (stat.estimated_completions ?? 0) > 0}
					<div>Due dates: {stat.estimated_completions}</div>
				{/if}
			</div>

			<!-- Item titles (lazy loaded) -->
			{#if loading}
				<div class="mt-1.5 pt-1.5 border-t border-neutral-700 dark:border-neutral-300 flex items-center gap-1.5 text-neutral-400 dark:text-neutral-500">
					<svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
					</svg>
					<span>Loading...</span>
				</div>
			{:else if titles && titles.length > 0}
				<div class="mt-1.5 pt-1.5 border-t border-neutral-700 dark:border-neutral-300 space-y-0.5">
					{#each titles.slice(0, 5) as item (item.id)}
						<div class="text-neutral-300 dark:text-neutral-600 truncate">
							{truncateTitle(item.title)}
						</div>
					{/each}
					{#if titles.length > 5}
						<div class="text-neutral-500 dark:text-neutral-400">+{titles.length - 5} more</div>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
</div>
