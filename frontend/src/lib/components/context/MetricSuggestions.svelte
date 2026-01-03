<script lang="ts">
	/**
	 * MetricSuggestions - Shows metric suggestions extracted from insights
	 *
	 * Displays suggestions to auto-populate context metrics (revenue, customers, etc.)
	 * based on clarification answers from meetings. Users can apply or dismiss each.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { MetricSuggestion } from '$lib/api/types';
	import Alert from '$lib/components/ui/Alert.svelte';

	// Props
	interface Props {
		onapplied?: (event: { field: string; value: string }) => void;
	}

	let { onapplied }: Props = $props();

	// State
	let suggestions = $state<MetricSuggestion[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let processingField = $state<string | null>(null);
	let successMessage = $state<string | null>(null);
	let dismissedFields = $state<Set<string>>(new Set());

	// Field display names
	const fieldLabels: Record<string, string> = {
		revenue: 'Revenue',
		customers: 'Customers',
		growth_rate: 'Growth Rate',
		team_size: 'Team Size'
	};

	onMount(async () => {
		// Load dismissed fields from localStorage
		try {
			const stored = localStorage.getItem('dismissedMetricSuggestions');
			if (stored) {
				const parsed = JSON.parse(stored);
				dismissedFields = new Set(parsed);
			}
		} catch {
			// Ignore localStorage errors
		}

		await loadSuggestions();
	});

	async function loadSuggestions() {
		isLoading = true;
		error = null;

		try {
			const response = await apiClient.getMetricSuggestions();
			// Filter out dismissed suggestions
			suggestions = (response.suggestions ?? []).filter(
				(s) => !dismissedFields.has(s.field)
			);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load suggestions';
			console.error('Failed to load metric suggestions:', e);
		} finally {
			isLoading = false;
		}
	}

	async function apply(suggestion: MetricSuggestion) {
		processingField = suggestion.field;
		error = null;

		try {
			await apiClient.applyMetricSuggestion({
				field: suggestion.field,
				value: suggestion.suggested_value,
				source_question: suggestion.source_question
			});

			// Remove from list
			suggestions = suggestions.filter((s) => s.field !== suggestion.field);
			successMessage = `Updated ${fieldLabels[suggestion.field] || suggestion.field}`;

			// Call callback for parent to refresh metrics
			if (onapplied) {
				onapplied({ field: suggestion.field, value: suggestion.suggested_value });
			}

			setTimeout(() => {
				successMessage = null;
			}, 3000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to apply suggestion';
		} finally {
			processingField = null;
		}
	}

	async function applyAll() {
		for (const suggestion of [...suggestions]) {
			await apply(suggestion);
			// Small delay between requests
			await new Promise((r) => setTimeout(r, 100));
		}
	}

	function dismiss(field: string) {
		// Remove from current list
		suggestions = suggestions.filter((s) => s.field !== field);

		// Add to dismissed set and persist
		dismissedFields.add(field);
		try {
			localStorage.setItem('dismissedMetricSuggestions', JSON.stringify([...dismissedFields]));
		} catch {
			// Ignore localStorage errors
		}
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

	function truncateQuestion(question: string, maxLen: number = 60): string {
		if (question.length <= maxLen) return question;
		return question.slice(0, maxLen - 3) + '...';
	}
</script>

{#if isLoading}
	<div class="flex items-center justify-center py-4">
		<div class="animate-spin h-5 w-5 border-2 border-brand-600 border-t-transparent rounded-full"></div>
	</div>
{:else if suggestions.length === 0}
	<!-- Empty state - don't show the card at all -->
{:else}
	<div
		class="bg-gradient-to-r from-brand-50 to-indigo-50 dark:from-brand-900/20 dark:to-indigo-900/20 rounded-xl border border-brand-200 dark:border-brand-800"
	>
		<!-- Header -->
		<div class="p-4 border-b border-brand-200 dark:border-brand-800">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<span class="text-lg">💡</span>
					<div>
						<h3 class="text-sm font-semibold text-slate-900 dark:text-white">
							Suggested from Insights
						</h3>
						<p class="text-xs text-slate-500 dark:text-slate-400">
							We found these values in your meeting Q&A
						</p>
					</div>
				</div>
				<div class="flex items-center gap-2">
					{#if suggestions.length > 1}
						<button
							class="px-2.5 py-1 text-xs font-medium text-brand-600 dark:text-brand-400 hover:bg-brand-100 dark:hover:bg-brand-900/30 rounded transition-colors"
							onclick={applyAll}
							disabled={processingField !== null}
						>
							Apply All
						</button>
					{/if}
					<span
						class="px-2 py-0.5 text-xs font-medium bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300 rounded-full"
					>
						{suggestions.length}
					</span>
				</div>
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
			{#each suggestions as suggestion (suggestion.field)}
				{@const fieldLabel = fieldLabels[suggestion.field] || suggestion.field}
				<div class="p-4 hover:bg-brand-100/50 dark:hover:bg-brand-900/30 transition-colors">
					<div class="flex items-start gap-3">
						<div class="flex-1 min-w-0">
							<!-- Field name and change -->
							<div class="flex items-center gap-2 mb-1">
								<span class="font-medium text-slate-900 dark:text-white text-sm">
									{fieldLabel}
								</span>
								{#if suggestion.current_value}
									<span class="text-xs text-slate-400 dark:text-slate-500 line-through">
										{suggestion.current_value}
									</span>
									<span class="text-slate-400">→</span>
								{/if}
								<span class="font-semibold text-brand-600 dark:text-brand-400">
									{suggestion.suggested_value}
								</span>
							</div>

							<!-- Source question -->
							<p
								class="text-xs text-slate-500 dark:text-slate-400 italic"
								title={suggestion.source_question}
							>
								"{truncateQuestion(suggestion.source_question)}"
							</p>

							<!-- Metadata -->
							<div class="flex items-center gap-3 mt-1.5 text-xs text-slate-400 dark:text-slate-500">
								<span
									class="inline-flex items-center gap-1"
									title="How confident we are in this extraction"
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
								disabled={processingField !== null}
							>
								{#if processingField === suggestion.field}
									<span
										class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"
									></span>
								{:else}
									Apply
								{/if}
							</button>
							<button
								class="px-2 py-1.5 text-xs text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
								onclick={() => dismiss(suggestion.field)}
								disabled={processingField !== null}
								title="Dismiss this suggestion"
							>
								✕
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}
