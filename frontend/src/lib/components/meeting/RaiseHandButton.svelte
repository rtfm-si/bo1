<script lang="ts">
	/**
	 * RaiseHandButton - Floating button for user interjections during meetings
	 *
	 * Allows users to "raise hand" and submit questions/comments during
	 * an active deliberation. Experts will acknowledge and respond.
	 */
	import { Hand, X, Send, Loader2 } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';
	import { apiClient, ApiClientError } from '$lib/api/client';
	import { fly, fade } from 'svelte/transition';

	interface Props {
		sessionId: string;
		sessionStatus: string | undefined;
		disabled?: boolean;
		hasPendingInterjection?: boolean;
	}

	let { sessionId, sessionStatus, disabled = false, hasPendingInterjection = false }: Props = $props();

	let modalOpen = $state(false);
	let message = $state('');
	let isSubmitting = $state(false);
	let errorMessage = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	const isActive = $derived(sessionStatus === 'active' || sessionStatus === 'running');
	const canRaiseHand = $derived(isActive && !disabled && !hasPendingInterjection);

	function openModal() {
		if (!canRaiseHand) return;
		modalOpen = true;
		errorMessage = null;
		successMessage = null;
	}

	function closeModal() {
		modalOpen = false;
		message = '';
		errorMessage = null;
		successMessage = null;
	}

	async function handleSubmit() {
		if (!message.trim() || isSubmitting) return;

		isSubmitting = true;
		errorMessage = null;

		try {
			await apiClient.raiseHand(sessionId, message.trim());
			successMessage = 'Experts will acknowledge your question shortly.';
			message = '';
			// Close modal after brief success message
			setTimeout(() => {
				closeModal();
			}, 2000);
		} catch (err) {
			if (err instanceof ApiClientError) {
				if (err.status === 400) {
					errorMessage = 'Cannot raise hand: meeting is not currently running.';
				} else if (err.status === 422) {
					errorMessage = 'Your message was flagged as potentially unsafe. Please rephrase.';
				} else {
					errorMessage = err.message || 'Failed to submit. Please try again.';
				}
			} else {
				errorMessage = 'Failed to submit. Please try again.';
			}
		} finally {
			isSubmitting = false;
		}
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey && message.trim()) {
			event.preventDefault();
			handleSubmit();
		}
		if (event.key === 'Escape') {
			closeModal();
		}
	}
</script>

<!-- Floating Raise Hand Button -->
{#if canRaiseHand}
	<button
		onclick={openModal}
		class="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-full shadow-lg transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-neutral-900"
		aria-label="Raise hand to ask a question"
		title="Ask a question or add context"
		transition:fly={{ y: 20, duration: 200 }}
	>
		<Hand size={20} />
		<span class="text-sm font-medium">Raise Hand</span>
	</button>
{/if}

<!-- Pending Interjection Indicator -->
{#if hasPendingInterjection && isActive}
	<div
		class="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 bg-warning-100 dark:bg-warning-900/50 text-warning-800 dark:text-warning-200 rounded-full shadow-lg border border-warning-300 dark:border-warning-700"
		transition:fly={{ y: 20, duration: 200 }}
	>
		<Loader2 size={20} class="animate-spin" />
		<span class="text-sm font-medium">Waiting for experts...</span>
	</div>
{/if}

<!-- Modal Overlay -->
{#if modalOpen}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center p-4"
		transition:fade={{ duration: 150 }}
	>
		<!-- Backdrop -->
		<button
			class="absolute inset-0 bg-black/50"
			onclick={closeModal}
			aria-label="Close modal"
		></button>

		<!-- Modal Content -->
		<div
			class="relative w-full max-w-lg bg-white dark:bg-neutral-800 rounded-xl shadow-2xl"
			transition:fly={{ y: -20, duration: 200 }}
		>
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-brand-100 dark:bg-brand-900/50 rounded-lg">
						<Hand size={20} class="text-brand-600 dark:text-brand-400" />
					</div>
					<div>
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Raise Your Hand</h2>
						<p class="text-sm text-neutral-500 dark:text-neutral-400">Ask a question or add context</p>
					</div>
				</div>
				<button
					onclick={closeModal}
					class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
					aria-label="Close"
				>
					<X size={20} class="text-neutral-500" />
				</button>
			</div>

			<!-- Body -->
			<div class="px-6 py-4">
				{#if successMessage}
					<div class="p-4 bg-success-50 dark:bg-success-900/30 border border-success-200 dark:border-success-800 rounded-lg text-success-700 dark:text-success-300 text-sm">
						{successMessage}
					</div>
				{:else}
					<div class="space-y-4">
						<p class="text-sm text-neutral-600 dark:text-neutral-400">
							The experts will pause to acknowledge your input and provide brief responses before continuing the discussion.
						</p>

						<div>
							<label for="interjection-message" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
								Your question or comment
							</label>
							<textarea
								id="interjection-message"
								bind:value={message}
								onkeydown={handleKeyDown}
								placeholder="What about the regulatory compliance implications?"
								rows={3}
								maxlength={2000}
								class="w-full px-4 py-3 bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
								disabled={isSubmitting}
							></textarea>
							<div class="flex justify-between mt-1 text-xs text-neutral-500">
								<span>Press Enter to submit, Shift+Enter for new line</span>
								<span>{message.length}/2000</span>
							</div>
						</div>

						{#if errorMessage}
							<div class="p-3 bg-error-50 dark:bg-error-900/30 border border-error-200 dark:border-error-800 rounded-lg text-error-700 dark:text-error-300 text-sm">
								{errorMessage}
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Footer -->
			{#if !successMessage}
				<div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/50 rounded-b-xl">
					<Button variant="ghost" size="md" onclick={closeModal} disabled={isSubmitting}>
						{#snippet children()}Cancel{/snippet}
					</Button>
					<Button
						variant="brand"
						size="md"
						onclick={handleSubmit}
						disabled={!message.trim() || isSubmitting}
						loading={isSubmitting}
					>
						{#snippet children()}
							{#if isSubmitting}
								<Loader2 size={16} class="animate-spin" />
								<span>Submitting...</span>
							{:else}
								<Send size={16} />
								<span>Submit</span>
							{/if}
						{/snippet}
					</Button>
				</div>
			{/if}
		</div>
	</div>
{/if}
