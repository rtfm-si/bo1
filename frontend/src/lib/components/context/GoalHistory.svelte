<script lang="ts">
	/**
	 * GoalHistory - Displays timeline of north star goal changes
	 * Shows evolution of goals over time with dates
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';

	import { formatDate } from '$lib/utils/time-formatting';
	interface GoalEntry {
		goal_text: string;
		changed_at: string;
		previous_goal: string | null;
	}

	interface Props {
		limit?: number;
	}

	let { limit = 10 }: Props = $props();

	let entries = $state<GoalEntry[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let expanded = $state(false);

	onMount(async () => {
		try {
			const data = await apiClient.getGoalHistory(limit);
			entries = data.entries ?? [];
		} catch (e) {
			error = 'Failed to load goal history';
		} finally {
			loading = false;
		}
	});


	function formatRelativeTime(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

		if (diffDays === 0) return 'Today';
		if (diffDays === 1) return 'Yesterday';
		if (diffDays < 7) return `${diffDays} days ago`;
		if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
		if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
		return `${Math.floor(diffDays / 365)} years ago`;
	}

	const displayEntries = $derived(expanded ? entries : entries.slice(0, 3));
	const hasMore = $derived(entries.length > 3);
</script>

{#if loading}
	<div class="animate-pulse space-y-3">
		{#each [1, 2, 3] as _}
			<div class="flex gap-3">
				<div class="w-3 h-3 rounded-full bg-neutral-200 dark:bg-neutral-700 mt-1.5"></div>
				<div class="flex-1 space-y-2">
					<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4"></div>
					<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-1/4"></div>
				</div>
			</div>
		{/each}
	</div>
{:else if error}
	<p class="text-sm text-neutral-500 dark:text-neutral-400">{error}</p>
{:else if entries.length === 0}
	<p class="text-sm text-neutral-500 dark:text-neutral-400">No goal history yet. Set your first goal to start tracking.</p>
{:else}
	<div class="space-y-0">
		{#each displayEntries as entry, idx (entry.changed_at)}
			<div class="flex gap-3 relative">
				<!-- Timeline connector -->
				{#if idx < displayEntries.length - 1}
					<div class="absolute left-1.5 top-6 w-0.5 h-full bg-neutral-200 dark:bg-neutral-700"></div>
				{/if}

				<!-- Timeline dot -->
				<div class="flex-shrink-0 w-3 h-3 rounded-full mt-1.5 {idx === 0 ? 'bg-brand-500' : 'bg-neutral-300 dark:bg-neutral-600'}"></div>

				<!-- Content -->
				<div class="flex-1 pb-4 min-w-0">
					<p class="text-sm font-medium text-neutral-900 dark:text-white break-words">
						{entry.goal_text}
					</p>
					<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
						{formatRelativeTime(entry.changed_at)}
						<span class="hidden sm:inline"> &middot; {formatDate(entry.changed_at)}</span>
					</p>
					{#if entry.previous_goal}
						<p class="text-xs text-neutral-400 dark:text-neutral-500 mt-1 italic">
							Changed from: {entry.previous_goal}
						</p>
					{/if}
				</div>
			</div>
		{/each}

		{#if hasMore}
			<button
				type="button"
				onclick={() => expanded = !expanded}
				class="text-xs text-brand-600 dark:text-brand-400 hover:underline mt-2"
			>
				{expanded ? 'Show less' : `Show ${entries.length - 3} more`}
			</button>
		{/if}
	</div>
{/if}
