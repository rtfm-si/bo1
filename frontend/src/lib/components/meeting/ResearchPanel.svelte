<script lang="ts">
	/**
	 * ResearchPanel Component (P2-006)
	 * Displays research results in a collapsible accordion format
	 * Shows query, AI summary, sources (clickable links), and metadata
	 */
	import { ChevronDown, ChevronUp, ExternalLink, Search } from 'lucide-svelte';
	import type { ResearchResult } from '$lib/api/sse-events';

	interface Props {
		researchResults: ResearchResult[];
		subProblemGoal?: string;
	}

	let { researchResults, subProblemGoal }: Props = $props();

	// Track which research items are expanded
	let expandedResearch = $state<Set<number>>(new Set());

	function toggleResearch(index: number) {
		if (expandedResearch.has(index)) {
			expandedResearch.delete(index);
		} else {
			expandedResearch.add(index);
		}
		// Trigger reactivity
		expandedResearch = new Set(expandedResearch);
	}

	const hasResults = $derived(researchResults && researchResults.length > 0);
</script>

{#if hasResults}
	<div
		class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden"
	>
		<!-- Header -->
		<div class="border-b border-slate-200 dark:border-slate-700 p-4">
			<div class="flex items-center gap-2">
				<Search class="w-5 h-5 text-blue-600 dark:text-blue-400" />
				<h3 class="text-lg font-semibold text-slate-900 dark:text-white">Research Results</h3>
			</div>
			{#if subProblemGoal}
				<p class="text-sm text-slate-600 dark:text-slate-400 mt-1">{subProblemGoal}</p>
			{/if}
		</div>

		<!-- Research Results Accordion -->
		<div class="divide-y divide-slate-200 dark:divide-slate-700">
			{#each researchResults as result, index}
				{@const isExpanded = expandedResearch.has(index)}
				<div class="border-b border-slate-200 dark:border-slate-700 last:border-b-0">
					<button
						type="button"
						onclick={() => toggleResearch(index)}
						class="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
					>
						<div class="flex items-center gap-3 flex-1 text-left">
							<!-- Search Icon -->
							<div
								class="flex-shrink-0 w-10 h-10 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full flex items-center justify-center"
							>
								<Search class="w-5 h-5" />
							</div>
							<!-- Query Text -->
							<div class="flex-1 min-w-0">
								<h4 class="font-medium text-slate-900 dark:text-white line-clamp-2">
									{result.query}
								</h4>
								<div class="flex items-center gap-2 mt-1 flex-wrap">
									<!-- Badges -->
									{#if result.cached}
										<span
											class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
										>
											Cached
										</span>
									{/if}
									<span
										class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
									>
										{result.depth === 'deep' ? 'Deep Research' : 'Basic Research'}
									</span>
									{#if result.proactive}
										<span
											class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300"
										>
											Proactive
										</span>
									{/if}
									<span class="text-xs text-slate-500 dark:text-slate-400">
										Round {result.round}
									</span>
								</div>
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

					<!-- Expanded Research Content -->
					{#if isExpanded}
						<div class="px-4 pb-4 bg-slate-50 dark:bg-slate-800/50">
							<!-- AI Summary -->
							<div class="prose prose-sm dark:prose-invert max-w-none mb-4">
								<h5 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
									Summary
								</h5>
								<p class="text-slate-700 dark:text-slate-300 leading-relaxed">
									{result.summary}
								</p>
							</div>

							<!-- Sources -->
							{#if result.sources && result.sources.length > 0}
								<div>
									<h5 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
										Sources ({result.sources.length})
									</h5>
									<ul class="space-y-1">
										{#each result.sources as source}
											<li>
												<a
													href={source}
													target="_blank"
													rel="noopener noreferrer"
													class="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
												>
													<ExternalLink class="w-3 h-3" />
													{source}
												</a>
											</li>
										{/each}
									</ul>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</div>
{/if}
