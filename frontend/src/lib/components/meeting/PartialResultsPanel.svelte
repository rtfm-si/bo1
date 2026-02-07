<script lang="ts">
	import { Copy, Check, FileText } from 'lucide-svelte';
	import { SvelteMap } from 'svelte/reactivity';
	import { Button } from '$lib/components/ui';
	import SubProblemStatusBadge from './SubProblemStatusBadge.svelte';
	import type { SubProblemResult } from './MeetingError.svelte';
	import {
		Accordion,
		AccordionItem,
		AccordionTrigger,
		AccordionContent,
	} from '$lib/components/ui/shadcn/accordion';

	interface Props {
		results: SubProblemResult[];
		totalSubProblems?: number;
	}

	let { results, totalSubProblems = 0 }: Props = $props();

	// Track copy states per item
	let copiedStates = new SvelteMap<string, boolean>();

	const completedResults = $derived(
		results.filter(r => r.status === 'complete' && r.synthesis)
	);

	const total = $derived(totalSubProblems || results.length);

	async function copyToClipboard(id: string, text: string) {
		try {
			await navigator.clipboard.writeText(text);
			copiedStates.set(id, true);

			// Reset after 2 seconds
			setTimeout(() => {
				copiedStates.set(id, false);
			}, 2000);
		} catch {
			console.error('Failed to copy to clipboard');
		}
	}

	function truncateSynthesis(text: string, maxLength = 200): string {
		if (text.length <= maxLength) return text;
		return text.slice(0, maxLength).trim() + '...';
	}
</script>

<div class="bg-white dark:bg-neutral-800 rounded-xl border border-neutral-200 dark:border-neutral-700 shadow-sm overflow-hidden">
	<!-- Header -->
	<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/50">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-3">
				<div class="w-10 h-10 rounded-full bg-success-100 dark:bg-success-900/40 flex items-center justify-center">
					<FileText size={20} class="text-success-600 dark:text-success-400" />
				</div>
				<div>
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">
						Partial Results Available
					</h3>
					<p class="text-sm text-neutral-600 dark:text-neutral-400">
						{completedResults.length} of {total} focus areas completed
					</p>
				</div>
			</div>

			<!-- Progress indicator -->
			<div class="flex items-center gap-2">
				<div class="w-24 h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
					<div
						class="h-full bg-success-500 dark:bg-success-400 rounded-full transition-all duration-300"
						style="width: {(completedResults.length / total) * 100}%"
					></div>
				</div>
				<span class="text-sm font-medium text-neutral-600 dark:text-neutral-400">
					{Math.round((completedResults.length / total) * 100)}%
				</span>
			</div>
		</div>
	</div>

	<!-- Sub-problem Results Accordion -->
	<Accordion type="multiple" class="divide-y divide-neutral-200 dark:divide-neutral-700">
		{#each results as result (result.id)}
			{@const isComplete = result.status === 'complete' && result.synthesis}
			{@const isCopied = copiedStates.get(result.id) || false}

			<AccordionItem value={result.id} class="border-b-0" disabled={!isComplete}>
				<AccordionTrigger
					class="px-6 py-4 hover:no-underline {isComplete
						? 'hover:bg-neutral-50 dark:hover:bg-neutral-700/50'
						: 'opacity-75 cursor-default'}"
					disabled={!isComplete}
				>
					<div class="flex items-center gap-3 min-w-0 flex-1">
						<div class="min-w-0 flex-1">
							<p class="font-medium text-neutral-900 dark:text-white truncate text-left">
								{result.goal}
							</p>
						</div>
					</div>
					<div class="flex items-center gap-3 flex-shrink-0 ml-3">
						<SubProblemStatusBadge status={result.status} />
					</div>
				</AccordionTrigger>
				{#if isComplete}
					<AccordionContent class="px-6">
						<div class="ml-0 bg-neutral-50 dark:bg-neutral-900/50 rounded-lg p-4">
							<!-- Synthesis Content -->
							<div class="prose prose-sm dark:prose-invert max-w-none">
								<p class="text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
									{result.synthesis}
								</p>
							</div>

							<!-- Copy Button -->
							<div class="mt-4 flex justify-end">
								<Button
									variant="ghost"
									size="sm"
									onclick={() => copyToClipboard(result.id, result.synthesis)}
								>
									{#if isCopied}
										<Check size={16} class="text-success-600" />
										<span class="text-success-600">Copied</span>
									{:else}
										<Copy size={16} />
										<span>Copy Synthesis</span>
									{/if}
								</Button>
							</div>
						</div>
					</AccordionContent>
				{/if}
			</AccordionItem>
		{/each}
	</Accordion>
</div>
