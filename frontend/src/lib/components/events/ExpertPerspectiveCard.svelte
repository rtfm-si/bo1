<script lang="ts">
	import { eventTokens } from '$lib/design/tokens';
	import type { SSEEvent } from '$lib/api/sse-events';
	import { Lightbulb, AlertTriangle, HelpCircle, Search } from 'lucide-svelte';

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
		// View mode controlled by parent (sub-problem level)
		viewMode?: 'simple' | 'full';
		// Whether to show full transcript (controlled by parent)
		showFull?: boolean;
		// Optional callback for toggling this card's view mode
		onToggle?: () => void;
	}

	let { event, viewMode = 'simple', showFull = false, onToggle }: Props = $props();

	// Fallback if no summary available
	const hasSummary = $derived(event.data.summary !== null && event.data.summary !== undefined);
	const hasSimpleSummary = $derived(hasSummary && event.data.summary?.concise);

	// Fallback: Generate simple summary from value_added or content if concise not available
	const simpleFallback = $derived.by(() => {
		if (hasSimpleSummary) return event.data.summary?.concise;
		if (event.data.summary?.value_added) {
			const text = event.data.summary.value_added;
			return text.length > 250 ? text.slice(0, 250) + '...' : text;
		}
		if (event.data.content) {
			// Take first 250 chars of content as fallback
			return event.data.content.length > 250 ? event.data.content.slice(0, 250) + '...' : event.data.content;
		}
		return null;
	});
	const canShowSimple = $derived(simpleFallback !== null);
</script>

<svelte:element
	this={onToggle ? 'button' : 'div'}
	class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 {onToggle ? 'hover:border-brand-300 dark:hover:border-brand-600 cursor-pointer' : ''} transition-all shadow-sm {onToggle ? 'hover:shadow-md w-full text-left' : ''}"
	onclick={onToggle}
	onkeydown={onToggle ? (e: KeyboardEvent) => e.key === 'Enter' && onToggle?.() : undefined}
	role={onToggle ? 'button' : undefined}
	tabindex={onToggle ? 0 : undefined}
>
	<!-- Expert Header -->
	<div class="flex items-center justify-between mb-3">
		<div>
			<h4 class="text-[1.25rem] font-medium leading-snug text-neutral-800 dark:text-neutral-100">
				{event.data.persona_name}
				{#if event.data.archetype}
					<span class="text-[0.875rem] font-normal text-neutral-600 dark:text-neutral-400">
						— {event.data.archetype}
					</span>
				{/if}
			</h4>
		</div>
	</div>

	<!-- Content Display -->
	{#if hasSummary && event.data.summary}
		<!-- Simple View: 1-2 sentence summary (with fallback generation) -->
		{#if viewMode === 'simple' && canShowSimple}
			<p class="text-[0.9375rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300">
				{simpleFallback}
			</p>
		{:else}
			<!-- Full View: Structured breakdown -->
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

		<!-- Full Transcript (when showFull is true) -->
		{#if showFull}
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
		<!-- Fallback: Show truncated or full content based on viewMode -->
		{#if viewMode === 'simple' && event.data.content.length > 250}
			<p class="text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
				{event.data.content.slice(0, 250)}...
			</p>
		{:else}
			<p class="text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
				{event.data.content}
			</p>
		{/if}
	{/if}
</svelte:element>
