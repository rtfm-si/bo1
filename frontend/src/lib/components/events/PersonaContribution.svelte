<script lang="ts">
	/**
	 * PersonaContribution Event Component
	 * Displays an expert's contribution to the deliberation
	 */
	import type { ContributionEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { getPersonaColor, getInitials } from '$lib/utils/color-helpers';

	interface Props {
		event: ContributionEvent;
	}

	let { event }: Props = $props();
</script>

<div class="space-y-3">
	<div class="flex items-start gap-3">
		<div
			class="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center font-bold text-base border-2 {getPersonaColor(event.data.persona_code)}"
		>
			{getInitials(event.data.persona_name)}
		</div>
		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-2 mb-2 flex-wrap">
				<h3 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
					{event.data.persona_name}
					{#if event.data.archetype}
						<span class="text-[0.875rem] font-normal text-neutral-600 dark:text-neutral-400">
							— {event.data.archetype}
						</span>
					{/if}
				</h3>
				<Badge variant="brand" size="sm">Round {event.data.round}</Badge>
				{#if event.data.contribution_type === 'initial'}
					<Badge variant="success" size="sm">Initial</Badge>
				{:else}
					<Badge variant="neutral" size="sm">Follow-up</Badge>
				{/if}
			</div>

			<div
				class="prose prose-sm dark:prose-invert max-w-none text-neutral-700 dark:text-neutral-300"
			>
				<p class="whitespace-pre-wrap">{event.data.content}</p>
			</div>
		</div>
	</div>
</div>
