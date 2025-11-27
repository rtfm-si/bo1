<script lang="ts">
	/**
	 * SubProblemProgress Event Component
	 * Displays completion status for a sub-problem including synthesis/conclusion
	 */
	import type { SubProblemCompleteEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: SubProblemCompleteEvent;
	}

	let { event }: Props = $props();

	const formatDuration = (seconds: number): string => {
		const minutes = Math.floor(seconds / 60);
		const remainingSeconds = Math.round(seconds % 60);
		return `${minutes}m ${remainingSeconds}s`;
	};

	const formatCost = (cost: number): string => {
		return `$${cost.toFixed(4)}`;
	};

	// State for showing full synthesis
	let showFullSynthesis = $state(false);

	// Truncate synthesis if too long (show first 300 chars)
	const truncatedSynthesis = $derived(
		event.data.synthesis && event.data.synthesis.length > 300
			? event.data.synthesis.slice(0, 300) + '...'
			: event.data.synthesis
	);

	const hasSynthesis = $derived(event.data.synthesis && event.data.synthesis.length > 0);
	const isLongSynthesis = $derived(event.data.synthesis && event.data.synthesis.length > 300);
</script>

<div class="space-y-3">
	<div
		class="bg-gradient-to-r from-success-50 to-brand-50 dark:from-success-900/20 dark:to-brand-900/20 border border-success-200 dark:border-success-700 rounded-lg p-4"
	>
		<div class="flex items-start gap-3">
			<div
				class="flex-shrink-0 w-12 h-12 bg-success-500 dark:bg-success-600 text-white rounded-full flex items-center justify-center"
			>
				<svg
					class="w-6 h-6"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M5 13l4 4L19 7"
					/>
				</svg>
			</div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-2">
					<h3 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
						Sub-Problem Complete
					</h3>
					<Badge variant="success" size="sm">
						#{event.data.sub_problem_index + 1}
					</Badge>
				</div>

				<p class="text-sm text-neutral-700 dark:text-neutral-300 mb-3">
					{event.data.goal}
				</p>

				<!-- Synthesis/Conclusion -->
				{#if hasSynthesis}
					<div class="mb-4 p-3 bg-white/50 dark:bg-neutral-800/50 rounded-lg border border-success-100 dark:border-success-800">
						<h4 class="text-sm font-semibold text-success-800 dark:text-success-300 mb-2 flex items-center gap-1.5">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Conclusion
						</h4>
						<div class="text-sm text-neutral-700 dark:text-neutral-300 prose prose-sm dark:prose-invert max-w-none">
							{#if showFullSynthesis || !isLongSynthesis}
								{event.data.synthesis}
							{:else}
								{truncatedSynthesis}
							{/if}
						</div>
						{#if isLongSynthesis}
							<button
								type="button"
								class="mt-2 text-sm text-success-700 dark:text-success-400 hover:text-success-900 dark:hover:text-success-200 font-medium"
								onclick={() => showFullSynthesis = !showFullSynthesis}
							>
								{showFullSynthesis ? 'Show less' : 'Show more'}
							</button>
						{/if}
					</div>
				{/if}

				<!-- Metrics -->
				<div class="grid grid-cols-2 gap-3 text-sm">
					<div>
						<span class="text-neutral-600 dark:text-neutral-400">Duration:</span>
						<span class="font-semibold text-neutral-900 dark:text-neutral-100 ml-1">
							{formatDuration(event.data.duration_seconds)}
						</span>
					</div>
					<div>
						<span class="text-neutral-600 dark:text-neutral-400">Cost:</span>
						<span class="font-semibold text-neutral-900 dark:text-neutral-100 ml-1">
							{formatCost(event.data.cost)}
						</span>
					</div>
					<div>
						<span class="text-neutral-600 dark:text-neutral-400">Contributions:</span>
						<span class="font-semibold text-neutral-900 dark:text-neutral-100 ml-1">
							{event.data.contribution_count}
						</span>
					</div>
					<div>
						<span class="text-neutral-600 dark:text-neutral-400">Experts:</span>
						<span class="font-semibold text-neutral-900 dark:text-neutral-100 ml-1">
							{event.data.expert_panel.length}
						</span>
					</div>
				</div>

				<!-- Expert Panel -->
				<div class="mt-3 flex flex-wrap gap-1">
					{#each event.data.expert_panel as expert}
						<Badge variant="brand" size="sm">{expert}</Badge>
					{/each}
				</div>
			</div>
		</div>
	</div>
</div>
