<script lang="ts">
	import { fade } from 'svelte/transition';
	import { AlertCircle } from 'lucide-svelte';
	import { env } from '$env/dynamic/public';
	import { apiClient, getCsrfToken } from '$lib/api/client';

	interface ClarificationQuestion {
		question: string;
		reason?: string;
		priority?: string;
	}

	interface Props {
		sessionId: string;
		questions: ClarificationQuestion[];
		reason?: string;
		onSubmitted: () => Promise<void>;
	}

	let { sessionId, questions, reason, onSubmitted }: Props = $props();

	let answers = $state<Record<string, string>>({});
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);
	let firstInputRef: HTMLTextAreaElement | undefined = $state(undefined);

	// Auto-focus first input on mount
	$effect(() => {
		if (firstInputRef) {
			setTimeout(() => firstInputRef?.focus(), 150);
		}
	});

	async function handleSubmit() {
		isSubmitting = true;
		error = null;

		try {
			const csrfToken = getCsrfToken();
			const headers: HeadersInit = {
				'Content-Type': 'application/json',
			};
			if (csrfToken) {
				headers['X-CSRF-Token'] = csrfToken;
			}

			const response = await fetch(
				`${env.PUBLIC_API_URL}/api/v1/sessions/${sessionId}/clarifications`,
				{
					method: 'POST',
					headers,
					credentials: 'include',
					body: JSON.stringify({
						answers,
					}),
				}
			);

			if (!response.ok) {
				throw new Error(`Failed to submit clarifications: ${response.statusText}`);
			}

			// Resume the session after clarifications are submitted
			await apiClient.resumeDeliberation(sessionId);
			await onSubmitted();
		} catch (err) {
			console.error('Failed to submit clarifications:', err);
			error = err instanceof Error ? err.message : 'Failed to submit answers';
		} finally {
			isSubmitting = false;
		}
	}

	async function handleSkip() {
		isSubmitting = true;
		error = null;

		try {
			const csrfToken = getCsrfToken();
			const headers: HeadersInit = {
				'Content-Type': 'application/json',
			};
			if (csrfToken) {
				headers['X-CSRF-Token'] = csrfToken;
			}

			const response = await fetch(
				`${env.PUBLIC_API_URL}/api/v1/sessions/${sessionId}/clarifications`,
				{
					method: 'POST',
					headers,
					credentials: 'include',
					body: JSON.stringify({
						answers: {},
						skip: true,
					}),
				}
			);

			if (!response.ok) {
				throw new Error(`Failed to skip clarifications: ${response.statusText}`);
			}

			// Clear answers and resume
			answers = {};
			await apiClient.resumeDeliberation(sessionId);
			await onSubmitted();
		} catch (err) {
			console.error('Failed to skip clarifications:', err);
			error = err instanceof Error ? err.message : 'Failed to skip questions';
		} finally {
			isSubmitting = false;
		}
	}
</script>

<div
	class="mb-6 bg-amber-50 dark:bg-amber-900/20 border-2 border-amber-300 dark:border-amber-700 rounded-lg p-6 shadow-lg animate-attention-pulse"
	transition:fade
>
	<div class="flex items-start gap-4">
		<div class="flex-shrink-0">
			<AlertCircle class="w-6 h-6 text-amber-600 dark:text-amber-400" />
		</div>
		<div class="flex-1 min-w-0">
			<h3 class="text-lg font-semibold text-amber-900 dark:text-amber-100 mb-2">
				Before We Begin: A Few Quick Questions
			</h3>
			<p class="text-sm text-amber-700 dark:text-amber-300 mb-4">
				{reason || 'Answering these questions will help our experts provide better recommendations.'}
			</p>

			<div class="space-y-4">
				{#each questions as question, index}
					<div
						class="bg-white dark:bg-slate-800 rounded-lg p-4 border border-amber-100 dark:border-amber-800"
					>
						<label
							for="clarification-{index}"
							class="block text-sm font-medium text-slate-900 dark:text-white mb-2"
						>
							{question.question}
							{#if question.priority === 'CRITICAL'}
								<span
									class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
								>
									Critical
								</span>
							{/if}
						</label>
						{#if question.reason}
							<p class="text-xs text-slate-500 dark:text-slate-400 mb-2">{question.reason}</p>
						{/if}
						{#if index === 0}
						<textarea
							id="clarification-{index}"
							rows="2"
							bind:value={answers[question.question]}
							bind:this={firstInputRef}
							placeholder="Your answer..."
							class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
						></textarea>
					{:else}
						<textarea
							id="clarification-{index}"
							rows="2"
							bind:value={answers[question.question]}
							placeholder="Your answer..."
							class="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
						></textarea>
					{/if}
					</div>
				{/each}
			</div>

			{#if error}
				<div
					class="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
				>
					<p class="text-sm text-red-700 dark:text-red-300">{error}</p>
				</div>
			{/if}

			<div class="mt-6 flex items-center gap-4">
				<button
					onclick={handleSubmit}
					disabled={isSubmitting}
					class="px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-amber-400 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
				>
					{#if isSubmitting}
						<span
							class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
						></span>
						Submitting...
					{:else}
						Continue with Answers
					{/if}
				</button>
				<button
					onclick={handleSkip}
					disabled={isSubmitting}
					class="px-4 py-2 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white font-medium transition-colors"
				>
					Skip Questions
				</button>
			</div>
		</div>
	</div>
</div>
