<script lang="ts">
	/**
	 * UnblockSuggestions - AI-powered suggestions for unblocking blocked actions
	 *
	 * Shows a button to generate suggestions, then displays 3-5 actionable approaches
	 * with effort levels and rationale.
	 */
	import { Lightbulb, Loader2, ChevronDown, ChevronUp, Zap, Clock, AlertTriangle } from 'lucide-svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { apiClient } from '$lib/api/client';
	import type { UnblockSuggestion } from '$lib/api/types';

	interface Props {
		actionId: string;
		onApply?: (suggestion: UnblockSuggestion) => void;
	}

	let { actionId, onApply }: Props = $props();

	let isLoading = $state(false);
	let isExpanded = $state(false);
	let suggestions = $state<UnblockSuggestion[]>([]);
	let error = $state<string | null>(null);
	let hasLoaded = $state(false);

	async function loadSuggestions() {
		if (isLoading) return;

		isLoading = true;
		error = null;

		try {
			const response = await apiClient.suggestUnblockPaths(actionId);
			suggestions = response.suggestions;
			hasLoaded = true;
			isExpanded = true;
		} catch (e) {
			if (e instanceof Error) {
				// Handle rate limit
				if (e.message.includes('429') || e.message.includes('rate')) {
					error = 'Rate limit reached. Please wait a minute before trying again.';
				} else {
					error = e.message || 'Failed to generate suggestions';
				}
			} else {
				error = 'Failed to generate suggestions';
			}
		} finally {
			isLoading = false;
		}
	}

	function handleApply(suggestion: UnblockSuggestion) {
		onApply?.(suggestion);
	}

	function getEffortIcon(level: string) {
		switch (level) {
			case 'low':
				return Zap;
			case 'high':
				return AlertTriangle;
			default:
				return Clock;
		}
	}

	function getEffortVariant(level: string): 'success' | 'warning' | 'error' {
		switch (level) {
			case 'low':
				return 'success';
			case 'high':
				return 'warning';
			default:
				return 'info' as 'warning'; // info maps closest to medium
		}
	}
</script>

<div class="space-y-3">
	{#if !hasLoaded}
		<!-- Initial state: button to generate suggestions -->
		<BoButton
			variant="outline"
			size="sm"
			onclick={loadSuggestions}
			disabled={isLoading}
			loading={isLoading}
		>
			{#if !isLoading}
				<Lightbulb class="h-4 w-4 mr-2" />
			{/if}
			{isLoading ? 'Generating suggestions...' : 'Suggest ways to unblock'}
		</BoButton>
	{:else}
		<!-- Loaded state: collapsible suggestions panel -->
		<button
			type="button"
			class="flex items-center gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
			onclick={() => (isExpanded = !isExpanded)}
		>
			<Lightbulb class="h-4 w-4" />
			<span>Unblock suggestions ({suggestions.length})</span>
			{#if isExpanded}
				<ChevronUp class="h-4 w-4" />
			{:else}
				<ChevronDown class="h-4 w-4" />
			{/if}
		</button>

		{#if isExpanded}
			<div class="space-y-3">
				{#each suggestions as suggestion, i}
					<BoCard variant="bordered" padding="sm">
						<div class="space-y-2">
							<div class="flex items-start justify-between gap-3">
								<p class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
									{suggestion.approach}
								</p>
								<Badge variant={getEffortVariant(suggestion.effort_level)} size="sm">
									<svelte:component this={getEffortIcon(suggestion.effort_level)} class="h-3 w-3 mr-1" />
									{suggestion.effort_level}
								</Badge>
							</div>

							<p class="text-xs text-neutral-600 dark:text-neutral-400">
								{suggestion.rationale}
							</p>

							{#if onApply}
								<div class="pt-1">
									<BoButton
										variant="ghost"
										size="sm"
										onclick={() => handleApply(suggestion)}
									>
										Apply this approach
									</BoButton>
								</div>
							{/if}
						</div>
					</BoCard>
				{/each}

				<!-- Refresh button -->
				<BoButton
					variant="ghost"
					size="sm"
					onclick={loadSuggestions}
					disabled={isLoading}
					loading={isLoading}
				>
					{isLoading ? 'Generating...' : 'Get new suggestions'}
				</BoButton>
			</div>
		{/if}
	{/if}

	{#if error}
		<Alert variant="error">
			{error}
		</Alert>
	{/if}
</div>
