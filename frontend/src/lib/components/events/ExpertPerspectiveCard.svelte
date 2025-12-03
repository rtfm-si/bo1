<script lang="ts">
	import { eventTokens } from '$lib/design/tokens';
	import type { SSEEvent } from '$lib/api/sse-events';
	import { Lightbulb, AlertTriangle, HelpCircle, Search } from 'lucide-svelte';

	interface ExpertPerspectiveSummary {
		concise?: string;
		looking_for?: string;
		value_added?: string;
		concerns?: string[];
		questions?: string[];
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

	// Check if summary has useful structured data (not just exists, but has actual content)
	const hasSummary = $derived.by(() => {
		const summary = event.data.summary;
		if (!summary) return false;
		// Check if any structured field has content
		return !!(
			summary.concise ||
			summary.looking_for ||
			summary.value_added ||
			(summary.concerns && summary.concerns.length > 0) ||
			(summary.questions && summary.questions.length > 0)
		);
	});
	const hasSimpleSummary = $derived(hasSummary && event.data.summary?.concise);

	/**
	 * Extract a clean summary from raw content
	 * - Removes XML tags like <thinking>, <recommendation>
	 * - Takes first meaningful sentence(s)
	 */
	function extractCleanSummary(content: string, maxLength: number = 250): string {
		// Remove XML-like tags and their content
		let cleaned = content
			.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '')
			.replace(/<[^>]+>[\s\S]*?<\/[^>]+>/gi, '')
			.replace(/<[^>]+>/g, '')
			.replace(/\n+/g, ' ')
			.trim();

		// Try to end on a sentence boundary
		if (cleaned.length > maxLength) {
			const truncated = cleaned.slice(0, maxLength);
			const lastPeriod = truncated.lastIndexOf('.');
			const lastQuestion = truncated.lastIndexOf('?');
			const lastExclaim = truncated.lastIndexOf('!');
			const lastSentenceEnd = Math.max(lastPeriod, lastQuestion, lastExclaim);

			if (lastSentenceEnd > maxLength * 0.5) {
				return truncated.slice(0, lastSentenceEnd + 1);
			}
			return truncated + '...';
		}
		return cleaned;
	}

	// Fallback: Generate simple summary from value_added or content if concise not available
	const simpleFallback = $derived.by(() => {
		if (hasSimpleSummary) return event.data.summary?.concise;
		if (event.data.summary?.value_added) {
			return extractCleanSummary(event.data.summary.value_added, 250);
		}
		if (event.data.content) {
			return extractCleanSummary(event.data.content, 250);
		}
		return null;
	});
	const canShowSimple = $derived(simpleFallback !== null);
</script>

<svelte:element
	this={onToggle ? 'button' : 'div'}
	class="bg-white dark:bg-neutral-800 rounded-xl border border-neutral-200 dark:border-neutral-700 {onToggle ? 'hover:border-brand-300 dark:hover:border-brand-600 cursor-pointer' : ''} transition-all shadow-sm {onToggle ? 'hover:shadow-md w-full text-left' : ''} overflow-hidden"
	onclick={onToggle}
	onkeydown={onToggle ? (e: KeyboardEvent) => e.key === 'Enter' && onToggle?.() : undefined}
	role={onToggle ? 'button' : undefined}
	tabindex={onToggle ? 0 : undefined}
>
	<div class="border-l-4 border-brand-500 dark:border-brand-400 p-5">
		<!-- Expert Header - Single line with gap between name and role -->
		<div class="flex items-baseline gap-3 mb-3">
			<h4 class="text-lg font-bold text-neutral-900 dark:text-white leading-tight tracking-tight">
				{event.data.persona_name}
			</h4>
			{#if event.data.archetype}
				<span class="text-sm font-medium text-brand-600 dark:text-brand-400">
					{event.data.archetype}
				</span>
			{/if}
		</div>

		<!-- Content Display -->
		{#if hasSummary && event.data.summary}
			<!-- Simple View: 1-2 sentence summary (with fallback generation) -->
			{#if viewMode === 'simple' && canShowSimple}
				<p class="text-[0.9375rem] leading-relaxed text-neutral-600 dark:text-neutral-300">
					{simpleFallback}
				</p>
			{:else}
			<!-- Full View: Structured breakdown -->
			<div class="space-y-3">
				<!-- Looking For -->
				{#if event.data.summary.looking_for}
					<div>
						<p class="text-[0.75rem] font-semibold leading-normal text-neutral-900 dark:text-white mb-1 flex items-center gap-1.5">
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
						<p class="text-[0.75rem] font-semibold leading-normal text-neutral-900 dark:text-white mb-1 flex items-center gap-1.5">
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
						<p class="text-[0.75rem] font-semibold leading-normal text-neutral-900 dark:text-white mb-1 flex items-center gap-1.5">
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
						<p class="text-[0.75rem] font-semibold leading-normal text-neutral-900 dark:text-white mb-1 flex items-center gap-1.5">
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
		<!-- Fallback: Show cleaned and truncated content when no summary available -->
		{#if viewMode === 'simple'}
			<p class="text-[0.9375rem] leading-relaxed text-neutral-600 dark:text-neutral-300">
				{simpleFallback || extractCleanSummary(event.data.content, 250)}
			</p>
		{:else}
			<p class="text-[0.9375rem] leading-relaxed text-neutral-600 dark:text-neutral-300 whitespace-pre-wrap">
				{extractCleanSummary(event.data.content, 1000)}
			</p>
		{/if}
	{/if}
	</div>
</svelte:element>
