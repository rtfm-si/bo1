<script lang="ts">
	/**
	 * OptionComparisonCard - Displays a single decision option card
	 */
	import type { OptionCard } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { ChevronDown, ChevronUp, AlertTriangle } from 'lucide-svelte';

	interface Props {
		option: OptionCard;
		selected: boolean;
		onclick: () => void;
	}

	let { option, selected, onclick }: Props = $props();

	let showConditions = $state(false);

	const confidencePercent = $derived(
		Math.round(((option.confidence_range[0] + option.confidence_range[1]) / 2) * 100)
	);

	const confidenceColor = $derived(
		confidencePercent >= 70
			? 'bg-success-500'
			: confidencePercent >= 40
				? 'bg-warning-500'
				: 'bg-error-500'
	);

	const riskLevel = $derived(
		option.risk_summary
			? option.risk_summary.toLowerCase().includes('high')
				? 'error'
				: option.risk_summary.toLowerCase().includes('low')
					? 'success'
					: 'warning'
			: 'neutral'
	);

	const riskColor = $derived(
		riskLevel === 'error'
			? 'text-error-500'
			: riskLevel === 'success'
				? 'text-success-500'
				: 'text-warning-500'
	);
</script>

<button
	type="button"
	class="w-full text-left rounded-xl border-2 p-5 transition-all hover:shadow-md {selected
		? 'border-brand-500 bg-brand-50 dark:bg-brand-950 shadow-md'
		: 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 hover:border-neutral-300 dark:hover:border-neutral-600'}"
	{onclick}
>
	<!-- Header -->
	<div class="flex items-start justify-between gap-3">
		<div class="flex-1">
			<h4 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
				{option.label}
			</h4>
			<p class="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
				{option.description}
			</p>
		</div>
		{#if selected}
			<div
				class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500 flex items-center justify-center"
			>
				<svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
				</svg>
			</div>
		{/if}
	</div>

	<!-- Confidence bar -->
	<div class="mt-3">
		<div class="flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400 mb-1">
			<span>Confidence</span>
			<span>{Math.round(option.confidence_range[0] * 100)}–{Math.round(option.confidence_range[1] * 100)}%</span>
		</div>
		<div class="h-2 rounded-full bg-neutral-200 dark:bg-neutral-700">
			<div class="h-full rounded-full {confidenceColor}" style="width: {confidencePercent}%"></div>
		</div>
	</div>

	<!-- Supporting personas -->
	{#if option.supporting_personas.length > 0}
		<div class="mt-3 flex flex-wrap gap-1.5">
			{#each option.supporting_personas as persona (persona)}
				<Badge variant="info" size="sm">{persona}</Badge>
			{/each}
		</div>
	{/if}

	<!-- Tradeoffs -->
	{#if option.tradeoffs.length > 0}
		<div class="mt-3 flex flex-wrap gap-1.5">
			{#each option.tradeoffs as tradeoff (tradeoff)}
				<span class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-warning-100 text-warning-700 dark:bg-warning-900 dark:text-warning-300">
					{tradeoff}
				</span>
			{/each}
		</div>
	{/if}

	<!-- Constraint alignment badges -->
	{#if option.constraint_alignment && Object.keys(option.constraint_alignment).length > 0}
		<div class="mt-3 flex flex-wrap gap-1.5">
			{#each Object.entries(option.constraint_alignment) as [constraint, status] (constraint)}
				{@const badgeClass =
					status === 'pass'
						? 'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300'
						: status === 'violation'
							? 'bg-error-100 text-error-700 dark:bg-error-900 dark:text-error-300'
							: 'bg-warning-100 text-warning-700 dark:bg-warning-900 dark:text-warning-300'}
				<span class="inline-flex items-center px-2 py-0.5 rounded text-xs {badgeClass}">
					{status === 'pass' ? '✓' : status === 'violation' ? '✗' : '⚠'} {constraint}
				</span>
			{/each}
		</div>
	{/if}

	<!-- Risk -->
	{#if option.risk_summary}
		<div class="mt-3 flex items-start gap-2">
			<AlertTriangle class="w-4 h-4 mt-0.5 flex-shrink-0 {riskColor}" />
			<span class="text-xs text-neutral-600 dark:text-neutral-400">{option.risk_summary}</span>
		</div>
	{/if}

	<!-- Conditions (collapsible) -->
	{#if option.conditions.length > 0}
		<button
			type="button"
			class="mt-3 flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300"
			onclick={(e) => {
				e.stopPropagation();
				showConditions = !showConditions;
			}}
		>
			{#if showConditions}
				<ChevronUp class="w-3 h-3" />
			{:else}
				<ChevronDown class="w-3 h-3" />
			{/if}
			{option.conditions.length} condition{option.conditions.length > 1 ? 's' : ''}
		</button>
		{#if showConditions}
			<ul class="mt-1 pl-4 space-y-0.5">
				{#each option.conditions as condition (condition)}
					<li class="text-xs text-neutral-600 dark:text-neutral-400 list-disc">{condition}</li>
				{/each}
			</ul>
		{/if}
	{/if}
</button>
