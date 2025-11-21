<script lang="ts">
	/**
	 * PersonaSelection Event Component
	 * Displays a selected expert persona with rationale
	 */
	import type { PersonaSelectedEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: PersonaSelectedEvent;
	}

	let { event }: Props = $props();
</script>

<div class="space-y-3">
	<div class="flex items-start gap-3">
		<div
			class="flex-shrink-0 w-12 h-12 bg-brand-100 dark:bg-brand-900 text-brand-800 dark:text-brand-200 rounded-full flex items-center justify-center font-bold text-lg"
		>
			{event.data.order}
		</div>
		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-2 mb-2">
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
					{event.data.persona.display_name}
				</h3>
				<Badge variant="brand" size="sm">{event.data.persona.code}</Badge>
			</div>

			<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
				{event.data.rationale}
			</p>

			<div class="flex flex-wrap gap-2">
				{#each event.data.persona.domain_expertise as expertise}
					<Badge variant="neutral" size="sm">{expertise}</Badge>
				{/each}
			</div>
		</div>
	</div>
</div>
