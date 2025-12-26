<script lang="ts">
	/**
	 * TermsConsentModal - Modal for T&C, GDPR, and Privacy Policy acceptance
	 *
	 * Features:
	 * - Displays T&C content with scroll tracking
	 * - GDPR and Privacy Policy checkboxes
	 * - Accept button enabled after scroll-to-bottom (or timeout) AND all checkboxes checked
	 * - Records all consents via batch API
	 * - Non-closable until accepted
	 */
	import { AlertCircle, FileText, Check, ExternalLink } from 'lucide-svelte';
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
	let scrollContainer = $state<HTMLDivElement>();

	// Checkbox states for each policy
	let tcChecked = $state(false);
	let gdprChecked = $state(false);
	let privacyChecked = $state(false);

	// Enable accept button after scroll (or timeout) AND all checkboxes checked
	const SCROLL_TIMEOUT_MS = 10000;
	let scrollTimeoutReached = $state(false);

	// Computed: can accept when scrolled (or timeout) AND all policies checked
	let canAccept = $derived(
		(hasScrolledToBottom || scrollTimeoutReached) && tcChecked && gdprChecked && privacyChecked
	);

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
		}
	}

	async function handleAccept() {
		if (!terms || !canAccept) return;

		isSubmitting = true;
		error = null;

		try {
			// Record all three consents in batch
			await apiClient.recordMultiConsent(terms.id, ['tc', 'gdpr', 'privacy']);
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
			scrollTimeoutReached = false;
			tcChecked = false;
			gdprChecked = false;
			privacyChecked = false;

			// Fallback: enable scroll requirement after timeout
			const timeout = setTimeout(() => {
				scrollTimeoutReached = true;
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
					<span>-</span>
					<span>Published {new Date(terms.published_at).toLocaleDateString()}</span>
				</div>

				<div
					bind:this={scrollContainer}
					onscroll={handleScroll}
					class="max-h-72 overflow-y-auto border border-neutral-200 dark:border-neutral-700 rounded-lg p-4 bg-neutral-50 dark:bg-neutral-800"
				>
					<MarkdownContent
						content={terms.content}
						class="prose prose-sm dark:prose-invert max-w-none"
					/>
				</div>

				{#if !hasScrolledToBottom && !scrollTimeoutReached}
					<p class="text-xs text-neutral-500 dark:text-neutral-400 text-center">
						Please scroll to read the complete terms before accepting
					</p>
				{/if}

				<!-- Consent Checkboxes -->
				<div class="space-y-3 border-t border-neutral-200 dark:border-neutral-700 pt-4">
					<label class="flex items-start gap-3 cursor-pointer">
						<input
							type="checkbox"
							bind:checked={tcChecked}
							class="mt-1 h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
						/>
						<span class="text-sm text-neutral-700 dark:text-neutral-300">
							I have read and agree to the
							<a
								href="/legal/terms"
								target="_blank"
								class="text-brand-600 dark:text-brand-400 hover:underline inline-flex items-center gap-1"
							>
								Terms & Conditions
								<ExternalLink size={12} />
							</a>
						</span>
					</label>

					<label class="flex items-start gap-3 cursor-pointer">
						<input
							type="checkbox"
							bind:checked={gdprChecked}
							class="mt-1 h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
						/>
						<span class="text-sm text-neutral-700 dark:text-neutral-300">
							I consent to the processing of my personal data as described in the
							<a
								href="/legal/privacy#gdpr"
								target="_blank"
								class="text-brand-600 dark:text-brand-400 hover:underline inline-flex items-center gap-1"
							>
								GDPR Data Processing Agreement
								<ExternalLink size={12} />
							</a>
						</span>
					</label>

					<label class="flex items-start gap-3 cursor-pointer">
						<input
							type="checkbox"
							bind:checked={privacyChecked}
							class="mt-1 h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
						/>
						<span class="text-sm text-neutral-700 dark:text-neutral-300">
							I acknowledge that I have read the
							<a
								href="/legal/privacy"
								target="_blank"
								class="text-brand-600 dark:text-brand-400 hover:underline inline-flex items-center gap-1"
							>
								Privacy Policy
								<ExternalLink size={12} />
							</a>
						</span>
					</label>
				</div>
			{/if}
		</div>
	{/snippet}

	{#snippet footer()}
		<div class="flex flex-col gap-3">
			<p class="text-sm text-neutral-600 dark:text-neutral-400">
				By clicking "I Accept", you agree to our Terms & Conditions, GDPR data processing, and
				acknowledge our Privacy Policy.
			</p>
			<div class="flex justify-end">
				<Button variant="brand" size="md" onclick={handleAccept} disabled={!canAccept || isSubmitting}>
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
