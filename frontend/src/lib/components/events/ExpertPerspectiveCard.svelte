<script lang="ts">
	import { eventTokens } from '$lib/design/tokens';
	import type { SSEEvent } from '$lib/api/sse-events';

	interface ExpertPerspectiveSummary {
		looking_for: string;
		value_added: string;
		concerns: string[];
		questions: string[];
	}

	interface Props {
		event: SSEEvent & {
			data: {
				persona_code: string;
				persona_name: string;
				content: string;
				summary?: ExpertPerspectiveSummary;
				round: number;
				contribution_type: string;
			};
		};
	}

	let { event }: Props = $props();

	let showFullContent = $state(false);

	// Fallback if no summary available
	const hasSummary = $derived(event.data.summary !== null && event.data.summary !== undefined);
</script>

<div class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
	<!-- Expert Header -->
	<div class="flex items-center justify-between mb-3">
		<div class="flex items-center gap-3">
			<!-- Contribution Type Badge (instead of redundant avatar) -->
			<div class={[
				"px-2.5 py-1 rounded-md text-xs font-medium",
				event.data.contribution_type === 'research' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200' :
				event.data.contribution_type === 'insight' ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-200' :
				event.data.contribution_type === 'challenge' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200' :
				event.data.contribution_type === 'synthesis' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-200' :
				'bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300'
			].join(' ')}>
				{event.data.contribution_type || 'Contribution'}
			</div>
			<div>
				<h4 class="text-[1.25rem] font-medium leading-snug text-neutral-800 dark:text-neutral-100">
					{event.data.persona_name}
				</h4>
				<p class="text-[0.75rem] font-normal leading-normal text-neutral-500 dark:text-neutral-400">
					Round {event.data.round}
				</p>
			</div>
		</div>

		<!-- Expand toggle (only if summary exists) -->
		{#if hasSummary}
			<button
				onclick={() => (showFullContent = !showFullContent)}
				class="text-[0.75rem] text-brand-600 dark:text-brand-400 hover:underline font-medium"
			>
				{showFullContent ? 'Hide details' : 'Show full response'}
			</button>
		{/if}
	</div>

	<!-- Structured Insights (Always Visible if available) -->
	{#if hasSummary && event.data.summary}
		<div class="space-y-3">
			<!-- Looking For -->
			{#if event.data.summary.looking_for}
				<div>
					<p class="text-[0.75rem] font-medium leading-normal text-neutral-600 dark:text-neutral-400 mb-1">
						{eventTokens.insights.analyzing.label}
					</p>
					<p class="text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300">
						{event.data.summary.looking_for}
					</p>
				</div>
			{/if}

			<!-- Value Added -->
			{#if event.data.summary.value_added}
				<div>
					<p class="text-[0.75rem] font-medium leading-normal text-neutral-600 dark:text-neutral-400 mb-1">
						{eventTokens.insights.insight.label}
					</p>
					<p class="text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300">
						{event.data.summary.value_added}
					</p>
				</div>
			{/if}

			<!-- Concerns -->
			{#if event.data.summary.concerns && event.data.summary.concerns.length > 0}
				<div>
					<p class="text-[0.75rem] font-medium leading-normal text-neutral-600 dark:text-neutral-400 mb-1">
						{eventTokens.insights.concern.label}
					</p>
					<ul class="text-[0.875rem] text-neutral-700 dark:text-neutral-300 space-y-1">
						{#each event.data.summary.concerns as concern, i (i)}
							<li class="flex items-start gap-2">
								<span class="text-neutral-500 dark:text-neutral-400 flex-shrink-0 mt-1">•</span>
								<span class="leading-relaxed">{concern}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			<!-- Questions/Challenges -->
			{#if event.data.summary.questions && event.data.summary.questions.length > 0}
				<div>
					<p class="text-[0.75rem] font-medium leading-normal text-neutral-600 dark:text-neutral-400 mb-1">
						{eventTokens.insights.question.label}
					</p>
					<ul class="text-[0.875rem] text-neutral-700 dark:text-neutral-300 space-y-1">
						{#each event.data.summary.questions as question, i (i)}
							<li class="flex items-start gap-2">
								<span class="text-neutral-500 dark:text-neutral-400 flex-shrink-0 mt-1">•</span>
								<span class="leading-relaxed">{question}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			<!-- Show full content always (not just when expanded) if summary is incomplete -->
			{#if !event.data.summary.looking_for && !event.data.summary.value_added}
				<div class="mt-3">
					<p class="text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
						{event.data.content}
					</p>
				</div>
			{/if}
		</div>

		<!-- Full Content (Collapsible) -->
		{#if showFullContent && event.data.summary.looking_for && event.data.summary.value_added}
			<div class="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700">
				<p class="text-[0.75rem] font-medium leading-normal text-neutral-600 dark:text-neutral-400 mb-2">
					Full Response
				</p>
				<p class="text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
					{event.data.content}
				</p>
			</div>
		{/if}
	{:else}
		<!-- Fallback: Show full content if no summary -->
		<p class="text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
			{event.data.content}
		</p>
	{/if}
</div>
