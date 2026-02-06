<script lang="ts">
	/**
	 * ExpertSummariesPanel Component (P2-004)
	 * Displays expert summaries in a collapsible accordion format
	 * Shows each expert's summary from the synthesis phase
	 */
	import type { Persona } from '$lib/api/sse-events';
	import { ChevronDown, ChevronUp } from 'lucide-svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';

	interface Props {
		expertSummaries: Record<string, string>; // persona_code → summary text
		personas: Persona[]; // All personas selected for this sub-problem
		subProblemGoal?: string;
	}

	let { expertSummaries, personas, subProblemGoal }: Props = $props();

	// Track which summaries are expanded
	let expandedSummaries = $state<Set<string>>(new Set());

	function toggleSummary(personaCode: string) {
		if (expandedSummaries.has(personaCode)) {
			expandedSummaries.delete(personaCode);
		} else {
			expandedSummaries.add(personaCode);
		}
		// Trigger reactivity
		expandedSummaries = new Set(expandedSummaries);
	}

	// Get persona by code
	function getPersona(code: string): Persona | undefined {
		return personas.find((p) => p.code === code);
	}

	// Get expert summaries with persona info
	const expertsWithSummaries = $derived(
		Object.entries(expertSummaries)
			.map(([code, summary]) => ({
				code,
				summary,
				persona: getPersona(code)
			}))
			.filter((item) => item.persona !== undefined)
	);

	const hasSummaries = $derived(expertsWithSummaries.length > 0);
</script>

{#if hasSummaries}
	<div
		class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden"
	>
		<!-- Header -->
		<div class="border-b border-slate-200 dark:border-slate-700 p-4">
			<div class="flex items-center gap-2">
				<svg
					class="w-5 h-5 text-purple-600 dark:text-purple-400"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
					/>
				</svg>
				<h3 class="text-lg font-semibold text-slate-900 dark:text-white">Expert Summaries</h3>
			</div>
			{#if subProblemGoal}
				<p class="text-sm text-slate-600 dark:text-slate-400 mt-1">{subProblemGoal}</p>
			{/if}
		</div>

		<!-- Expert Summaries Accordion -->
		<div class="divide-y divide-slate-200 dark:divide-slate-700">
			{#each expertsWithSummaries as { code, summary, persona }}
				{@const isExpanded = expandedSummaries.has(code)}
				<div class="border-b border-slate-200 dark:border-slate-700 last:border-b-0">
					<button
						type="button"
						onclick={() => toggleSummary(code)}
						class="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
					>
						<div class="flex items-center gap-3 flex-1 text-left">
							<!-- Expert Avatar/Icon -->
							<div
								class="flex-shrink-0 w-10 h-10 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full flex items-center justify-center font-semibold"
							>
								{persona?.display_name?.[0] || code[0].toUpperCase()}
							</div>
							<!-- Expert Name & Archetype -->
							<div class="flex-1 min-w-0">
								<h4 class="font-medium text-slate-900 dark:text-white">
									{persona?.display_name || code}
								</h4>
								<p class="text-sm text-slate-600 dark:text-slate-400">
									{persona?.archetype || 'Expert'}
								</p>
							</div>
						</div>
						<!-- Expand/Collapse Icon -->
						<div class="flex-shrink-0 ml-3">
							{#if isExpanded}
								<ChevronUp class="w-5 h-5 text-slate-400" />
							{:else}
								<ChevronDown class="w-5 h-5 text-slate-400" />
							{/if}
						</div>
					</button>

					<!-- Expanded Summary Content -->
					{#if isExpanded}
						<div class="px-4 pb-4 bg-slate-50 dark:bg-slate-800/50">
							<div class="prose prose-sm dark:prose-invert max-w-none">
								<MarkdownContent content={summary} />
							</div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</div>
{/if}
