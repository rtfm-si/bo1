<script lang="ts">
	import type { SavedAnalysis } from '$lib/api/admin';

	interface Props {
		analyses: SavedAnalysis[];
		onRun: (id: string) => void;
		onDelete: (id: string) => void;
		onClose: () => void;
	}

	let { analyses, onRun, onDelete, onClose }: Props = $props();
</script>

<div
	class="fixed inset-y-0 right-0 w-80 bg-white dark:bg-neutral-800 border-l border-neutral-200 dark:border-neutral-700 shadow-xl z-50 flex flex-col"
>
	<!-- Header -->
	<div class="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
		<h3 class="text-sm font-semibold text-neutral-900 dark:text-white">Saved Analyses</h3>
		<button
			class="p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
			onclick={onClose}
		>
			<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
			</svg>
		</button>
	</div>

	<!-- List -->
	<div class="flex-1 overflow-y-auto">
		{#if analyses.length === 0}
			<div class="p-4 text-center text-sm text-neutral-400 dark:text-neutral-500">
				No saved analyses yet. Save an analysis from the chat to re-run it later.
			</div>
		{:else}
			{#each analyses as analysis (analysis.id)}
				<div
					class="px-4 py-3 border-b border-neutral-100 dark:border-neutral-700/50 hover:bg-neutral-50 dark:hover:bg-neutral-750 transition-colors"
				>
					<p class="text-sm font-medium text-neutral-800 dark:text-neutral-200 truncate">
						{analysis.title}
					</p>
					{#if analysis.description}
						<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 line-clamp-2">
							{analysis.description}
						</p>
					{/if}
					<p class="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
						{analysis.original_question}
					</p>
					{#if analysis.last_run_at}
						<p class="text-[10px] text-neutral-400 mt-0.5">
							Last run: {new Date(analysis.last_run_at).toLocaleDateString()}
						</p>
					{/if}
					<div class="flex gap-2 mt-2">
						<button
							class="text-xs px-2 py-1 rounded bg-accent-50 dark:bg-accent-900/20 text-accent-600 dark:text-accent-400 hover:bg-accent-100 dark:hover:bg-accent-900/40 transition-colors"
							onclick={() => onRun(analysis.id)}
						>
							Re-run
						</button>
						<button
							class="text-xs px-2 py-1 rounded text-error-500 hover:bg-error-50 dark:hover:bg-error-900/20 transition-colors"
							onclick={() => onDelete(analysis.id)}
						>
							Delete
						</button>
					</div>
				</div>
			{/each}
		{/if}
	</div>
</div>
