<script lang="ts">
	/**
	 * ResearchPanel Component (P2-006)
	 * Displays research results in a collapsible accordion format
	 * Shows query, AI summary, sources (clickable links), and metadata
	 */
	import { ExternalLink, Search } from 'lucide-svelte';
	import type { ResearchResult } from '$lib/api/sse-events';
	import {
		Accordion,
		AccordionItem,
		AccordionTrigger,
		AccordionContent,
	} from '$lib/components/ui/shadcn/accordion';

	interface Props {
		researchResults: ResearchResult[];
		subProblemGoal?: string;
	}

	let { researchResults, subProblemGoal }: Props = $props();

	const hasResults = $derived(researchResults && researchResults.length > 0);
</script>

{#if hasResults}
	<div
		class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 overflow-hidden"
	>
		<!-- Header -->
		<div class="border-b border-neutral-200 dark:border-neutral-700 p-4">
			<div class="flex items-center gap-2">
				<Search class="w-5 h-5 text-info-600 dark:text-info-400" />
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Research Results</h3>
			</div>
			{#if subProblemGoal}
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{subProblemGoal}</p>
			{/if}
		</div>

		<!-- Research Results Accordion -->
		<Accordion type="multiple" class="divide-y divide-neutral-200 dark:divide-neutral-700">
			{#each researchResults as result, index (index)}
				<AccordionItem value={String(index)} class="border-b-0">
					<AccordionTrigger class="px-4 py-3 hover:bg-neutral-50 dark:hover:bg-neutral-700/50 hover:no-underline">
						<div class="flex items-center gap-3 flex-1 text-left">
							<!-- Search Icon -->
							<div
								class="flex-shrink-0 w-10 h-10 bg-info-100 dark:bg-info-900/30 text-info-700 dark:text-info-300 rounded-full flex items-center justify-center"
							>
								<Search class="w-5 h-5" />
							</div>
							<!-- Query Text -->
							<div class="flex-1 min-w-0">
								<h4 class="font-medium text-neutral-900 dark:text-white line-clamp-2">
									{result.query}
								</h4>
								<div class="flex items-center gap-2 mt-1 flex-wrap">
									{#if result.cached}
										<span
											class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-300"
										>
											Cached
										</span>
									{/if}
									<span
										class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-info-100 text-info-800 dark:bg-info-900/30 dark:text-info-300"
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
									<span class="text-xs text-neutral-500 dark:text-neutral-400">
										Round {result.round}
									</span>
								</div>
							</div>
						</div>
					</AccordionTrigger>
					<AccordionContent class="px-4 bg-neutral-50 dark:bg-neutral-800/50">
						<!-- AI Summary -->
						<div class="prose prose-sm dark:prose-invert max-w-none mb-4">
							<h5 class="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
								Summary
							</h5>
							<p class="text-neutral-700 dark:text-neutral-300 leading-relaxed">
								{result.summary}
							</p>
						</div>

						<!-- Sources -->
						{#if result.sources && result.sources.length > 0}
							<div>
								<h5 class="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
									Sources ({result.sources.length})
								</h5>
								<ul class="space-y-1">
									{#each result.sources as source}
										<li>
											<a
												href={source}
												target="_blank"
												rel="noopener noreferrer"
												class="inline-flex items-center gap-1 text-sm text-info-600 dark:text-info-400 hover:underline"
											>
												<ExternalLink class="w-3 h-3" />
												{source}
											</a>
										</li>
									{/each}
								</ul>
							</div>
						{/if}
					</AccordionContent>
				</AccordionItem>
			{/each}
		</Accordion>
	</div>
{/if}
