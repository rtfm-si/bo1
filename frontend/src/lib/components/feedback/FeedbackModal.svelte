<script lang="ts">
	/**
	 * FeedbackModal Component - Submit feature requests or problem reports
	 * Rate limited to 5 submissions per hour
	 */
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import HoneypotFields from '$lib/components/ui/HoneypotFields.svelte';
	import { apiClient } from '$lib/api/client';
	import type { FeedbackType, HoneypotFields as HoneypotFieldsType } from '$lib/api/types';

	interface Props {
		open?: boolean;
		onclose?: () => void;
		onsuccess?: () => void;
	}

	let { open = $bindable(false), onclose, onsuccess }: Props = $props();

	let feedbackType = $state<FeedbackType>('feature_request');
	let title = $state('');
	let description = $state('');
	let includeContext = $state(true);
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);
	let success = $state(false);
	let honeypotValues = $state<HoneypotFieldsType>({});

	function handleClose() {
		// Close modal and reset form state
		open = false;
		feedbackType = 'feature_request';
		title = '';
		description = '';
		includeContext = true;
		error = null;
		success = false;
		honeypotValues = {};
		onclose?.();
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!title.trim()) {
			error = 'Please provide a title';
			return;
		}

		if (!description.trim()) {
			error = 'Please provide a description';
			return;
		}

		isSubmitting = true;
		error = null;

		try {
			await apiClient.submitFeedback({
				type: feedbackType,
				title: title.trim(),
				description: description.trim(),
				include_context: feedbackType === 'problem_report' ? includeContext : false,
				...honeypotValues
			});

			success = true;
			setTimeout(() => {
				open = false;
				// Reset after close animation
				setTimeout(() => {
					title = '';
					description = '';
					success = false;
					onsuccess?.();
				}, 300);
			}, 1500);
		} catch (e) {
			if (e instanceof Error && e.message.includes('429')) {
				error = 'You have reached the feedback limit (5 per hour). Please try again later.';
			} else {
				error = e instanceof Error ? e.message : 'Failed to submit feedback';
			}
		} finally {
			isSubmitting = false;
		}
	}
</script>

<Modal {open} title="Send Feedback" size="md" onclose={handleClose}>
	{#if success}
		<div class="text-center py-8">
			<div class="w-16 h-16 mx-auto mb-4 bg-success-100 dark:bg-success-900/30 rounded-full flex items-center justify-center">
				<svg class="w-8 h-8 text-success-600 dark:text-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
				</svg>
			</div>
			<h3 class="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-2">
				Thank you for your feedback!
			</h3>
			<p class="text-neutral-600 dark:text-neutral-400">
				We appreciate you taking the time to help us improve.
			</p>
		</div>
	{:else}
		<form onsubmit={handleSubmit} class="space-y-4">
			<!-- Honeypot fields for bot detection -->
			<HoneypotFields bind:values={honeypotValues} />

			{#if error}
				<Alert variant="error">{error}</Alert>
			{/if}

			<!-- Type Toggle -->
			<fieldset class="space-y-2">
				<legend class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
					What type of feedback?
				</legend>
				<div class="flex gap-2" role="group">
					<button
						type="button"
						class={[
							'flex-1 px-4 py-2 rounded-lg border text-sm font-medium transition-colors',
							feedbackType === 'feature_request'
								? 'border-brand-500 bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300'
								: 'border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800'
						].join(' ')}
						onclick={() => (feedbackType = 'feature_request')}
					>
						<span class="mr-2">💡</span>
						Feature Request
					</button>
					<button
						type="button"
						class={[
							'flex-1 px-4 py-2 rounded-lg border text-sm font-medium transition-colors',
							feedbackType === 'problem_report'
								? 'border-brand-500 bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300'
								: 'border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800'
						].join(' ')}
						onclick={() => (feedbackType = 'problem_report')}
					>
						<span class="mr-2">🐛</span>
						Report a Problem
					</button>
				</div>
			</fieldset>

			<!-- Title -->
			<div class="space-y-1">
				<label for="feedback-title" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
					{feedbackType === 'feature_request' ? 'What would you like to see?' : 'What went wrong?'}
				</label>
				<input
					id="feedback-title"
					type="text"
					bind:value={title}
					placeholder={feedbackType === 'feature_request' ? 'e.g., Add dark mode support' : 'e.g., Page not loading correctly'}
					required
					disabled={isSubmitting}
					maxlength={200}
					class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
				/>
			</div>

			<!-- Description -->
			<div class="space-y-1">
				<label for="feedback-description" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
					Tell us more
				</label>
				<textarea
					id="feedback-description"
					bind:value={description}
					placeholder={feedbackType === 'feature_request'
						? 'Describe the feature you\'d like and how it would help you...'
						: 'Describe what happened, what you expected, and any steps to reproduce...'}
					required
					disabled={isSubmitting}
					rows={4}
					maxlength={5000}
					class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none disabled:opacity-50 disabled:cursor-not-allowed"
				></textarea>
			</div>

			<!-- Context checkbox (only for problem reports) -->
			{#if feedbackType === 'problem_report'}
				<label class="flex items-start gap-3 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={includeContext}
						disabled={isSubmitting}
						class="mt-1 w-4 h-4 text-brand-600 border-neutral-300 dark:border-neutral-600 rounded focus:ring-brand-500"
					/>
					<span class="text-sm text-neutral-600 dark:text-neutral-400">
						Include context to help us debug
						<span class="block text-xs text-neutral-500 dark:text-neutral-500">
							Shares your subscription tier, current page URL, and browser info
						</span>
					</span>
				</label>
			{/if}

			<div class="flex justify-end gap-3 pt-4">
				<Button type="button" variant="ghost" onclick={handleClose} disabled={isSubmitting}>
					Cancel
				</Button>
				<Button type="submit" variant="brand" loading={isSubmitting}>
					Submit Feedback
				</Button>
			</div>
		</form>
	{/if}
</Modal>
