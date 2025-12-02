<script lang="ts">
	/**
	 * DecompositionComplete Event Component
	 * Displays the list of focus areas identified during decomposition
	 */
	import type { DecompositionCompleteEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: DecompositionCompleteEvent;
	}

	let { event }: Props = $props();
</script>

<div class="space-y-3">
	<div class="flex items-center gap-2">
		<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
			Decision Breakdown Complete
		</h3>
	</div>

	<div class="space-y-2">
		{#each event.data.sub_problems as subProblem, index}
			<div
				class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="flex items-start gap-3">
					<div
						class="flex-shrink-0 w-8 h-8 bg-brand-100 dark:bg-brand-900 text-brand-800 dark:text-brand-200 rounded-full flex items-center justify-center font-bold text-sm"
					>
						{index + 1}
					</div>
					<div class="flex-1 min-w-0">
						<h4 class="font-semibold text-neutral-900 dark:text-neutral-100 mb-1">
							{subProblem.goal}
						</h4>
						<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
							{subProblem.rationale}
						</p>
						{#if subProblem.dependencies.length > 0}
							<div class="flex items-center gap-3 text-xs">
								<Badge variant="warning" size="sm">
									Depends on: {subProblem.dependencies.length} other(s)
								</Badge>
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/each}
	</div>
</div>
