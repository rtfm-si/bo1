<script lang="ts">
	/**
	 * PendingUpdates - Shows suggested context updates requiring user approval
	 *
	 * Displays low-confidence context updates extracted from clarifications,
	 * problem statements, and action notes. Users can approve or dismiss each.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { ContextUpdateSuggestion, ContextUpdateSource } from '$lib/api/types';
	import Alert from '$lib/components/ui/Alert.svelte';

	// State
	let suggestions = $state<ContextUpdateSuggestion[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let processingId = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	// Source label config
	const sourceLabels: Record<ContextUpdateSource, { label: string; icon: string }> = {
		clarification: { label: 'Meeting Q&A', icon: '💬' },
		problem_statement: { label: 'Problem Statement', icon: '📝' },
		action: { label: 'Action Update', icon: '✓' }
	};

	// Field display names
	const fieldLabels: Record<string, string> = {
		revenue: 'Revenue',
		customers: 'Customers',
		growth_rate: 'Growth Rate',
		team_size: 'Team Size',
		business_stage: 'Business Stage',
		primary_objective: 'Primary Objective',
		industry: 'Industry',
		pricing_model: 'Pricing Model',
		target_geography: 'Target Geography',
		competitors: 'Competitors',
		mau_bucket: 'MAU Range',
		revenue_stage: 'Revenue Stage'
	};

	onMount(async () => {
		await loadPendingUpdates();
	});

	async function loadPendingUpdates() {
		isLoading = true;
		error = null;

		try {
			const response = await apiClient.getPendingUpdates();
			suggestions = response.suggestions;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load pending updates';
			console.error('Failed to load pending updates:', e);
		} finally {
			isLoading = false;
		}
	}

	async function approve(id: string) {
		processingId = id;
		error = null;

		try {
			const result = await apiClient.approvePendingUpdate(id);
			suggestions = suggestions.filter((s) => s.id !== id);
			successMessage = `Updated ${fieldLabels[result.field_name] || result.field_name}`;
			setTimeout(() => {
				successMessage = null;
			}, 3000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to approve update';
		} finally {
			processingId = null;
		}
	}

	async function dismiss(id: string) {
		processingId = id;
		error = null;

		try {
			await apiClient.dismissPendingUpdate(id);
			suggestions = suggestions.filter((s) => s.id !== id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to dismiss update';
		} finally {
			processingId = null;
		}
	}

	function formatConfidence(confidence: number): string {
		return `${Math.round(confidence * 100)}%`;
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric'
		});
	}
</script>

{#if isLoading}
	<div class="flex items-center justify-center py-8">
		<div class="animate-spin h-6 w-6 border-2 border-brand-600 border-t-transparent rounded-full"
		></div>
	</div>
{:else if suggestions.length === 0}
	<!-- Empty state - don't show the card at all -->
{:else}
	<div
		class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700"
	>
		<!-- Header -->
		<div class="p-4 border-b border-slate-200 dark:border-slate-700">
			<div class="flex items-center justify-between">
				<div>
					<h3 class="text-sm font-semibold text-slate-900 dark:text-white">Suggested Updates</h3>
					<p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
						We detected these from your meetings
					</p>
				</div>
				<span
					class="px-2 py-0.5 text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full"
				>
					{suggestions.length} pending
				</span>
			</div>
		</div>

		<!-- Error Alert -->
		{#if error}
			<div class="p-4 border-b border-slate-200 dark:border-slate-700">
				<Alert variant="error">
					{error}
					<button
						class="ml-2 underline"
						onclick={() => {
							error = null;
						}}>Dismiss</button
					>
				</Alert>
			</div>
		{/if}

		<!-- Success message -->
		{#if successMessage}
			<div class="p-4 border-b border-slate-200 dark:border-slate-700">
				<Alert variant="success">{successMessage}</Alert>
			</div>
		{/if}

		<!-- Suggestions List -->
		<div class="divide-y divide-slate-200 dark:divide-slate-700">
			{#each suggestions as suggestion (suggestion.id)}
				{@const source = sourceLabels[suggestion.source_type]}
				{@const fieldLabel = fieldLabels[suggestion.field_name] || suggestion.field_name}
				<div class="p-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
					<div class="flex items-start gap-3">
						<div class="flex-1 min-w-0">
							<!-- Field name and source -->
							<div class="flex items-center gap-2 mb-2">
								<span
									class="font-medium text-slate-900 dark:text-white text-sm"
								>
									{fieldLabel}
								</span>
								<span
									class="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded"
								>
									<span>{source.icon}</span>
									{source.label}
								</span>
							</div>

							<!-- Value change -->
							<div class="flex items-center gap-2 text-sm mb-2">
								{#if suggestion.current_value}
									<span class="text-slate-500 dark:text-slate-400 line-through">
										{suggestion.current_value}
									</span>
									<span class="text-slate-400">→</span>
								{/if}
								<span class="font-medium text-brand-600 dark:text-brand-400">
									{suggestion.new_value}
								</span>
							</div>

							<!-- Source text -->
							<p class="text-xs text-slate-500 dark:text-slate-400 italic truncate">
								"{suggestion.source_text}"
							</p>

							<!-- Metadata -->
							<div class="flex items-center gap-3 mt-2 text-xs text-slate-400 dark:text-slate-500">
								<span>Confidence: {formatConfidence(suggestion.confidence)}</span>
								<span>{formatDate(suggestion.extracted_at)}</span>
							</div>
						</div>

						<!-- Actions -->
						<div class="flex items-center gap-2 flex-shrink-0">
							<button
								class="px-3 py-1.5 text-xs font-medium text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded transition-colors disabled:opacity-50"
								onclick={() => approve(suggestion.id)}
								disabled={processingId === suggestion.id}
							>
								{#if processingId === suggestion.id}
									<span class="inline-block w-4 h-4 border-2 border-brand-600 border-t-transparent rounded-full animate-spin"></span>
								{:else}
									Apply
								{/if}
							</button>
							<button
								class="px-3 py-1.5 text-xs font-medium text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors disabled:opacity-50"
								onclick={() => dismiss(suggestion.id)}
								disabled={processingId === suggestion.id}
							>
								Dismiss
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}
