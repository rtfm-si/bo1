<script lang="ts">
	/**
	 * MetricCalculatorModal - Q&A guided metric calculation
	 * Walks user through questions to derive metric values
	 */
	import Modal from '$lib/components/ui/Modal.svelte';
	import { Button } from '$lib/components/ui/shadcn/button';
	import { Input } from '$lib/components/ui/shadcn/input';
	import {
		apiClient,
		type MetricQuestionDef,
		type MetricFormulaResponse
	} from '$lib/api/client';
	import { preferredCurrency } from '$lib/stores/preferences';
	import { getCurrencySymbol } from '$lib/utils/currency';

	interface Props {
		open?: boolean;
		onClose: () => void;
		onCalculated?: (metricKey: string, value: number, unit: string) => void;
	}

	let {
		open = $bindable(false),
		onClose,
		onCalculated
	}: Props = $props();

	// State
	let step = $state<'select' | 'questions' | 'result'>('select');
	let selectedMetric = $state<string | null>(null);
	let availableMetrics = $state<string[]>([]);
	let formula = $state<MetricFormulaResponse | null>(null);
	let answers = $state<Record<string, string | number>>({});
	let calculatedValue = $state<number | null>(null);
	let resultUnit = $state<string>('');
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	// Metric display names
	const metricDisplayNames: Record<string, string> = {
		mrr: 'Monthly Recurring Revenue (MRR)',
		arr: 'Annual Recurring Revenue (ARR)',
		burn_rate: 'Burn Rate',
		runway: 'Runway',
		gross_margin: 'Gross Margin',
		churn: 'Churn Rate',
		nps: 'Net Promoter Score (NPS)',
		cac: 'Customer Acquisition Cost (CAC)',
		ltv: 'Customer Lifetime Value (LTV)',
		ltv_cac_ratio: 'LTV:CAC Ratio',
		aov: 'Average Order Value (AOV)',
		conversion_rate: 'Conversion Rate',
		return_rate: 'Return Rate'
	};

	// Load available metrics when modal opens
	$effect(() => {
		if (open && availableMetrics.length === 0) {
			loadAvailableMetrics();
		}
	});

	// Reset state when modal closes
	$effect(() => {
		if (!open) {
			setTimeout(() => {
				step = 'select';
				selectedMetric = null;
				formula = null;
				answers = {};
				calculatedValue = null;
				resultUnit = '';
				error = null;
			}, 300);
		}
	});

	async function loadAvailableMetrics() {
		isLoading = true;
		error = null;
		try {
			const response = await apiClient.getCalculableMetrics();
			availableMetrics = response.metrics;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load metrics';
		} finally {
			isLoading = false;
		}
	}

	async function selectMetric(metricKey: string) {
		selectedMetric = metricKey;
		isLoading = true;
		error = null;
		try {
			formula = await apiClient.getMetricQuestions(metricKey);
			// Initialize answers
			answers = {};
			for (const q of formula.questions) {
				answers[q.id] = '';
			}
			step = 'questions';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load questions';
		} finally {
			isLoading = false;
		}
	}

	async function calculate() {
		if (!selectedMetric || !formula) return;

		// Validate all answers are filled
		for (const q of formula.questions) {
			const val = answers[q.id];
			if (val === '' || val === undefined || val === null) {
				error = `Please answer: ${q.question}`;
				return;
			}
			const numVal = typeof val === 'number' ? val : parseFloat(val);
			if (isNaN(numVal)) {
				error = `Please enter a valid number for: ${q.question}`;
				return;
			}
		}

		isLoading = true;
		error = null;
		try {
			const answersList = Object.entries(answers).map(([question_id, value]) => ({
				question_id,
				value: typeof value === 'number' ? value : parseFloat(value)
			}));

			const response = await apiClient.calculateMetric(selectedMetric, {
				answers: answersList,
				save_insight: true
			});

			if (response.success && response.calculated_value != null) {
				calculatedValue = response.calculated_value;
				resultUnit = response.result_unit || '';
				step = 'result';
			} else {
				error = response.error || 'Calculation failed';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Calculation failed';
		} finally {
			isLoading = false;
		}
	}

	function formatResult(value: number, unit: string): string {
		const currencySymbol = getCurrencySymbol($preferredCurrency);
		switch (unit) {
			case '$':
				return `${currencySymbol}${value.toLocaleString()}`;
			case '%':
				return `${value.toFixed(1)}%`;
			case 'months':
				return `${value.toFixed(1)} months`;
			case 'ratio':
				return `${value.toFixed(2)}:1`;
			case 'score':
				return `${value.toFixed(0)}`;
			default:
				return value.toLocaleString();
		}
	}

	function useValue() {
		if (selectedMetric && calculatedValue !== null) {
			onCalculated?.(selectedMetric, calculatedValue, resultUnit);
		}
		handleClose();
	}

	function goBack() {
		if (step === 'questions') {
			step = 'select';
			formula = null;
			answers = {};
		} else if (step === 'result') {
			step = 'questions';
		}
	}

	function handleClose() {
		open = false;
		onClose();
	}
</script>

<Modal bind:open title="Calculate a Metric" size="md" onclose={handleClose}>
	<div class="space-y-4">
		{#if error}
			<div class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
				<p class="text-sm text-red-700 dark:text-red-300">{error}</p>
			</div>
		{/if}

		{#if isLoading && step === 'select'}
			<div class="flex items-center justify-center py-8">
				<div class="animate-spin h-6 w-6 border-2 border-brand-600 border-t-transparent rounded-full"></div>
			</div>
		{:else if step === 'select'}
			<!-- Step 1: Select Metric -->
			<div>
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
					Choose a metric to calculate. We'll guide you through the questions to derive the value.
				</p>
				<div class="grid gap-2">
					{#each availableMetrics as metric}
						<button
							type="button"
							onclick={() => selectMetric(metric)}
							class="w-full text-left p-3 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
							disabled={isLoading}
						>
							<span class="font-medium text-neutral-900 dark:text-white">
								{metricDisplayNames[metric] || metric.toUpperCase()}
							</span>
						</button>
					{/each}
				</div>
			</div>
		{:else if step === 'questions' && formula}
			<!-- Step 2: Answer Questions -->
			<div>
				<div class="flex items-center gap-2 mb-4">
					<button
						type="button"
						onclick={goBack}
						class="p-1 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
						</svg>
					</button>
					<h3 class="font-medium text-neutral-900 dark:text-white">
						{metricDisplayNames[selectedMetric!] || selectedMetric!.toUpperCase()}
					</h3>
				</div>

				<div class="space-y-4">
					{#each formula.questions as question}
						<div>
							<label for={question.id} class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
								{question.question}
							</label>
							<div class="flex items-center gap-2">
								{#if question.input_type === 'currency'}
									<span class="text-neutral-400">{getCurrencySymbol($preferredCurrency)}</span>
								{/if}
								<Input
									id={question.id}
									type="number"
									bind:value={answers[question.id]}
									placeholder={question.placeholder}
									class="flex-1"
									disabled={isLoading}
								/>
								{#if question.input_type === 'percent'}
									<span class="text-neutral-400">%</span>
								{/if}
							</div>
							{#if question.help_text}
								<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">{question.help_text}</p>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{:else if step === 'result'}
			<!-- Step 3: Show Result -->
			<div>
				<div class="flex items-center gap-2 mb-4">
					<button
						type="button"
						onclick={goBack}
						class="p-1 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
						</svg>
					</button>
					<h3 class="font-medium text-neutral-900 dark:text-white">
						{metricDisplayNames[selectedMetric!] || selectedMetric!.toUpperCase()}
					</h3>
				</div>

				<div class="text-center py-6">
					<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-2">Calculated Value</p>
					<p class="text-4xl font-bold text-brand-600 dark:text-brand-400">
						{formatResult(calculatedValue!, resultUnit)}
					</p>
				</div>

				<div class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
					<div class="flex items-center gap-2">
						<svg class="w-5 h-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
						</svg>
						<p class="text-sm text-green-700 dark:text-green-300">
							Calculation saved to your insights
						</p>
					</div>
				</div>
			</div>
		{/if}
	</div>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			{#if step === 'select'}
				<Button variant="outline" onclick={handleClose}>
					Cancel
				</Button>
			{:else if step === 'questions'}
				<Button variant="outline" onclick={handleClose}>
					Cancel
				</Button>
				<Button variant="default" onclick={calculate} disabled={isLoading}>
					{#if isLoading}
						<svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Calculating...
					{:else}
						Calculate
					{/if}
				</Button>
			{:else if step === 'result'}
				<Button variant="outline" onclick={handleClose}>
					Close
				</Button>
				<Button variant="default" onclick={useValue}>
					Use This Value
				</Button>
			{/if}
		</div>
	{/snippet}
</Modal>
