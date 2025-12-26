<script lang="ts">
	/**
	 * TermsConsentModal - Modal for T&C acceptance during first login/version update
	 *
	 * Features:
	 * - Displays T&C content with scroll tracking
	 * - Accept button enabled after scroll-to-bottom or timeout
	 * - Records consent via API
	 * - Non-closable until accepted
	 */
	import { AlertCircle, FileText, Check } from 'lucide-svelte';
	import { Modal, Button, Alert, Spinner } from '$lib/components/ui';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import { apiClient, ApiClientError } from '$lib/api/client';
	import type { TermsVersionResponse } from '$lib/api/client';

	interface Props {
		open: boolean;
		onAccept: () => void;
	}

	let { open = $bindable(), onAccept }: Props = $props();

	// State
	let isLoading = $state(true);
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);
	let terms = $state<TermsVersionResponse | null>(null);
	let hasScrolledToBottom = $state(false);
	let canAccept = $state(false);
	let scrollContainer = $state<HTMLDivElement>();

	// Enable accept button after scroll or 10s timeout
	const SCROLL_TIMEOUT_MS = 10000;

	async function loadTerms() {
		isLoading = true;
		error = null;
		try {
			terms = await apiClient.getCurrentTerms();
		} catch (err) {
			console.error('Failed to load terms:', err);
			error = err instanceof ApiClientError ? err.message : 'Failed to load terms';
		} finally {
			isLoading = false;
		}
	}

	function handleScroll() {
		if (!scrollContainer) return;

		const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
		// Consider scrolled to bottom if within 50px of the end
		if (scrollTop + clientHeight >= scrollHeight - 50) {
			hasScrolledToBottom = true;
			canAccept = true;
		}
	}

	async function handleAccept() {
		if (!terms || !canAccept) return;

		isSubmitting = true;
		error = null;

		try {
			await apiClient.recordTermsConsent(terms.id);
			onAccept();
		} catch (err) {
			console.error('Failed to record consent:', err);
			error = err instanceof ApiClientError ? err.message : 'Failed to record consent';
		} finally {
			isSubmitting = false;
		}
	}

	// Load terms when modal opens
	$effect(() => {
		if (open) {
			loadTerms();
			hasScrolledToBottom = false;
			canAccept = false;

			// Fallback: enable accept after timeout
			const timeout = setTimeout(() => {
				canAccept = true;
			}, SCROLL_TIMEOUT_MS);

			return () => clearTimeout(timeout);
		}
	});
</script>

<Modal {open} title="Terms & Conditions" size="lg" closable={false}>
	{#snippet children()}
		<div class="space-y-4">
			{#if error}
				<Alert variant="error">
					<AlertCircle size={16} />
					<span>{error}</span>
				</Alert>
			{/if}

			{#if isLoading}
				<div class="flex items-center justify-center py-12">
					<Spinner size="lg" />
				</div>
			{:else if terms}
				<div class="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
					<FileText size={16} />
					<span>Version {terms.version}</span>
					<span>•</span>
					<span>Published {new Date(terms.published_at).toLocaleDateString()}</span>
				</div>

				<div
					bind:this={scrollContainer}
					onscroll={handleScroll}
					class="max-h-96 overflow-y-auto border border-neutral-200 dark:border-neutral-700 rounded-lg p-4 bg-neutral-50 dark:bg-neutral-800"
				>
					<MarkdownContent content={terms.content} class="prose prose-sm dark:prose-invert max-w-none" />
				</div>

				{#if !hasScrolledToBottom}
					<p class="text-xs text-neutral-500 dark:text-neutral-400 text-center">
						Please scroll to read the complete terms before accepting
					</p>
				{/if}
			{/if}
		</div>
	{/snippet}

	{#snippet footer()}
		<div class="flex flex-col gap-3">
			<p class="text-sm text-neutral-600 dark:text-neutral-400">
				By clicking "I Accept", you agree to our Terms & Conditions.
			</p>
			<div class="flex justify-end">
				<Button
					variant="brand"
					size="md"
					onclick={handleAccept}
					disabled={!canAccept || isSubmitting}
				>
					{#if isSubmitting}
						<Spinner size="sm" />
						<span>Processing...</span>
					{:else}
						<Check size={16} />
						<span>I Accept</span>
					{/if}
				</Button>
			</div>
		</div>
	{/snippet}
</Modal>
