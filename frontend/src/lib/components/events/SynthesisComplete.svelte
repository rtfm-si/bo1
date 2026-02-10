<script lang="ts">
	/**
	 * SynthesisComplete Event Component
	 * Displays the synthesis report with parsed XML/Markdown sections
	 */
	import type { SynthesisCompleteEvent, MetaSynthesisCompleteEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';
	import ActionableTasks from './ActionableTasks.svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import { parseSynthesisXML, isXMLFormatted, isMarkdownFormatted, type SynthesisSection, type MetaSynthesisAction } from '$lib/utils/xml-parser';
	import { getPriorityConfig } from '$lib/utils/priority';

	interface Props {
		event: SynthesisCompleteEvent | MetaSynthesisCompleteEvent;
	}

	let { event }: Props = $props();

	const isMeta = $derived(event.event_type === 'meta_synthesis_complete');
	// Always try to parse - supports JSON, XML (<tag>), and Markdown (## Header) formats
	const sections = $derived(parseSynthesisXML(event.data.synthesis));
	// Check if we got meaningful parsed sections (not just raw content dumped in executive_summary)
	const hasParsedSections = $derived(
		sections &&
			(sections.recommendation ||
				sections.rationale ||
				sections.convergence_point ||
				sections.vote_breakdown ||
				sections.recommended_actions?.length ||
				Object.keys(sections).length > 2) // More than just executive_summary + warning
	);
	// Check if we have structured recommended_actions from JSON meta-synthesis
	const hasStructuredActions = $derived(sections?.recommended_actions && sections.recommended_actions.length > 0);

	function getPriorityColor(priority: string): string {
		const config = getPriorityConfig(priority);
		return `${config.badge} ${config.border}`;
	}
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
					{#if isMeta}
						Decision Complete
					{:else if event.event_type === 'synthesis_complete' && event.data.sub_problem_index !== undefined}
						Sub-Problem Complete
					{:else}
						Meeting Complete
					{/if}
				</h3>
			</div>
		</div>

		<!-- Parsed Synthesis Content -->
		{#if hasParsedSections && sections}
			<!-- Executive Summary - Prominent -->
			{#if sections.executive_summary}
				<div class="bg-info-50 dark:bg-info-900/20 border-l-4 border-info-600 p-4 rounded-r-lg mb-4">
					<h4 class="font-semibold text-info-900 dark:text-info-100 mb-2 flex items-center gap-2">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
						Executive Summary
					</h4>
					<MarkdownContent content={sections.executive_summary} class="text-sm text-info-800 dark:text-info-200" />
				</div>
			{/if}

			<!-- Key Recommendation - Highlighted -->
			{#if sections.recommendation}
				<div class="bg-success-50 dark:bg-success-900/20 border-l-4 border-success-600 p-4 rounded-r-lg mb-4">
					<h4 class="font-semibold text-success-900 dark:text-success-100 mb-2 flex items-center gap-2">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						Recommendation
					</h4>
					<MarkdownContent content={sections.recommendation} class="text-sm text-success-800 dark:text-success-200" />
				</div>
			{/if}

			<!-- Collapsible Sections -->
			<div class="space-y-2">
				{#if sections.rationale}
					<details class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Rationale
						</summary>
						<div class="px-4 pb-4 pt-2">
							<MarkdownContent content={sections.rationale} class="text-sm text-neutral-600 dark:text-neutral-400" />
						</div>
					</details>
				{/if}

				{#if sections.implementation_considerations}
					<details class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
							</svg>
							Implementation Considerations
						</summary>
						<div class="px-4 pb-4 pt-2">
							<MarkdownContent content={sections.implementation_considerations} class="text-sm text-neutral-600 dark:text-neutral-400" />
						</div>
					</details>
				{/if}

				{#if sections.confidence_assessment}
					<details class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
							</svg>
							Confidence Assessment
						</summary>
						<div class="px-4 pb-4 pt-2">
							<MarkdownContent content={sections.confidence_assessment} class="text-sm text-neutral-600 dark:text-neutral-400" />
						</div>
					</details>
				{/if}

				{#if sections.risks_and_mitigations}
					<details class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
							</svg>
							Risks & Mitigations
						</summary>
						<div class="px-4 pb-4 pt-2">
							<MarkdownContent content={sections.risks_and_mitigations} class="text-sm text-neutral-600 dark:text-neutral-400" />
						</div>
					</details>
				{/if}

				{#if sections.success_metrics}
					<details class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
							</svg>
							Success Metrics
						</summary>
						<div class="px-4 pb-4 pt-2">
							<MarkdownContent content={sections.success_metrics} class="text-sm text-neutral-600 dark:text-neutral-400" />
						</div>
					</details>
				{/if}

				{#if sections.timeline}
					<details class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Timeline
						</summary>
						<div class="px-4 pb-4 pt-2">
							<MarkdownContent content={sections.timeline} class="text-sm text-neutral-600 dark:text-neutral-400" />
						</div>
					</details>
				{/if}

				{#if sections.resources_required}
					<details class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
							</svg>
							Resources Required
						</summary>
						<div class="px-4 pb-4 pt-2">
							<MarkdownContent content={sections.resources_required} class="text-sm text-neutral-600 dark:text-neutral-400" />
						</div>
					</details>
				{/if}

				{#if sections.open_questions}
					<details class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Open Questions
						</summary>
						<div class="px-4 pb-4 pt-2">
							<MarkdownContent content={sections.open_questions} class="text-sm text-neutral-600 dark:text-neutral-400" />
						</div>
					</details>
				{/if}

				{#if sections.vote_breakdown}
					<details class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
							</svg>
							Vote Breakdown
						</summary>
						<div class="px-4 pb-4 pt-2">
							<MarkdownContent content={sections.vote_breakdown} class="text-sm text-neutral-600 dark:text-neutral-400" />
						</div>
					</details>
				{/if}

				{#if sections.convergence_point}
					<details class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg overflow-hidden" open>
						<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
							Convergence Point
						</summary>
						<div class="px-4 pb-4 pt-2">
							<MarkdownContent content={sections.convergence_point} class="text-sm text-neutral-600 dark:text-neutral-400" />
						</div>
					</details>
				{/if}

				{#if sections.dissenting_views}
					<details class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg overflow-hidden">
						<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors flex items-center gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
							</svg>
							Dissenting Views
						</summary>
						<div class="px-4 pb-4 pt-2">
							<MarkdownContent content={sections.dissenting_views} class="text-sm text-neutral-600 dark:text-neutral-400" />
						</div>
					</details>
				{/if}
			</div>
		{:else}
			<!-- Fallback: Display parsed content (even if only executive_summary) -->
			{#if sections?.executive_summary}
				<div class="bg-info-50 dark:bg-info-900/20 border-l-4 border-info-600 p-4 rounded-r-lg mb-4">
					<h4 class="font-semibold text-info-900 dark:text-info-100 mb-2 flex items-center gap-2">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
						Executive Summary
					</h4>
					<MarkdownContent content={sections.executive_summary} class="text-sm text-info-800 dark:text-info-200" />
				</div>
			{:else}
				<!-- Raw fallback if parsing completely failed -->
				<div
					class="prose prose-sm dark:prose-invert max-w-none bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
				>
					<MarkdownContent content={event.data.synthesis} class="text-neutral-700 dark:text-neutral-300" />
				</div>
			{/if}
		{/if}

		{#if isMeta}
			<div class="mt-3 text-xs text-neutral-600 dark:text-neutral-400 italic">
				This synthesis integrates insights from multiple sub-problem deliberations.
			</div>
		{/if}
	</div>

	<!-- Recommended Actions Section -->
	{#if hasStructuredActions && sections?.recommended_actions}
		<!-- Display structured recommended_actions directly from JSON meta-synthesis -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
			<div class="bg-warning-50 dark:bg-warning-900/20 border-b border-warning-200 dark:border-warning-800 px-4 py-3">
				<h4 class="font-semibold text-warning-900 dark:text-warning-100 flex items-center gap-2">
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
					</svg>
					Recommended Actions ({sections.recommended_actions.length})
				</h4>
			</div>
			<div class="divide-y divide-neutral-200 dark:divide-neutral-700">
				{#each sections.recommended_actions as action, i}
					<div class="p-4 hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors">
						<div class="flex items-start gap-3">
							<span class="flex-shrink-0 w-6 h-6 bg-warning-500 text-white rounded-full flex items-center justify-center text-sm font-medium">
								{i + 1}
							</span>
							<div class="flex-1 min-w-0">
								<div class="flex flex-wrap items-center gap-2 mb-2">
									<h5 class="font-medium text-neutral-900 dark:text-white">
										{action.title || action.action?.split(':')[0] || `Action ${i + 1}`}
									</h5>
									<span class="px-2 py-0.5 text-xs font-medium rounded border {getPriorityColor(action.priority)}">
										{action.priority}
									</span>
									{#if action.timeline}
										<span class="px-2 py-0.5 text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400 rounded">
											{action.timeline}
										</span>
									{/if}
								</div>
								{#if action.description || action.action}
									<p class="text-sm text-neutral-700 dark:text-neutral-300 mb-3">
										{action.description || action.action}
									</p>
								{/if}
								{#if action.rationale}
									<div class="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
										<span class="font-medium">Rationale:</span> {action.rationale}
									</div>
								{/if}
								{#if action.success_metrics?.length > 0}
									<div class="mt-2">
										<span class="text-xs font-medium text-neutral-500 dark:text-neutral-500 uppercase tracking-wider">Success Metrics</span>
										<ul class="mt-1 text-sm text-neutral-600 dark:text-neutral-400 list-disc list-inside">
											{#each action.success_metrics as metric}
												<li>{metric}</li>
											{/each}
										</ul>
									</div>
								{/if}
								{#if action.risks?.length > 0}
									<div class="mt-2">
										<span class="text-xs font-medium text-error-500 dark:text-error-400 uppercase tracking-wider">Risks</span>
										<ul class="mt-1 text-sm text-neutral-600 dark:text-neutral-400 list-disc list-inside">
											{#each action.risks as risk}
												<li>{risk}</li>
											{/each}
										</ul>
									</div>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{:else}
		<!-- Fallback: Use API-based ActionableTasks for non-JSON synthesis -->
		<ActionableTasks sessionId={event.session_id ?? ''} subProblemIndex={event.event_type === 'synthesis_complete' ? event.data.sub_problem_index : undefined} />
	{/if}

	<!-- Decision Gate CTA -->
	<div class="mt-6 pt-4 border-t border-neutral-200 dark:border-neutral-700">
		<button
			type="button"
			class="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium text-sm transition-colors"
			onclick={() => {
				const gate = document.getElementById('decision-gate');
				if (gate) gate.scrollIntoView({ behavior: 'smooth' });
			}}
		>
			Make Your Decision
		</button>
	</div>
</div>
