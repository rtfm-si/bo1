<script lang="ts">
	/**
	 * SynthesisComplete Event Component
	 * Displays the synthesis report (markdown formatted)
	 */
	import type { SynthesisCompleteEvent, MetaSynthesisCompleteEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: SynthesisCompleteEvent | MetaSynthesisCompleteEvent;
	}

	let { event }: Props = $props();

	const isMeta = $derived(event.event_type === 'meta_synthesis_complete');
</script>

<div class="space-y-3">
	<div
		class="border border-success-200 dark:border-success-700 bg-success-50/50 dark:bg-success-900/10 rounded-lg p-4"
	>
		<div class="flex items-center justify-between mb-3">
			<div class="flex items-center gap-2">
				<div
					class="flex-shrink-0 w-10 h-10 bg-success-500 dark:bg-success-600 text-white rounded-full flex items-center justify-center"
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
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
					{isMeta ? 'Meta-Synthesis' : 'Synthesis'} Complete
				</h3>
			</div>
			<Badge variant="success">{event.data.word_count} words</Badge>
		</div>

		<!-- Markdown Content -->
		<div
			class="prose prose-sm dark:prose-invert max-w-none bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
		>
			<div class="whitespace-pre-wrap text-neutral-700 dark:text-neutral-300">
				{event.data.synthesis}
			</div>
		</div>

		{#if isMeta}
			<div class="mt-3 text-xs text-neutral-600 dark:text-neutral-400 italic">
				This synthesis integrates insights from multiple sub-problem deliberations.
			</div>
		{/if}
	</div>
</div>
