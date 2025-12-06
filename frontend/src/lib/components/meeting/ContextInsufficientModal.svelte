<script lang="ts">
	/**
	 * Context Insufficient Modal - Option D+E Hybrid
	 *
	 * Shown when experts are struggling due to insufficient context.
	 * Gives user 3 choices:
	 * 1. Provide more context
	 * 2. Continue with best effort
	 * 3. End the meeting
	 */

	import { fade } from 'svelte/transition';
	import { AlertCircle, MessageSquarePlus, PlayCircle, XCircle } from 'lucide-svelte';
	import { env } from '$env/dynamic/public';
	import type { ContextInsufficientEvent } from '$lib/api/sse-events';

	interface Props {
		sessionId: string;
		eventData: ContextInsufficientEvent['data'];
		onChoiceMade: () => Promise<void>;
	}

	let { sessionId, eventData, onChoiceMade }: Props = $props();

	let additionalContext = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);
	let selectedChoice = $state<'provide_more' | 'continue' | 'end' | null>(null);

	async function submitChoice(choice: 'provide_more' | 'continue' | 'end') {
		isSubmitting = true;
		error = null;
		selectedChoice = choice;

		try {
			const body: { choice: string; additional_context?: string } = { choice };
			if (choice === 'provide_more' && additionalContext.trim()) {
				body.additional_context = additionalContext.trim();
			}

			const response = await fetch(
				`${env.PUBLIC_API_URL}/api/v1/sessions/${sessionId}/context-choice`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
					},
					credentials: 'include',
					body: JSON.stringify(body),
				}
			);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || `Failed to submit choice: ${response.statusText}`);
			}

			await onChoiceMade();
		} catch (err) {
			console.error('Failed to submit context choice:', err);
			error = err instanceof Error ? err.message : 'Failed to submit choice';
			selectedChoice = null;
		} finally {
			isSubmitting = false;
		}
	}

	const metaRatioPercent = $derived(Math.round(eventData.meta_ratio * 100));
</script>

<div
	class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
	transition:fade
>
	<div
		class="w-full max-w-2xl bg-white dark:bg-neutral-900 rounded-xl shadow-2xl overflow-hidden"
		role="dialog"
		aria-modal="true"
		aria-labelledby="context-modal-title"
	>
		<!-- Header -->
		<div class="bg-amber-50 dark:bg-amber-900/30 px-6 py-4 border-b border-amber-200 dark:border-amber-800">
			<div class="flex items-center gap-3">
				<AlertCircle class="w-6 h-6 text-amber-600 dark:text-amber-400 flex-shrink-0" />
				<div>
					<h2 id="context-modal-title" class="text-lg font-semibold text-amber-900 dark:text-amber-100">
						Experts Need More Context
					</h2>
					<p class="text-sm text-amber-700 dark:text-amber-300 mt-1">
						{metaRatioPercent}% of contributions indicate insufficient context for meaningful analysis
					</p>
				</div>
			</div>
		</div>

		<!-- Body -->
		<div class="px-6 py-4">
			{#if eventData.expert_questions && eventData.expert_questions.length > 0}
				<div class="mb-6">
					<h3 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
						Questions from the experts:
					</h3>
					<ul class="space-y-2">
						{#each eventData.expert_questions as question}
							<li class="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-400">
								<span class="text-amber-500 mt-0.5">•</span>
								<span>{question}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			<p class="text-sm text-slate-600 dark:text-slate-400 mb-6">
				{eventData.reason || 'The experts are having difficulty providing meaningful analysis with the available information.'}
			</p>

			<!-- Choices -->
			<div class="space-y-4">
				<!-- Option 1: Provide More Context -->
				<div
					class="border border-slate-200 dark:border-slate-700 rounded-lg p-4 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
				>
					<div class="flex items-start gap-3">
						<MessageSquarePlus class="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
						<div class="flex-1">
							<h4 class="font-medium text-slate-900 dark:text-white mb-1">
								Provide Additional Details
							</h4>
							<p class="text-sm text-slate-600 dark:text-slate-400 mb-3">
								Share more context to help the experts provide better recommendations.
							</p>
							<textarea
								bind:value={additionalContext}
								rows="3"
								placeholder="Add context that might help the experts... (budget, timeline, constraints, preferences, etc.)"
								class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
								disabled={isSubmitting}
							></textarea>
							<button
								onclick={() => submitChoice('provide_more')}
								disabled={isSubmitting || !additionalContext.trim()}
								class="mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center gap-2"
							>
								{#if isSubmitting && selectedChoice === 'provide_more'}
									<span
										class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
									></span>
									Submitting...
								{:else}
									Submit Additional Context
								{/if}
							</button>
						</div>
					</div>
				</div>

				<!-- Option 2: Continue Best Effort -->
				<div
					class="border border-slate-200 dark:border-slate-700 rounded-lg p-4 hover:border-green-300 dark:hover:border-green-600 transition-colors"
				>
					<div class="flex items-start gap-3">
						<PlayCircle class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
						<div class="flex-1">
							<h4 class="font-medium text-slate-900 dark:text-white mb-1">
								Continue with Available Information
							</h4>
							<p class="text-sm text-slate-600 dark:text-slate-400 mb-3">
								Experts will do their best with what's available. The final recommendation will include
								explicit assumptions and limitations.
							</p>
							<button
								onclick={() => submitChoice('continue')}
								disabled={isSubmitting}
								class="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
							>
								{#if isSubmitting && selectedChoice === 'continue'}
									<span
										class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
									></span>
									Continuing...
								{:else}
									Continue with Best Effort
								{/if}
							</button>
						</div>
					</div>
				</div>

				<!-- Option 3: End Meeting -->
				<div
					class="border border-slate-200 dark:border-slate-700 rounded-lg p-4 hover:border-red-300 dark:hover:border-red-600 transition-colors"
				>
					<div class="flex items-start gap-3">
						<XCircle class="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
						<div class="flex-1">
							<h4 class="font-medium text-slate-900 dark:text-white mb-1">
								End This Meeting
							</h4>
							<p class="text-sm text-slate-600 dark:text-slate-400 mb-3">
								Stop the meeting now. You can start a new meeting later with more information.
							</p>
							<button
								onclick={() => submitChoice('end')}
								disabled={isSubmitting}
								class="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
							>
								{#if isSubmitting && selectedChoice === 'end'}
									<span
										class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
									></span>
									Ending...
								{:else}
									End Meeting
								{/if}
							</button>
						</div>
					</div>
				</div>
			</div>

			{#if error}
				<div
					class="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
				>
					<p class="text-sm text-red-700 dark:text-red-300">{error}</p>
				</div>
			{/if}
		</div>

		<!-- Footer with timeout info -->
		<div class="px-6 py-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700">
			<p class="text-xs text-slate-500 dark:text-slate-400 text-center">
				The meeting is paused while waiting for your decision.
			</p>
		</div>
	</div>
</div>
