<script lang="ts">
	/**
	 * BusinessContextForm - Collects business context for enhanced insights
	 *
	 * Allows users to set goals, KPIs, and objectives to inform LLM suggestions.
	 */
	import type { DatasetBusinessContext } from '$lib/api/types';
	import { Button } from '$lib/components/ui';

	interface Props {
		context: DatasetBusinessContext | null;
		loading?: boolean;
		saving?: boolean;
		onSave?: (context: DatasetBusinessContext) => void;
		onCancel?: () => void;
	}

	let { context, loading = false, saving = false, onSave, onCancel }: Props = $props();

	// Form state initialized from context
	let businessGoal = $state(context?.business_goal ?? '');
	let keyMetricsInput = $state(context?.key_metrics?.join(', ') ?? '');
	let kpisInput = $state(context?.kpis?.join(', ') ?? '');
	let objectives = $state(context?.objectives ?? '');
	let industry = $state(context?.industry ?? '');
	let additionalContext = $state(context?.additional_context ?? '');

	// Track if form has changes
	const hasChanges = $derived(
		businessGoal !== (context?.business_goal ?? '') ||
		keyMetricsInput !== (context?.key_metrics?.join(', ') ?? '') ||
		kpisInput !== (context?.kpis?.join(', ') ?? '') ||
		objectives !== (context?.objectives ?? '') ||
		industry !== (context?.industry ?? '') ||
		additionalContext !== (context?.additional_context ?? '')
	);

	// Industry options
	const industries = [
		'',
		'E-commerce',
		'SaaS',
		'Fintech',
		'Healthcare',
		'Education',
		'Real Estate',
		'Manufacturing',
		'Retail',
		'Media',
		'Travel',
		'Food & Beverage',
		'Professional Services',
		'Non-profit',
		'Other'
	];

	function parseCommaSeparated(input: string): string[] {
		return input
			.split(',')
			.map(s => s.trim())
			.filter(s => s.length > 0);
	}

	function handleSubmit() {
		const contextData: DatasetBusinessContext = {
			business_goal: businessGoal || null,
			key_metrics: parseCommaSeparated(keyMetricsInput),
			kpis: parseCommaSeparated(kpisInput),
			objectives: objectives || null,
			industry: industry || null,
			additional_context: additionalContext || null
		};
		onSave?.(contextData);
	}

	function handleReset() {
		businessGoal = context?.business_goal ?? '';
		keyMetricsInput = context?.key_metrics?.join(', ') ?? '';
		kpisInput = context?.kpis?.join(', ') ?? '';
		objectives = context?.objectives ?? '';
		industry = context?.industry ?? '';
		additionalContext = context?.additional_context ?? '';
	}
</script>

<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
	<!-- Header -->
	<div class="p-6 border-b border-neutral-200 dark:border-neutral-700">
		<div class="flex items-center gap-3">
			<span class="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
				<svg class="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
				</svg>
			</span>
			<div>
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Business Context</h2>
				<p class="text-sm text-neutral-500 dark:text-neutral-400">Help us understand your goals for smarter insights</p>
			</div>
		</div>
	</div>

	<!-- Form -->
	<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="p-6 space-y-5">
		<!-- Business Goal -->
		<div>
			<label for="business-goal" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
				Business Goal
			</label>
			<input
				id="business-goal"
				type="text"
				bind:value={businessGoal}
				placeholder="e.g., Increase monthly recurring revenue by 30%"
				class="w-full px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">What are you trying to achieve with this data?</p>
		</div>

		<!-- Key Metrics -->
		<div>
			<label for="key-metrics" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
				Key Metrics
			</label>
			<input
				id="key-metrics"
				type="text"
				bind:value={keyMetricsInput}
				placeholder="e.g., Revenue, Orders, Conversion Rate"
				class="w-full px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">Comma-separated list of metrics you care most about</p>
		</div>

		<!-- KPIs -->
		<div>
			<label for="kpis" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
				KPIs
			</label>
			<input
				id="kpis"
				type="text"
				bind:value={kpisInput}
				placeholder="e.g., CAC < $50, Churn < 5%, AOV > $100"
				class="w-full px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			/>
			<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">Target values for your key performance indicators</p>
		</div>

		<!-- Industry -->
		<div>
			<label for="industry" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
				Industry
			</label>
			<select
				id="industry"
				bind:value={industry}
				class="w-full px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			>
				{#each industries as ind}
					<option value={ind}>{ind || 'Select industry...'}</option>
				{/each}
			</select>
		</div>

		<!-- Objectives -->
		<div>
			<label for="objectives" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
				Current Objectives
			</label>
			<textarea
				id="objectives"
				bind:value={objectives}
				rows={2}
				placeholder="e.g., Reduce customer churn, Optimize pricing strategy"
				class="w-full px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
			></textarea>
		</div>

		<!-- Additional Context -->
		<div>
			<label for="additional-context" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
				Additional Context
			</label>
			<textarea
				id="additional-context"
				bind:value={additionalContext}
				rows={3}
				placeholder="Any other information that would help us provide better insights..."
				class="w-full px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none"
			></textarea>
		</div>

		<!-- Actions -->
		<div class="flex items-center justify-end gap-3 pt-2">
			{#if hasChanges}
				<button
					type="button"
					onclick={handleReset}
					class="px-4 py-2 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors"
				>
					Reset
				</button>
			{/if}
			{#if onCancel}
				<Button variant="secondary" size="md" onclick={onCancel}>
					{#snippet children()}
						Cancel
					{/snippet}
				</Button>
			{/if}
			<Button
				variant="brand"
				size="md"
				type="submit"
				disabled={saving || !hasChanges}
			>
				{#snippet children()}
					{#if saving}
						<svg class="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Saving...
					{:else}
						Save Context
					{/if}
				{/snippet}
			</Button>
		</div>
	</form>
</div>
