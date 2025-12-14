<script lang="ts">
	/**
	 * MeetingCostCalculator Component - Projected meeting cost calculator widget
	 *
	 * Calculates and compares traditional meeting costs vs Bo1 meeting costs
	 * to demonstrate potential savings.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { CostCalculatorDefaults } from '$lib/api/types';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import ChevronDown from 'lucide-svelte/icons/chevron-down';
	import ChevronUp from 'lucide-svelte/icons/chevron-up';
	import Calculator from 'lucide-svelte/icons/calculator';
	import Save from 'lucide-svelte/icons/save';

	// State
	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let expanded = $state(false);
	let saveSuccess = $state(false);

	// Calculator inputs (match CostCalculatorDefaults)
	let avgHourlyRate = $state(75);
	let participants = $state(5);
	let durationMins = $state(60);
	let prepMins = $state(30);

	// Bo1 meeting cost estimate (simplified - based on typical LLM costs)
	// In reality this could come from tier data or actual usage
	const BO1_COST_PER_MEETING = 0.15; // Average cost per Bo1 meeting

	// Derived calculations
	const traditionalCost = $derived.by(() => {
		// Total person-hours: participants × (duration + prep time)
		const totalMinutes = participants * (durationMins + prepMins);
		const totalHours = totalMinutes / 60;
		return totalHours * avgHourlyRate;
	});

	const savings = $derived.by(() => {
		return Math.max(0, traditionalCost - BO1_COST_PER_MEETING);
	});

	const savingsPercent = $derived.by(() => {
		if (traditionalCost <= 0) return 0;
		return ((traditionalCost - BO1_COST_PER_MEETING) / traditionalCost) * 100;
	});

	// Format currency
	function formatCurrency(value: number): string {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD',
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		}).format(value);
	}

	// Format percentage
	function formatPercent(value: number): string {
		return `${Math.round(value)}%`;
	}

	// Load user defaults
	async function loadDefaults() {
		try {
			loading = true;
			error = null;
			const defaults = await apiClient.getCostCalculatorDefaults();
			avgHourlyRate = defaults.avg_hourly_rate;
			participants = defaults.typical_participants;
			durationMins = defaults.typical_duration_mins;
			prepMins = defaults.typical_prep_mins;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load defaults';
		} finally {
			loading = false;
		}
	}

	// Save user defaults
	async function saveDefaults() {
		try {
			saving = true;
			error = null;
			saveSuccess = false;
			await apiClient.updateCostCalculatorDefaults({
				avg_hourly_rate: avgHourlyRate,
				typical_participants: participants,
				typical_duration_mins: durationMins,
				typical_prep_mins: prepMins
			});
			saveSuccess = true;
			setTimeout(() => (saveSuccess = false), 3000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save defaults';
		} finally {
			saving = false;
		}
	}

	onMount(() => {
		loadDefaults();
	});
</script>

<BoCard variant="bordered" padding="md">
	{#snippet header()}
		<button
			class="w-full flex items-center justify-between text-left cursor-pointer"
			onclick={() => (expanded = !expanded)}
		>
			<div class="flex items-center gap-2">
				<Calculator class="w-5 h-5 text-brand-600 dark:text-brand-400" />
				<h3 class="text-base font-medium text-neutral-900 dark:text-neutral-100">
					Meeting Cost Calculator
				</h3>
			</div>
			{#if expanded}
				<ChevronUp class="w-5 h-5 text-neutral-500" />
			{:else}
				<ChevronDown class="w-5 h-5 text-neutral-500" />
			{/if}
		</button>
	{/snippet}

	{#if loading}
		<div class="flex items-center justify-center py-4">
			<Spinner size="sm" />
		</div>
	{:else if !expanded}
		<!-- Collapsed summary view -->
		<div class="flex items-center justify-between py-2">
			<span class="text-sm text-neutral-600 dark:text-neutral-400">
				Potential savings per meeting
			</span>
			<div class="flex items-center gap-2">
				<span class="text-lg font-semibold text-success-600 dark:text-success-400">
					{formatCurrency(savings)}
				</span>
				<Badge variant="success">{formatPercent(savingsPercent)}</Badge>
			</div>
		</div>
	{:else}
		<!-- Expanded calculator view -->
		<div class="space-y-4 pt-2">
			{#if error}
				<div class="text-sm text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/20 p-2 rounded">
					{error}
				</div>
			{/if}

			<!-- Input sliders -->
			<div class="space-y-3">
				<!-- Participants -->
				<div class="space-y-1">
					<div class="flex justify-between text-sm">
						<label for="participants" class="text-neutral-600 dark:text-neutral-400">
							Participants
						</label>
						<span class="font-medium text-neutral-900 dark:text-neutral-100">{participants}</span>
					</div>
					<input
						id="participants"
						type="range"
						min="1"
						max="20"
						bind:value={participants}
						class="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-brand-600"
					/>
				</div>

				<!-- Hourly Rate -->
				<div class="space-y-1">
					<div class="flex justify-between text-sm">
						<label for="hourlyRate" class="text-neutral-600 dark:text-neutral-400">
							Avg hourly rate
						</label>
						<span class="font-medium text-neutral-900 dark:text-neutral-100">
							{formatCurrency(avgHourlyRate)}/hr
						</span>
					</div>
					<input
						id="hourlyRate"
						type="range"
						min="10"
						max="500"
						step="5"
						bind:value={avgHourlyRate}
						class="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-brand-600"
					/>
				</div>

				<!-- Meeting Duration -->
				<div class="space-y-1">
					<div class="flex justify-between text-sm">
						<label for="duration" class="text-neutral-600 dark:text-neutral-400">
							Meeting duration
						</label>
						<span class="font-medium text-neutral-900 dark:text-neutral-100">{durationMins} min</span>
					</div>
					<input
						id="duration"
						type="range"
						min="15"
						max="180"
						step="15"
						bind:value={durationMins}
						class="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-brand-600"
					/>
				</div>

				<!-- Prep Time -->
				<div class="space-y-1">
					<div class="flex justify-between text-sm">
						<label for="prepTime" class="text-neutral-600 dark:text-neutral-400">
							Prep time per person
						</label>
						<span class="font-medium text-neutral-900 dark:text-neutral-100">{prepMins} min</span>
					</div>
					<input
						id="prepTime"
						type="range"
						min="0"
						max="120"
						step="5"
						bind:value={prepMins}
						class="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-brand-600"
					/>
				</div>
			</div>

			<!-- Cost comparison -->
			<div class="border-t border-neutral-200 dark:border-neutral-700 pt-4 space-y-3">
				<div class="flex justify-between items-center">
					<span class="text-sm text-neutral-600 dark:text-neutral-400">Traditional meeting cost</span>
					<span class="font-medium text-neutral-900 dark:text-neutral-100">
						{formatCurrency(traditionalCost)}
					</span>
				</div>
				<div class="flex justify-between items-center">
					<span class="text-sm text-neutral-600 dark:text-neutral-400">Bo1 meeting cost</span>
					<span class="font-medium text-success-600 dark:text-success-400">
						{formatCurrency(BO1_COST_PER_MEETING)}
					</span>
				</div>
				<div
					class="flex justify-between items-center bg-success-50 dark:bg-success-900/20 p-3 rounded-lg"
				>
					<span class="font-medium text-success-700 dark:text-success-300">Your savings</span>
					<div class="flex items-center gap-2">
						<span class="text-xl font-bold text-success-600 dark:text-success-400">
							{formatCurrency(savings)}
						</span>
						<Badge variant="success">{formatPercent(savingsPercent)}</Badge>
					</div>
				</div>
			</div>

			<!-- Formula explanation -->
			<details class="text-xs text-neutral-500 dark:text-neutral-400">
				<summary class="cursor-pointer hover:text-neutral-700 dark:hover:text-neutral-300">
					How is this calculated?
				</summary>
				<p class="mt-2 pl-4">
					Traditional cost = Participants × (Duration + Prep time) × Hourly rate
					<br />
					({participants} × ({durationMins} + {prepMins}) min ÷ 60) × {formatCurrency(avgHourlyRate)}/hr = {formatCurrency(traditionalCost)}
				</p>
			</details>

			<!-- Save button -->
			<div class="flex items-center justify-between pt-2">
				{#if saveSuccess}
					<span class="text-sm text-success-600 dark:text-success-400">Defaults saved!</span>
				{:else}
					<span class="text-xs text-neutral-500 dark:text-neutral-400">
						Save these values as your defaults
					</span>
				{/if}
				<BoButton
					variant="secondary"
					size="sm"
					disabled={saving}
					onclick={saveDefaults}
				>
					{#if saving}
						<Spinner size="xs" class="mr-1" />
						Saving...
					{:else}
						<Save class="w-4 h-4 mr-1" />
						Save Defaults
					{/if}
				</BoButton>
			</div>
		</div>
	{/if}
</BoCard>
