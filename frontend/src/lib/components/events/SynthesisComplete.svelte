<script lang="ts">
	/**
	 * SynthesisComplete Event Component
	 * Displays the synthesis report with parsed XML sections
	 */
	import type { SynthesisCompleteEvent, MetaSynthesisCompleteEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';
	import ActionableTasks from './ActionableTasks.svelte';
	import { parseSynthesisXML, isXMLFormatted, type SynthesisSection } from '$lib/utils/xml-parser';

	interface Props {
		event: SynthesisCompleteEvent | MetaSynthesisCompleteEvent;
	}

	let { event }: Props = $props();

	const isMeta = $derived(event.event_type === 'meta_synthesis_complete');
	const isXML = $derived(isXMLFormatted(event.data.synthesis));
	const sections = $derived(isXML ? parseSynthesisXML(event.data.synthesis) : null);
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
					{isMeta ? 'Decision' : 'Meeting'} Complete
				</h3>
			</div>
		</div>

		<!-- Parsed Synthesis Content -->
		{#if sections}
			<!-- Executive Summary - Prominent -->
			{#if sections.executive_summary}
				<div class="bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-600 p-4 rounded-r-lg mb-4">
					<h4 class="font-semibold text-blue-900 dark:text-blue-100 mb-2 flex items-center gap-2">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
						Executive Summary
					</h4>
					<div class="text-sm text-blue-800 dark:text-blue-200 whitespace-pre-wrap">
						{sections.executive_summary}
					</div>
				</div>
			{/if}

			<!-- Key Recommendation - Highlighted -->
			{#if sections.recommendation}
				<div class="bg-green-50 dark:bg-green-900/20 border-l-4 border-green-600 p-4 rounded-r-lg mb-4">
					<h4 class="font-semibold text-green-900 dark:text-green-100 mb-2 flex items-center gap-2">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						Recommendation
					</h4>
					<div class="text-sm text-green-800 dark:text-green-200 whitespace-pre-wrap">
						{sections.recommendation}
					</div>
				</div>
			{/if}

			<!-- Collapsible Sections -->
			<div class="space-y-2">
				{#if sections.rationale}
					<details class="bg-slate-50 dark:bg-slate-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Rationale
						</summary>
						<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
							{sections.rationale}
						</div>
					</details>
				{/if}

				{#if sections.implementation_considerations}
					<details class="bg-slate-50 dark:bg-slate-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
							</svg>
							Implementation Considerations
						</summary>
						<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
							{sections.implementation_considerations}
						</div>
					</details>
				{/if}

				{#if sections.confidence_assessment}
					<details class="bg-slate-50 dark:bg-slate-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
							</svg>
							Confidence Assessment
						</summary>
						<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
							{sections.confidence_assessment}
						</div>
					</details>
				{/if}

				{#if sections.risks_and_mitigations}
					<details class="bg-slate-50 dark:bg-slate-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
							</svg>
							Risks & Mitigations
						</summary>
						<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
							{sections.risks_and_mitigations}
						</div>
					</details>
				{/if}

				{#if sections.success_metrics}
					<details class="bg-slate-50 dark:bg-slate-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
							</svg>
							Success Metrics
						</summary>
						<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
							{sections.success_metrics}
						</div>
					</details>
				{/if}

				{#if sections.timeline}
					<details class="bg-slate-50 dark:bg-slate-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Timeline
						</summary>
						<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
							{sections.timeline}
						</div>
					</details>
				{/if}

				{#if sections.resources_required}
					<details class="bg-slate-50 dark:bg-slate-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
							</svg>
							Resources Required
						</summary>
						<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
							{sections.resources_required}
						</div>
					</details>
				{/if}

				{#if sections.open_questions}
					<details class="bg-slate-50 dark:bg-slate-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Open Questions
						</summary>
						<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
							{sections.open_questions}
						</div>
					</details>
				{/if}

				{#if sections.vote_breakdown}
					<details class="bg-slate-50 dark:bg-slate-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
							</svg>
							Vote Breakdown
						</summary>
						<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
							{sections.vote_breakdown}
						</div>
					</details>
				{/if}
			</div>
		{:else}
			<!-- Fallback: Display raw content if not XML -->
			<div
				class="prose prose-sm dark:prose-invert max-w-none bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="whitespace-pre-wrap text-neutral-700 dark:text-neutral-300">
					{event.data.synthesis}
				</div>
			</div>
		{/if}

		{#if isMeta}
			<div class="mt-3 text-xs text-neutral-600 dark:text-neutral-400 italic">
				This synthesis integrates insights from multiple sub-problem deliberations.
			</div>
		{/if}
	</div>

	<!-- Actionable Tasks Section (show for both synthesis_complete and meta_synthesis_complete) -->
	<ActionableTasks sessionId={event.session_id} />
</div>
