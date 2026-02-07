<script lang="ts">
	/**
	 * BusinessMetricSuggestions - Shows business metric suggestions from insights
	 *
	 * Displays suggestions to auto-populate business metrics (MRR, churn, etc.)
	 * based on clarification answers from meetings. Uses keyword-based matching.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { BusinessMetricSuggestion } from '$lib/api/types';
	import Alert from '$lib/components/ui/Alert.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	// Props
	interface Props {
		onapplied?: (event: { metricKey: string; value: number }) => void;
	}

	let { onapplied }: Props = $props();

	// State
	let suggestions = $state<BusinessMetricSuggestion[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let processingMetric = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	onMount(async () => {
		await loadSuggestions();
	});

	async function loadSuggestions() {
		isLoading = true;
		error = null;

		try {
			const response = await apiClient.getBusinessMetricSuggestions();
			suggestions = response.suggestions ?? [];
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load suggestions';
			console.error('Failed to load business metric suggestions:', e);
		} finally {
			isLoading = false;
		}
	}

	async function apply(suggestion: BusinessMetricSuggestion) {
		processingMetric = suggestion.metric_key;
		error = null;

		try {
			// Parse numeric value from suggested_value string
			const numValue = parseNumericValue(suggestion.suggested_value);
			if (numValue === null) {
				throw new Error('Could not parse numeric value from suggestion');
			}

			await apiClient.applyBusinessMetricSuggestion({
				metric_key: suggestion.metric_key,
				value: numValue,
				source_question: suggestion.source_question
			});

			// Remove from list
			suggestions = suggestions.filter((s) => s.metric_key !== suggestion.metric_key);
			successMessage = `Updated ${suggestion.metric_name || suggestion.metric_key}`;

			// Call callback for parent to refresh metrics
			if (onapplied) {
				onapplied({ metricKey: suggestion.metric_key, value: numValue });
			}

			setTimeout(() => {
				successMessage = null;
			}, 3000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to apply suggestion';
		} finally {
			processingMetric = null;
		}
	}

	async function dismiss(suggestion: BusinessMetricSuggestion) {
		processingMetric = suggestion.metric_key;

		try {
			await apiClient.dismissBusinessMetricSuggestion({
				metric_key: suggestion.metric_key,
				source_question: suggestion.source_question
			});

			// Remove from list
			suggestions = suggestions.filter((s) => s.metric_key !== suggestion.metric_key);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to dismiss suggestion';
		} finally {
			processingMetric = null;
		}
	}

	function parseNumericValue(value: string): number | null {
		// Remove currency symbols, commas, and common suffixes
		const cleaned = value
			.replace(/[$,]/g, '')
			.replace(/\s*(k|K|m|M|%|mo|months?|ratio).*$/i, '')
			.trim();

		const num = parseFloat(cleaned);
		if (isNaN(num)) return null;

		// Handle multipliers like "50K" or "1.5M"
		const lowerValue = value.toLowerCase();
		if (lowerValue.includes('k')) return num * 1000;
		if (lowerValue.includes('m')) return num * 1000000;

		return num;
	}

	function formatConfidence(confidence: number): string {
		return `${Math.round(confidence * 100)}%`;
	}

	function formatDate(dateStr: string | null | undefined): string {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric'
		});
	}

	function truncateQuestion(question: string, maxLen: number = 50): string {
		if (question.length <= maxLen) return question;
		return question.slice(0, maxLen - 3) + '...';
	}
</script>

{#if isLoading}
	<div class="flex items-center justify-center py-4">
		<Spinner size="sm" />
	</div>
{:else if suggestions.length === 0}
	<!-- Empty state - don't show the card at all -->
{:else}
	<div
		class="bg-gradient-to-r from-brand-50 to-indigo-50 dark:from-brand-900/20 dark:to-indigo-900/20 rounded-xl border border-brand-200 dark:border-brand-800 mb-6"
	>
		<!-- Header -->
		<div class="p-4 border-b border-brand-200 dark:border-brand-800">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<span class="text-lg">&#128161;</span>
					<div>
						<h3 class="text-sm font-semibold text-neutral-900 dark:text-white">
							Suggested from Insights
						</h3>
						<p class="text-xs text-neutral-500 dark:text-neutral-400">
							Values detected in your meeting Q&A
						</p>
					</div>
				</div>
				<span
					class="px-2 py-0.5 text-xs font-medium bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300 rounded-full"
				>
					{suggestions.length}
				</span>
			</div>
		</div>

		<!-- Error Alert -->
		{#if error}
			<div class="p-3 border-b border-brand-200 dark:border-brand-800">
				<Alert variant="error">
					{error}
					<button
						class="ml-2 underline text-sm"
						onclick={() => {
							error = null;
						}}>Dismiss</button
					>
				</Alert>
			</div>
		{/if}

		<!-- Success message -->
		{#if successMessage}
			<div class="p-3 border-b border-brand-200 dark:border-brand-800">
				<Alert variant="success">{successMessage}</Alert>
			</div>
		{/if}

		<!-- Suggestions List -->
		<div class="divide-y divide-brand-200 dark:divide-brand-800">
			{#each suggestions as suggestion (suggestion.metric_key)}
				{@const displayName = suggestion.metric_name || suggestion.metric_key}
				<div class="p-4 hover:bg-brand-100/50 dark:hover:bg-brand-900/30 transition-colors">
					<div class="flex items-start gap-3">
						<div class="flex-1 min-w-0">
							<!-- Metric name and change -->
							<div class="flex items-center gap-2 mb-1 flex-wrap">
								<span class="font-medium text-neutral-900 dark:text-white text-sm">
									{displayName}
								</span>
								{#if suggestion.current_value !== null && suggestion.current_value !== undefined}
									<span class="text-xs text-neutral-400 dark:text-neutral-500 line-through">
										{suggestion.current_value}
									</span>
									<span class="text-neutral-400">&rarr;</span>
								{/if}
								<span class="font-semibold text-brand-600 dark:text-brand-400">
									{suggestion.suggested_value}
								</span>
							</div>

							<!-- Source question -->
							<p
								class="text-xs text-neutral-500 dark:text-neutral-400 italic"
								title={suggestion.source_question}
							>
								&ldquo;{truncateQuestion(suggestion.source_question)}&rdquo;
							</p>

							<!-- Metadata -->
							<div
								class="flex items-center gap-3 mt-1.5 text-xs text-neutral-400 dark:text-neutral-500"
							>
								<span
									class="inline-flex items-center gap-1"
									title="How confident we are in this match"
								>
									Confidence: {formatConfidence(suggestion.confidence)}
								</span>
								{#if suggestion.answered_at}
									<span>{formatDate(suggestion.answered_at)}</span>
								{/if}
							</div>
						</div>

						<!-- Actions -->
						<div class="flex items-center gap-1.5 flex-shrink-0">
							<button
								class="px-3 py-1.5 text-xs font-medium text-white bg-brand-600 hover:bg-brand-700 rounded transition-colors disabled:opacity-50"
								onclick={() => apply(suggestion)}
								disabled={processingMetric !== null}
							>
								{#if processingMetric === suggestion.metric_key}
									<span
										class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"
									></span>
								{:else}
									Apply
								{/if}
							</button>
							<button
								class="px-2 py-1.5 text-xs text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded transition-colors"
								onclick={() => dismiss(suggestion)}
								disabled={processingMetric !== null}
								title="Dismiss this suggestion"
							>
								&times;
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}
