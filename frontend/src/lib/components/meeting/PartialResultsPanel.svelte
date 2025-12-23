<script lang="ts">
	import { ChevronDown, ChevronRight, Copy, Check, FileText } from 'lucide-svelte';
	import { SvelteSet, SvelteMap } from 'svelte/reactivity';
	import { Button } from '$lib/components/ui';
	import SubProblemStatusBadge from './SubProblemStatusBadge.svelte';
	import type { SubProblemResult } from './MeetingError.svelte';

	interface Props {
		results: SubProblemResult[];
		totalSubProblems?: number;
	}

	let { results, totalSubProblems = 0 }: Props = $props();

	// Track expanded accordion items
	let expandedItems = new SvelteSet<string>();

	// Track copy states per item
	let copiedStates = new SvelteMap<string, boolean>();

	const completedResults = $derived(
		results.filter(r => r.status === 'complete' && r.synthesis)
	);

	const total = $derived(totalSubProblems || results.length);

	function toggleItem(id: string) {
		if (expandedItems.has(id)) {
			expandedItems.delete(id);
		} else {
			expandedItems.add(id);
		}
	}

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

<div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
	<!-- Header -->
	<div class="px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-3">
				<div class="w-10 h-10 rounded-full bg-success-100 dark:bg-success-900/40 flex items-center justify-center">
					<FileText size={20} class="text-success-600 dark:text-success-400" />
				</div>
				<div>
					<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
						Partial Results Available
					</h3>
					<p class="text-sm text-slate-600 dark:text-slate-400">
						{completedResults.length} of {total} focus areas completed
					</p>
				</div>
			</div>

			<!-- Progress indicator -->
			<div class="flex items-center gap-2">
				<div class="w-24 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
					<div
						class="h-full bg-success-500 dark:bg-success-400 rounded-full transition-all duration-300"
						style="width: {(completedResults.length / total) * 100}%"
					></div>
				</div>
				<span class="text-sm font-medium text-slate-600 dark:text-slate-400">
					{Math.round((completedResults.length / total) * 100)}%
				</span>
			</div>
		</div>
	</div>

	<!-- Sub-problem Results Accordion -->
	<div class="divide-y divide-slate-200 dark:divide-slate-700">
		{#each results as result (result.id)}
			{@const isExpanded = expandedItems.has(result.id)}
			{@const isCopied = copiedStates.get(result.id) || false}
			{@const isComplete = result.status === 'complete' && result.synthesis}

			<div class="group">
				<!-- Accordion Header -->
				<button
					onclick={() => isComplete && toggleItem(result.id)}
					class="w-full px-6 py-4 flex items-center justify-between text-left transition-colors
						{isComplete
							? 'hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer'
							: 'cursor-default opacity-75'
						}"
					disabled={!isComplete}
					aria-expanded={isExpanded}
					aria-controls="content-{result.id}"
				>
					<div class="flex items-center gap-3 min-w-0 flex-1">
						{#if isComplete}
							<span class="text-slate-400 dark:text-slate-500 transition-transform {isExpanded ? 'rotate-0' : '-rotate-90'}">
								<ChevronDown size={20} />
							</span>
						{:else}
							<span class="text-slate-300 dark:text-slate-600">
								<ChevronRight size={20} />
							</span>
						{/if}

						<div class="min-w-0 flex-1">
							<p class="font-medium text-slate-900 dark:text-white truncate">
								{result.goal}
							</p>
							{#if isComplete && !isExpanded}
								<p class="text-sm text-slate-500 dark:text-slate-400 truncate mt-0.5">
									{truncateSynthesis(result.synthesis)}
								</p>
							{/if}
						</div>
					</div>

					<div class="flex items-center gap-3 flex-shrink-0 ml-3">
						<SubProblemStatusBadge status={result.status} />
					</div>
				</button>

				<!-- Accordion Content -->
				{#if isExpanded && isComplete}
					<div
						id="content-{result.id}"
						class="px-6 pb-4 pt-0"
					>
						<div class="ml-8 bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
							<!-- Synthesis Content -->
							<div class="prose prose-sm dark:prose-invert max-w-none">
								<p class="text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
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
					</div>
				{/if}
			</div>
		{/each}
	</div>
</div>
