<script lang="ts">
	/**
	 * EventCardSkeleton - Skeleton loader for event cards
	 * Matches the structure of actual event cards for better perceived performance
	 */

	interface Props {
		hasAvatar?: boolean;
		hasTitle?: boolean;
		hasContent?: boolean;
		lines?: number;
	}

	let {
		hasAvatar = true,
		hasTitle = true,
		hasContent = true,
		lines = 3
	}: Props = $props();
</script>

<div class="bg-neutral-50 dark:bg-neutral-900/50 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 animate-pulse">
	<div class="flex items-start gap-3">
		{#if hasAvatar}
			<div class="w-10 h-10 bg-neutral-200 dark:bg-neutral-700 rounded-full flex-shrink-0"></div>
		{/if}
		<div class="flex-1 space-y-3">
			{#if hasTitle}
				<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4"></div>
			{/if}
			{#if hasContent}
				{#each Array(lines) as _, i}
					<div
						class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded"
						style="width: {i === lines - 1 ? '60%' : '100%'}"
					></div>
				{/each}
			{/if}
		</div>
	</div>
</div>
