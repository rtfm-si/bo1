<script lang="ts">
	/**
	 * ReplanningSuggestionModal - Modal for creating a new meeting to replan a failed action
	 * Pre-fills context from the cancelled action
	 */

	import { AlertCircle, Loader2, X, ArrowRight } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface RelatedAction {
		id: string;
		title: string;
		status: string;
	}

	interface Props {
		open?: boolean;
		actionTitle?: string;
		problemStatement?: string;
		failureCategory?: string;
		failureReason?: string;
		relatedActions?: RelatedAction[];
		isSubmitting?: boolean;
		error?: string | null;
		oncancel?: () => void;
		onsubmit?: (problemStatement: string) => void;
	}

	let {
		open = $bindable(false),
		actionTitle = '',
		problemStatement = '',
		failureCategory = 'unknown',
		failureReason = '',
		relatedActions = [],
		isSubmitting = false,
		error = null,
		oncancel,
		onsubmit
	}: Props = $props();

	let useOriginalProblem = $state(true);
	let refinedProblem = $state('');

	// Sync refinedProblem when problemStatement prop changes
	$effect(() => {
		refinedProblem = problemStatement;
	});

	function handleClose() {
		if (!isSubmitting) {
			oncancel?.();
		}
	}

	function handleSubmit() {
		const problem = useOriginalProblem ? problemStatement : refinedProblem.trim();
		if (problem && onsubmit) {
			onsubmit(problem);
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && !isSubmitting) {
			handleClose();
		}
		if (e.key === 'Enter' && e.ctrlKey) {
			const problem = useOriginalProblem ? problemStatement : refinedProblem.trim();
			if (problem) {
				handleSubmit();
			}
		}
	}

	function getCategoryLabel(category: string): string {
		const labels: Record<string, string> = {
			blocker: 'Blocker',
			scope_creep: 'Scope Change',
			dependency: 'Dependency Issue',
			unknown: 'Unknown Reason'
		};
		return labels[category] || 'Unknown';
	}
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="fixed inset-0 z-50 flex items-center justify-center" onkeydown={handleKeydown}>
		<!-- Backdrop -->
		<button
			type="button"
			class="absolute inset-0 bg-black/50 backdrop-blur-sm"
			onclick={handleClose}
			disabled={isSubmitting}
			aria-label="Close modal"
		></button>

		<!-- Modal Content -->
		<div
			class="relative bg-white dark:bg-neutral-900 rounded-xl shadow-xl max-w-2xl w-full mx-4 overflow-hidden"
			role="dialog"
			aria-modal="true"
			aria-labelledby="replan-modal-title"
		>
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3">
					<div class="p-2 rounded-lg bg-brand-100 dark:bg-brand-900/30">
						<AlertCircle class="w-5 h-5 text-brand-600 dark:text-brand-400" />
					</div>
					<div>
						<h3 id="replan-modal-title" class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
							Replan: {actionTitle}
						</h3>
						<p class="text-sm text-neutral-500 dark:text-neutral-400">Create a new meeting to address what went wrong</p>
					</div>
				</div>
				<button
					onclick={handleClose}
					disabled={isSubmitting}
					class="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors disabled:opacity-50"
					aria-label="Close"
				>
					<X class="w-5 h-5 text-neutral-500" />
				</button>
			</div>

			<!-- Body -->
			<div class="px-6 py-4 max-h-[60vh] overflow-y-auto">
				<!-- Failure Context -->
				<div class="mb-6 p-4 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-start gap-3">
						<div class="flex-1">
							<div class="flex items-center gap-2 mb-2">
								<span class="text-xs font-semibold px-2 py-1 rounded bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300">
									{getCategoryLabel(failureCategory)}
								</span>
							</div>
							{#if failureReason}
								<p class="text-sm text-neutral-700 dark:text-neutral-300">{failureReason}</p>
							{/if}
						</div>
					</div>
				</div>

				<!-- Problem Statement -->
				<div class="mb-6">
					<label class="block mb-3">
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5 block">
							Problem Statement for New Meeting
						</span>
						<div class="flex items-center gap-2 mb-3">
							<input
								type="radio"
								id="use-original"
								bind:group={useOriginalProblem}
								value={true}
								disabled={isSubmitting}
								class="w-4 h-4"
							/>
							<label for="use-original" class="text-sm text-neutral-600 dark:text-neutral-400">
								Use original problem statement
							</label>
						</div>
						{#if useOriginalProblem && problemStatement}
							<div class="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-sm text-blue-900 dark:text-blue-300">
								{problemStatement}
							</div>
						{/if}
					</label>

					<label class="block mb-3">
						<div class="flex items-center gap-2 mb-3">
							<input
								type="radio"
								id="refine-problem"
								bind:group={useOriginalProblem}
								value={false}
								disabled={isSubmitting}
								class="w-4 h-4"
							/>
							<label for="refine-problem" class="text-sm text-neutral-600 dark:text-neutral-400">
								Refine problem statement
							</label>
						</div>
						{#if !useOriginalProblem}
							<textarea
								bind:value={refinedProblem}
								placeholder="Describe the refined problem to address..."
								rows="3"
								disabled={isSubmitting}
								class="w-full px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none disabled:opacity-50"
							></textarea>
						{/if}
					</label>
				</div>

				<!-- Related Actions Info -->
				{#if relatedActions.length > 0}
					<div class="mb-6">
						<h4 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
							Related Actions From This Problem
						</h4>
						<div class="space-y-2 max-h-40 overflow-y-auto">
							{#each relatedActions.slice(0, 5) as action (action.id)}
								<div class="flex items-start gap-2 p-2 rounded text-sm bg-neutral-50 dark:bg-neutral-800/50">
									<div class="flex-1">
										<div class="font-medium text-neutral-900 dark:text-neutral-100">{action.title}</div>
										<div class="text-xs text-neutral-500 dark:text-neutral-400 capitalize">Status: {action.status}</div>
									</div>
								</div>
							{/each}
							{#if relatedActions.length > 5}
								<div class="text-xs text-neutral-500 dark:text-neutral-400 px-2">
									+{relatedActions.length - 5} more related actions
								</div>
							{/if}
						</div>
						<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-2">
							These actions may be affected by or dependent on the replanning.
						</p>
					</div>
				{/if}

				{#if error}
					<div class="mb-4 p-3 rounded-lg bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800">
						<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-end gap-3 px-6 py-4 bg-neutral-50 dark:bg-neutral-800/50 border-t border-neutral-200 dark:border-neutral-700">
				<Button variant="ghost" onclick={handleClose} disabled={isSubmitting}>
					Cancel
				</Button>
				<Button
					variant="brand"
					onclick={handleSubmit}
					disabled={isSubmitting || !(useOriginalProblem ? problemStatement : refinedProblem.trim())}
				>
					{#if isSubmitting}
						<Loader2 class="w-4 h-4 mr-2 animate-spin" />
						Creating Meeting...
					{:else}
						<ArrowRight class="w-4 h-4 mr-2" />
						Create Meeting
					{/if}
				</Button>
			</div>
		</div>
	</div>
{/if}
