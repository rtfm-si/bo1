<script lang="ts">
	/**
	 * FacilitatorDecision Event Component
	 * Displays the facilitator's decision on how to proceed
	 */
	import type { FacilitatorDecisionEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: FacilitatorDecisionEvent;
	}

	let { event }: Props = $props();

	const actionLabels: Record<string, string> = {
		continue: 'Continue Discussion',
		vote: 'Proceed to Voting',
		research: 'Research Needed',
		clarify: 'User Clarification Required',
		moderator: 'Moderator Intervention',
	};

	const actionVariants: Record<string, 'info' | 'success' | 'warning' | 'error'> = {
		continue: 'info',
		vote: 'success',
		research: 'warning',
		clarify: 'warning',
		moderator: 'error',
	};
</script>

<div class="space-y-3">
	<div class="flex items-center gap-2">
		<div
			class="flex-shrink-0 w-10 h-10 bg-accent-100 dark:bg-accent-900 text-accent-800 dark:text-accent-200 rounded-full flex items-center justify-center"
		>
			<svg
				class="w-5 h-5"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
				/>
			</svg>
		</div>
		<div class="flex-1">
			<div class="flex items-center gap-2 mb-1">
				<h3 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
					Facilitator Decision
				</h3>
				<Badge variant={actionVariants[event.data.action]}>
					{actionLabels[event.data.action]}
				</Badge>
			</div>

			<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
				{event.data.reasoning}
			</p>

			{#if event.data.next_speaker}
				<p class="text-sm text-neutral-700 dark:text-neutral-300">
					<span class="font-medium">Next speaker:</span>
					{event.data.next_speaker}
				</p>
			{/if}

			<div class="text-xs text-neutral-500 dark:text-neutral-400 mt-2">
				Round {event.data.round}
			</div>
		</div>
	</div>
</div>
