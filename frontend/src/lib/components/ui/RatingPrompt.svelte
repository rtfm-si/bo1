<script lang="ts">
	/**
	 * RatingPrompt - Thumbs up/down feedback component
	 *
	 * Shows a prompt asking for user feedback with thumbs up/down buttons.
	 * Once rated, shows a thank you message.
	 */
	import { onMount } from 'svelte';
	import { ThumbsUp, ThumbsDown } from 'lucide-svelte';
	import { toast } from '$lib/stores/toast';
	import { apiClient } from '$lib/api/client';

	interface Props {
		entityType: 'meeting' | 'action';
		entityId: string;
		prompt?: string;
		compact?: boolean;
		class?: string;
	}

	let {
		entityType,
		entityId,
		prompt = 'How was this?',
		compact = false,
		class: className = ''
	}: Props = $props();

	let rating = $state<number | null>(null);
	let submitted = $state(false);
	let submitting = $state(false);
	let error = $state<string | null>(null);

	// Load existing rating on mount - use onMount for one-time initialization
	onMount(() => {
		loadExistingRating();
	});

	async function loadExistingRating() {
		try {
			const response = await apiClient.getRating(entityType, entityId);
			if (response && response.rating !== undefined) {
				rating = response.rating;
				submitted = true;
			}
		} catch (e) {
			// No existing rating, that's fine
		}
	}

	async function submitRating(value: number) {
		if (submitting) return;

		submitting = true;
		error = null;

		try {
			await apiClient.submitRating({
				entity_type: entityType,
				entity_id: entityId,
				rating: value
			});

			rating = value;
			submitted = true;
			toast.success('Thanks for your feedback!');
		} catch (e) {
			error = 'Failed to submit rating';
			toast.error('Failed to submit rating. Please try again.');
		} finally {
			submitting = false;
		}
	}
</script>

{#if submitted}
	<div
		class="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400 {className}"
		role="status"
		aria-live="polite"
	>
		{#if rating === 1}
			<ThumbsUp size={compact ? 14 : 16} class="text-success-500" aria-hidden="true" />
			<span>Thanks for the positive feedback!</span>
		{:else}
			<ThumbsDown size={compact ? 14 : 16} class="text-error-500" aria-hidden="true" />
			<span>Thanks for the feedback. We'll work on improving.</span>
		{/if}
	</div>
{:else}
	<div
		class="flex items-center gap-3 {compact ? 'text-sm' : ''} {className}"
		role="group"
		aria-label="Rate this {entityType}"
	>
		<span class="text-neutral-600 dark:text-neutral-400">{prompt}</span>
		<div class="flex items-center gap-2">
			<button
				onclick={() => submitRating(1)}
				disabled={submitting}
				class="p-2 rounded-full transition-colors hover:bg-success-100 dark:hover:bg-success-900/30 focus:outline-none focus:ring-2 focus:ring-success-500 focus:ring-offset-2 dark:focus:ring-offset-neutral-900 disabled:opacity-50 disabled:cursor-not-allowed"
				aria-label="Rate positively (thumbs up)"
			>
				<ThumbsUp
					size={compact ? 18 : 22}
					class="text-neutral-400 hover:text-success-500 transition-colors"
				/>
			</button>
			<button
				onclick={() => submitRating(-1)}
				disabled={submitting}
				class="p-2 rounded-full transition-colors hover:bg-error-100 dark:hover:bg-error-900/30 focus:outline-none focus:ring-2 focus:ring-error-500 focus:ring-offset-2 dark:focus:ring-offset-neutral-900 disabled:opacity-50 disabled:cursor-not-allowed"
				aria-label="Rate negatively (thumbs down)"
			>
				<ThumbsDown
					size={compact ? 18 : 22}
					class="text-neutral-400 hover:text-error-500 transition-colors"
				/>
			</button>
		</div>
		{#if submitting}
			<span class="text-xs text-neutral-400">Submitting...</span>
		{/if}
	</div>
{/if}
