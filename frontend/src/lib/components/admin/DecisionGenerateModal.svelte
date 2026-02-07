<script lang="ts">
	/**
	 * DecisionGenerateModal - Generate decision content using AI
	 */
	import { Button, Alert } from '$lib/components/ui';
	import { X, Sparkles, Plus } from 'lucide-svelte';
	import {
		adminApi,
		type Decision,
		type DecisionCategory,
		DECISION_CATEGORIES
	} from '$lib/api/admin';

	interface Props {
		onclose: () => void;
		ongenerated: (decision: Decision) => void;
	}

	let { onclose, ongenerated }: Props = $props();

	// Form state
	let question = $state('');
	let category = $state<DecisionCategory>('hiring');
	let stage = $state('');
	let constraints = $state<string[]>([]);
	let situation = $state('');
	let newConstraint = $state('');

	let isGenerating = $state(false);
	let error = $state<string | null>(null);

	function addConstraint() {
		if (newConstraint.trim()) {
			constraints = [...constraints, newConstraint.trim()];
			newConstraint = '';
		}
	}

	function removeConstraint(index: number) {
		constraints = constraints.filter((_, i) => i !== index);
	}

	function validate(): string | null {
		if (!question.trim()) return 'Decision question is required';
		if (question.length < 10) return 'Question must be at least 10 characters';
		if (!category) return 'Category is required';
		return null;
	}

	async function handleGenerate() {
		error = null;

		const validationError = validate();
		if (validationError) {
			error = validationError;
			return;
		}

		isGenerating = true;
		try {
			const decision = await adminApi.generateDecision({
				question: question.trim(),
				category,
				founder_context: {
					stage: stage.trim() || undefined,
					constraints: constraints.length > 0 ? constraints : undefined,
					situation: situation.trim() || undefined
				}
			});
			ongenerated(decision);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to generate decision';
		} finally {
			isGenerating = false;
		}
	}
</script>

<div
	class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
	role="dialog"
	aria-modal="true"
>
	<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-xl w-full max-w-2xl">
		<!-- Header -->
		<div
			class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700"
		>
			<div class="flex items-center gap-2">
				<Sparkles class="w-5 h-5 text-brand-600 dark:text-brand-400" />
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Generate Decision</h2>
			</div>
			<button
				onclick={onclose}
				class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
				aria-label="Close"
			>
				<X class="w-5 h-5 text-neutral-500" />
			</button>
		</div>

		<!-- Content -->
		<div class="p-6 space-y-4">
			{#if error}
				<Alert variant="error">{error}</Alert>
			{/if}

			<div class="bg-warning-50 dark:bg-warning-900/20 rounded-lg p-4 text-sm text-warning-700 dark:text-warning-400">
				<p>
					AI will generate expert perspectives and a synthesis for this decision question.
					Content is saved as draft for review before publishing.
				</p>
			</div>

			<!-- Question -->
			<div>
				<label
					for="question"
					class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
				>
					Decision Question *
				</label>
				<input
					id="question"
					type="text"
					bind:value={question}
					placeholder="Should I hire my first engineer or use contractors?"
					class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
				/>
			</div>

			<!-- Category -->
			<div>
				<label
					for="category"
					class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
				>
					Category *
				</label>
				<select
					id="category"
					bind:value={category}
					class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
				>
					{#each DECISION_CATEGORIES as cat}
						<option value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</option>
					{/each}
				</select>
			</div>

			<!-- Founder Context -->
			<div class="border-t border-neutral-200 dark:border-neutral-700 pt-4">
				<h3 class="text-sm font-medium text-neutral-900 dark:text-white mb-3">
					Founder Context (for more targeted advice)
				</h3>

				<div class="space-y-3">
					<div>
						<label for="stage" class="block text-sm text-neutral-600 dark:text-neutral-400 mb-1">
							Stage
						</label>
						<input
							id="stage"
							type="text"
							bind:value={stage}
							placeholder="£50-200k ARR"
							class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
						/>
					</div>

					<div>
						<label class="block text-sm text-neutral-600 dark:text-neutral-400 mb-1">
							Constraints
						</label>
						<div class="flex gap-2 mb-2">
							<input
								type="text"
								bind:value={newConstraint}
								placeholder="Add a constraint..."
								class="flex-1 px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
								onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addConstraint())}
							/>
							<Button type="button" variant="outline" size="sm" onclick={addConstraint}>
								<Plus class="w-4 h-4" />
							</Button>
						</div>
						{#if constraints.length > 0}
							<div class="flex flex-wrap gap-2">
								{#each constraints as constraint, i}
									<span
										class="inline-flex items-center gap-1 px-2 py-1 rounded bg-neutral-100 dark:bg-neutral-700 text-sm text-neutral-700 dark:text-neutral-300"
									>
										{constraint}
										<button
											type="button"
											onclick={() => removeConstraint(i)}
											class="hover:text-error-500"
										>
											<X class="w-3 h-3" />
										</button>
									</span>
								{/each}
							</div>
						{/if}
					</div>

					<div>
						<label
							for="situation"
							class="block text-sm text-neutral-600 dark:text-neutral-400 mb-1"
						>
							Situation
						</label>
						<textarea
							id="situation"
							bind:value={situation}
							placeholder="Paying contractors, considering hiring first FTE"
							rows="2"
							class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
						></textarea>
					</div>
				</div>
			</div>
		</div>

		<!-- Footer -->
		<div
			class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-200 dark:border-neutral-700"
		>
			<Button variant="outline" onclick={onclose} disabled={isGenerating}>Cancel</Button>
			<Button onclick={handleGenerate} disabled={isGenerating}>
				{#if isGenerating}
					<span class="animate-pulse">Generating...</span>
				{:else}
					<Sparkles class="w-4 h-4 mr-1.5" />
					Generate Decision
				{/if}
			</Button>
		</div>
	</div>
</div>
