<script lang="ts">
	import { eventTokens } from '$lib/design/tokens';
	import type { SSEEvent } from '$lib/api/sse-events';
	import { Lightbulb, AlertTriangle, HelpCircle, Search, ChevronDown, ChevronUp } from 'lucide-svelte';

	interface ExpertPerspectiveSummary {
		concise?: string;
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
				archetype?: string;
				domain_expertise?: string[];
				content: string;
				summary?: ExpertPerspectiveSummary;
				round: number;
				contribution_type: string;
			};
		};
	}

	let { event }: Props = $props();

	// View mode: 'concise' (1-2 sentence) or 'detailed' (structured breakdown)
	let viewMode = $state<'concise' | 'detailed'>('concise');
	let showFullContent = $state(false);

	// Fallback if no summary available
	const hasSummary = $derived(event.data.summary !== null && event.data.summary !== undefined);
	const hasConcise = $derived(hasSummary && event.data.summary?.concise);
</script>

<div class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
	<!-- Expert Header -->
	<div class="flex items-center justify-between mb-3">
		<div>
			<h4 class="text-[1.25rem] font-medium leading-snug text-neutral-800 dark:text-neutral-100">
				{event.data.persona_name}
			</h4>
			{#if event.data.archetype}
				<p class="text-[0.8125rem] font-medium leading-normal text-neutral-700 dark:text-neutral-300">
					{event.data.archetype}
				</p>
			{/if}
		</div>

		<!-- View toggle buttons (concise/detailed/full) -->
		{#if hasSummary}
			<div class="flex items-center gap-2">
				{#if hasConcise}
					<button
						onclick={() => viewMode = viewMode === 'concise' ? 'detailed' : 'concise'}
						class="text-[0.75rem] px-2 py-1 rounded-md transition-colors {viewMode === 'concise'
							? 'bg-brand-100 text-brand-700 dark:bg-brand-900 dark:text-brand-300'
							: 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700'}"
					>
						{viewMode === 'concise' ? 'Concise' : 'Detailed'}
					</button>
				{/if}
				<button
					onclick={() => (showFullContent = !showFullContent)}
					class="text-[0.75rem] text-brand-600 dark:text-brand-400 hover:underline font-medium flex items-center gap-1"
				>
					{showFullContent ? 'Hide full' : 'Show full'}
					{#if showFullContent}
						<ChevronUp size={12} />
					{:else}
						<ChevronDown size={12} />
					{/if}
				</button>
			</div>
		{/if}
	</div>

	<!-- Content Display -->
	{#if hasSummary && event.data.summary}
		<!-- Concise View: 1-2 sentence summary -->
		{#if viewMode === 'concise' && hasConcise}
			<p class="text-[0.9375rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300">
				{event.data.summary.concise}
			</p>
		{:else}
			<!-- Detailed View: Structured breakdown -->
			<div class="space-y-3">
				<!-- Looking For -->
				{#if event.data.summary.looking_for}
					<div>
						<p class="text-[0.75rem] font-medium leading-normal text-neutral-600 dark:text-neutral-400 mb-1 flex items-center gap-1.5">
							<Search size={14} class="text-blue-500 dark:text-blue-400" />
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
						<p class="text-[0.75rem] font-medium leading-normal text-neutral-600 dark:text-neutral-400 mb-1 flex items-center gap-1.5">
							<Lightbulb size={14} class="text-amber-500 dark:text-amber-400" />
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
						<p class="text-[0.75rem] font-medium leading-normal text-neutral-600 dark:text-neutral-400 mb-1 flex items-center gap-1.5">
							<AlertTriangle size={14} class="text-orange-500 dark:text-orange-400" />
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
						<p class="text-[0.75rem] font-medium leading-normal text-neutral-600 dark:text-neutral-400 mb-1 flex items-center gap-1.5">
							<HelpCircle size={14} class="text-purple-500 dark:text-purple-400" />
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

				<!-- Show full content if summary is incomplete -->
				{#if !event.data.summary.looking_for && !event.data.summary.value_added}
					<div class="mt-3">
						<p class="text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
							{event.data.content}
						</p>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Full Content (Collapsible) -->
		{#if showFullContent}
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
