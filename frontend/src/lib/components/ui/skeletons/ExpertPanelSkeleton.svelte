<script lang="ts">
	/**
	 * ExpertPanelSkeleton - Skeleton loader for expert panel component
	 * Shows multiple expert cards in a grid
	 */

	interface Props {
		expertCount?: number;
	}

	let { expertCount = 4 }: Props = $props();
</script>

<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 border border-slate-200 dark:border-slate-700 animate-pulse">
	<div class="h-5 bg-slate-200 dark:bg-slate-700 rounded w-1/3 mb-4"></div>
	<div class="grid grid-cols-2 gap-3">
		{#each Array(expertCount) as _, i}
			<div class="flex items-center gap-3 p-3 bg-slate-100 dark:bg-slate-800 rounded-lg">
				<div class="w-10 h-10 bg-slate-200 dark:bg-slate-700 rounded-full flex-shrink-0"></div>
				<div class="flex-1 space-y-2">
					<div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-3/4"></div>
					<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
				</div>
			</div>
		{/each}
	</div>
</div>
