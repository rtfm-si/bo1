<script lang="ts">
	/**
	 * ExpertSummariesPanel Component (P2-004)
	 * Displays expert summaries in a collapsible accordion format
	 * Shows each expert's summary from the synthesis phase
	 */
	import type { Persona } from '$lib/api/sse-events';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import {
		Accordion,
		AccordionItem,
		AccordionTrigger,
		AccordionContent,
	} from '$lib/components/ui/shadcn/accordion';

	interface Props {
		expertSummaries: Record<string, string>;
		personas: Persona[];
		subProblemGoal?: string;
	}

	let { expertSummaries, personas, subProblemGoal }: Props = $props();

	function getPersona(code: string): Persona | undefined {
		return personas.find((p) => p.code === code);
	}

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
		class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 overflow-hidden"
	>
		<div class="border-b border-neutral-200 dark:border-neutral-700 p-4">
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
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Expert Summaries</h3>
			</div>
			{#if subProblemGoal}
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{subProblemGoal}</p>
			{/if}
		</div>

		<Accordion type="multiple" class="divide-y divide-neutral-200 dark:divide-neutral-700">
			{#each expertsWithSummaries as { code, summary, persona } (code)}
				<AccordionItem value={code} class="border-b-0">
					<AccordionTrigger class="px-4 py-3 hover:bg-neutral-50 dark:hover:bg-neutral-700/50 hover:no-underline">
						<div class="flex items-center gap-3 flex-1 text-left">
							<div
								class="flex-shrink-0 w-10 h-10 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full flex items-center justify-center font-semibold"
							>
								{persona?.display_name?.[0] || code[0].toUpperCase()}
							</div>
							<div class="flex-1 min-w-0">
								<h4 class="font-medium text-neutral-900 dark:text-white">
									{persona?.display_name || code}
								</h4>
								<p class="text-sm text-neutral-600 dark:text-neutral-400">
									{persona?.archetype || 'Expert'}
								</p>
							</div>
						</div>
					</AccordionTrigger>
					<AccordionContent class="px-4 bg-neutral-50 dark:bg-neutral-800/50">
						<div class="prose prose-sm dark:prose-invert max-w-none">
							<MarkdownContent content={summary} />
						</div>
					</AccordionContent>
				</AccordionItem>
			{/each}
		</Accordion>
	</div>
{/if}
