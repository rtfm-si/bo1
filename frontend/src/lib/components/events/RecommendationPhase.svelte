<script lang="ts">
	/**
	 * RecommendationPhase Event Component
	 * Displays when recommendation phase has started
	 */
	import type { VotingStartedEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: VotingStartedEvent;
	}

	let { event }: Props = $props();
</script>

<div class="space-y-3">
	<div
		class="bg-gradient-to-r from-brand-50 to-accent-50 dark:from-brand-900/20 dark:to-accent-900/20 border border-brand-200 dark:border-brand-700 rounded-lg p-4"
	>
		<div class="flex items-center gap-3">
			<div
				class="flex-shrink-0 w-12 h-12 bg-brand-500 dark:bg-brand-600 text-white rounded-full flex items-center justify-center"
			>
				<svg
					class="w-6 h-6"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
					/>
				</svg>
			</div>
			<div class="flex-1">
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-1">
					Voting Phase Started
				</h3>
				<p class="text-sm text-neutral-600 dark:text-neutral-400">
					All experts will now provide their recommendations
				</p>
			</div>
			<Badge variant="success">{event.data.count} experts</Badge>
		</div>

		<div class="mt-3 flex flex-wrap gap-2">
			{#each event.data.experts as expert}
				<Badge variant="brand" size="sm">{expert}</Badge>
			{/each}
		</div>
	</div>
</div>
