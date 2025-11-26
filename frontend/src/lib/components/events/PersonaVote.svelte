<script lang="ts">
	/**
	 * PersonaVote Event Component
	 * Displays an expert's recommendation with confidence and conditions
	 */
	import type { PersonaVoteEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: PersonaVoteEvent;
	}

	let { event }: Props = $props();

	// Convert confidence to descriptive text
	const confidenceText = $derived(
		event.data.confidence >= 0.85
			? 'very high confidence'
			: event.data.confidence >= 0.7
				? 'high confidence'
				: event.data.confidence >= 0.5
					? 'medium confidence'
					: 'low confidence'
	);
	const confidenceVariant = $derived(
		event.data.confidence >= 0.7
			? 'success'
			: event.data.confidence >= 0.5
				? 'info'
				: 'warning'
	);
</script>

<div class="space-y-3">
	<div
		class="border border-brand-200 dark:border-brand-700 bg-brand-50/50 dark:bg-brand-900/10 rounded-lg p-4"
	>
		<div class="flex items-start gap-3">
			<div
				class="flex-shrink-0 w-10 h-10 bg-brand-500 dark:bg-brand-600 text-white rounded-full flex items-center justify-center font-bold"
			>
				{event.data.persona_code.substring(0, 2)}
			</div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-2">
					<h3 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
						{event.data.persona_name}
					</h3>
					<Badge variant={confidenceVariant} size="sm">
						{confidenceText}
					</Badge>
				</div>

				<!-- Recommendation -->
				<div class="mb-3">
					<h4 class="text-xs font-semibold text-neutral-600 dark:text-neutral-400 uppercase mb-1">
						Recommendation
					</h4>
					<p class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
						{event.data.recommendation}
					</p>
				</div>

				<!-- Reasoning -->
				<div class="mb-3">
					<h4 class="text-xs font-semibold text-neutral-600 dark:text-neutral-400 uppercase mb-1">
						Reasoning
					</h4>
					<p class="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
						{event.data.reasoning}
					</p>
				</div>

				<!-- Conditions -->
				{#if event.data.conditions && event.data.conditions.length > 0}
					<div>
						<h4 class="text-xs font-semibold text-neutral-600 dark:text-neutral-400 uppercase mb-2">
							Conditions
						</h4>
						<ul class="space-y-1">
							{#each event.data.conditions as condition}
								<li class="flex items-start gap-2 text-sm text-neutral-700 dark:text-neutral-300">
									<span class="text-brand-500 mt-0.5">•</span>
									<span>{condition}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
