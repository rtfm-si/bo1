<script lang="ts">
	/**
	 * RoundGroup Component
	 * Groups expert contributions from the same round into a collapsible section
	 */
	import type { SSEEvent } from '$lib/api/sse-events';
	import PersonaContribution from './PersonaContribution.svelte';

	interface Props {
		roundNumber: number;
		contributions: SSEEvent[];
		isCurrentRound?: boolean;
	}

	let { roundNumber, contributions, isCurrentRound = false }: Props = $props();

	// Start expanded if it's the current round OR first 2 rounds
	let isExpanded = $state(isCurrentRound || roundNumber <= 2);
</script>

<details bind:open={isExpanded} class="group mb-3">
	<summary
		class="cursor-pointer bg-slate-100 dark:bg-slate-800 rounded-lg p-4 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors list-none"
	>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-3">
				<div
					class="flex-shrink-0 w-10 h-10 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded-full flex items-center justify-center font-bold"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z"
						/>
					</svg>
				</div>
				<div>
					<h3 class="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
						Round {roundNumber}
						{#if isCurrentRound}
							<span
								class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200"
							>
								Current
							</span>
						{/if}
					</h3>
					<p class="text-sm text-slate-600 dark:text-slate-400">
						{contributions.length} expert perspective{contributions.length !== 1 ? 's' : ''}
					</p>
				</div>
			</div>
			<svg
				class="w-5 h-5 text-slate-500 transition-transform duration-200 group-open:rotate-180"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</div>
	</summary>

	<div class="mt-3 space-y-3 pl-2 border-l-2 border-slate-200 dark:border-slate-700 ml-5">
		{#each contributions as contribution (contribution.timestamp + contribution.data.persona_code)}
			<div class="pl-4">
				<PersonaContribution event={contribution as any} />
			</div>
		{/each}
	</div>
</details>
