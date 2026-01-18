<script lang="ts">
	/**
	 * Tier2AssessmentFlow - Advanced cognitive assessment (unlocked after 3+ meetings)
	 *
	 * Three instruments:
	 * 1. Leverage Instinct Index - How you naturally create power
	 * 2. Value Tension Scan - Your competing priorities
	 * 3. Strategic Time Bias - Short vs long-term orientation
	 */
	import Button from '$lib/components/ui/Button.svelte';

	type Instrument = 'leverage' | 'tension' | 'time_bias';

	interface QuestionOption {
		value: number;
		label: string;
	}

	interface Question {
		key: string;
		instrument: Instrument;
		question: string;
		options: QuestionOption[];
	}

	interface Props {
		instrument: Instrument;
		onComplete: (instrument: Instrument, responses: Record<string, number>) => void;
		onCancel?: () => void;
	}

	let { instrument, onComplete, onCancel }: Props = $props();

	// Questions by instrument
	const leverageQuestions: Question[] = [
		{
			key: 'leverage_structural',
			instrument: 'leverage',
			question: 'When tackling a complex challenge, you instinctively...',
			options: [
				{ value: 0.2, label: 'Jump in and figure it out as you go' },
				{ value: 0.5, label: 'Create a loose plan and adapt' },
				{ value: 0.8, label: 'Design a system or process first' }
			]
		},
		{
			key: 'leverage_informational',
			instrument: 'leverage',
			question: 'Before making a major decision, you typically...',
			options: [
				{ value: 0.2, label: 'Trust your gut and experience' },
				{ value: 0.5, label: 'Do some quick research' },
				{ value: 0.8, label: 'Gather comprehensive data and analysis' }
			]
		},
		{
			key: 'leverage_relational',
			instrument: 'leverage',
			question: 'To get things done, you most often...',
			options: [
				{ value: 0.2, label: 'Do it yourself to ensure quality' },
				{ value: 0.5, label: 'Collaborate with a small trusted group' },
				{ value: 0.8, label: 'Leverage your network and delegate' }
			]
		},
		{
			key: 'leverage_temporal',
			instrument: 'leverage',
			question: 'When an opportunity arises, you prefer to...',
			options: [
				{ value: 0.2, label: 'Act quickly before it passes' },
				{ value: 0.5, label: 'Take a moment to evaluate' },
				{ value: 0.8, label: 'Wait for the optimal moment' }
			]
		}
	];

	const tensionQuestions: Question[] = [
		{
			key: 'tension_autonomy_security',
			instrument: 'tension',
			question: 'If you had to choose, you would prefer...',
			options: [
				{ value: -0.8, label: 'Complete freedom with uncertain income' },
				{ value: 0, label: 'Balance of independence and stability' },
				{ value: 0.8, label: 'Stable income with less autonomy' }
			]
		},
		{
			key: 'tension_mastery_speed',
			instrument: 'tension',
			question: 'When learning a new skill, you tend to...',
			options: [
				{ value: -0.8, label: 'Take time to truly master it' },
				{ value: 0, label: 'Get competent enough, then move on' },
				{ value: 0.8, label: 'Learn just enough to execute quickly' }
			]
		},
		{
			key: 'tension_growth_stability',
			instrument: 'tension',
			question: 'For your business/career, you prioritize...',
			options: [
				{ value: -0.8, label: 'Aggressive growth, even with volatility' },
				{ value: 0, label: 'Sustainable growth with managed risk' },
				{ value: 0.8, label: 'Stability and predictability' }
			]
		}
	];

	const timeBiasQuestions: Question[] = [
		{
			key: 'time_bias_immediate',
			instrument: 'time_bias',
			question: 'When resources are limited, you tend to...',
			options: [
				{ value: 0.2, label: 'Invest in immediate returns' },
				{ value: 0.5, label: 'Balance short and long-term' },
				{ value: 0.8, label: 'Sacrifice now for future gains' }
			]
		},
		{
			key: 'time_bias_planning',
			instrument: 'time_bias',
			question: 'Your planning horizon is typically...',
			options: [
				{ value: 0.2, label: 'Days to weeks' },
				{ value: 0.5, label: 'Months to a year' },
				{ value: 0.8, label: 'Years to decades' }
			]
		},
		{
			key: 'time_bias_gratification',
			instrument: 'time_bias',
			question: 'When offered a reward now vs more later, you...',
			options: [
				{ value: 0.2, label: 'Usually take it now' },
				{ value: 0.5, label: 'Depends on how much more' },
				{ value: 0.8, label: 'Almost always wait for more' }
			]
		}
	];

	// Get questions for selected instrument
	const questions = $derived(
		instrument === 'leverage'
			? leverageQuestions
			: instrument === 'tension'
				? tensionQuestions
				: timeBiasQuestions
	);

	const instrumentLabels: Record<Instrument, string> = {
		leverage: 'Leverage Instinct',
		tension: 'Value Tensions',
		time_bias: 'Time Orientation'
	};

	// State
	let currentQuestionIndex = $state(0);
	let responses = $state<Record<string, number>>({});
	let selectedValue = $state<number | null>(null);

	// Computed
	const currentQuestion = $derived(questions[currentQuestionIndex]);
	const progress = $derived(((currentQuestionIndex + 1) / questions.length) * 100);
	const isLastQuestion = $derived(currentQuestionIndex === questions.length - 1);
	const canProceed = $derived(selectedValue !== null);

	function selectOption(value: number) {
		selectedValue = value;
	}

	function nextQuestion() {
		if (selectedValue === null) return;

		// Save response
		responses[currentQuestion.key] = selectedValue;

		if (isLastQuestion) {
			// For time_bias, compute single score from multiple questions
			if (instrument === 'time_bias') {
				const avgScore =
					Object.values(responses).reduce((a, b) => a + b, 0) / Object.values(responses).length;
				onComplete(instrument, { time_bias_score: avgScore });
			} else {
				onComplete(instrument, responses);
			}
		} else {
			currentQuestionIndex++;
			selectedValue = null;
		}
	}

	function previousQuestion() {
		if (currentQuestionIndex > 0) {
			currentQuestionIndex--;
			selectedValue = responses[questions[currentQuestionIndex].key] ?? null;
		}
	}
</script>

<div class="max-w-xl mx-auto">
	<!-- Progress bar -->
	<div class="mb-6">
		<div class="flex justify-between text-sm text-slate-600 dark:text-slate-400 mb-2">
			<span>{instrumentLabels[instrument]}</span>
			<span>Question {currentQuestionIndex + 1} of {questions.length}</span>
		</div>
		<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
			<div
				class="h-full bg-indigo-600 transition-all duration-300"
				style="width: {progress}%"
			></div>
		</div>
	</div>

	<!-- Question -->
	<div
		class="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm border border-slate-200 dark:border-slate-700"
	>
		<h3 class="text-xl font-semibold text-slate-900 dark:text-white mb-6">
			{currentQuestion.question}
		</h3>

		<!-- Options -->
		<div class="space-y-3">
			{#each currentQuestion.options as option (option.value)}
				<button
					type="button"
					onclick={() => selectOption(option.value)}
					class={[
						'w-full p-4 text-left rounded-lg border-2 transition-all',
						selectedValue === option.value
							? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20'
							: 'border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-700'
					].join(' ')}
				>
					<div class="flex items-center gap-3">
						<div
							class={[
								'w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0',
								selectedValue === option.value
									? 'border-indigo-600 bg-indigo-600'
									: 'border-slate-300 dark:border-slate-600'
							].join(' ')}
						>
							{#if selectedValue === option.value}
								<svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
										clip-rule="evenodd"
									/>
								</svg>
							{/if}
						</div>
						<span class="text-slate-700 dark:text-slate-300">{option.label}</span>
					</div>
				</button>
			{/each}
		</div>
	</div>

	<!-- Navigation -->
	<div class="flex justify-between mt-6">
		<div>
			{#if currentQuestionIndex > 0}
				<Button variant="secondary" onclick={previousQuestion}>Back</Button>
			{:else if onCancel}
				<Button variant="secondary" onclick={onCancel}>Cancel</Button>
			{:else}
				<div></div>
			{/if}
		</div>

		<Button variant="brand" onclick={nextQuestion} disabled={!canProceed}>
			{isLastQuestion ? 'Complete' : 'Next'}
		</Button>
	</div>
</div>
