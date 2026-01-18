<script lang="ts">
	/**
	 * CognitionQuestionFlow - Reusable cognitive assessment questionnaire
	 *
	 * Presents 9 questions (3 per instrument) in a single-question-at-a-time flow.
	 * Used in both onboarding (lite assessment) and settings page.
	 */
	import Button from '$lib/components/ui/Button.svelte';

	interface QuestionOption {
		value: number;
		label: string;
	}

	interface Question {
		key: string;
		instrument: 'gravity' | 'friction' | 'uncertainty';
		question: string;
		options: QuestionOption[];
	}

	// Props
	interface Props {
		onComplete: (responses: Record<string, number>) => void;
		onCancel?: () => void;
		showProgress?: boolean;
	}

	let { onComplete, onCancel, showProgress = true }: Props = $props();

	// Assessment questions
	const questions: Question[] = [
		// Cognitive Gravity Map (3 questions)
		{
			key: 'gravity_time_horizon',
			instrument: 'gravity',
			question: 'When facing a big decision, you typically think about...',
			options: [
				{ value: 0, label: 'What will happen this week or month' },
				{ value: 0.5, label: 'The next quarter or two' },
				{ value: 1, label: 'Where this leads in 1-3 years' }
			]
		},
		{
			key: 'gravity_information_density',
			instrument: 'gravity',
			question: 'Before making a decision, you prefer...',
			options: [
				{ value: 0, label: 'A clear summary and recommendation' },
				{ value: 0.5, label: 'Key points with some supporting data' },
				{ value: 1, label: 'Comprehensive analysis with all the details' }
			]
		},
		{
			key: 'gravity_control_style',
			instrument: 'gravity',
			question: 'For important tasks, you would rather...',
			options: [
				{ value: 0, label: 'Set the direction and let others execute' },
				{ value: 0.5, label: 'Stay involved at key checkpoints' },
				{ value: 1, label: 'Be hands-on throughout the process' }
			]
		},
		// Decision Friction Profile (3 questions)
		{
			key: 'friction_risk_sensitivity',
			instrument: 'friction',
			question: 'Which feels heavier?',
			options: [
				{ value: 0, label: 'Missing an opportunity by being too cautious' },
				{ value: 0.5, label: 'Both feel equally uncomfortable' },
				{ value: 1, label: 'Making a mistake by moving too fast' }
			]
		},
		{
			key: 'friction_cognitive_load',
			instrument: 'friction',
			question: 'When presented with many options...',
			options: [
				{ value: 0, label: 'I enjoy exploring all possibilities' },
				{ value: 0.5, label: 'I narrow down quickly then explore' },
				{ value: 1, label: 'I prefer a shortlist of the best choices' }
			]
		},
		{
			key: 'friction_ambiguity_tolerance',
			instrument: 'friction',
			question: 'When a situation is unclear...',
			options: [
				{ value: 0, label: 'I can move forward with uncertainty' },
				{ value: 0.5, label: 'I need some clarity on key aspects' },
				{ value: 1, label: 'I need to understand it fully before acting' }
			]
		},
		// Uncertainty Posture Matrix (3 questions)
		{
			key: 'uncertainty_threat_lens',
			instrument: 'uncertainty',
			question: 'An unproven idea feels more like...',
			options: [
				{ value: 0, label: 'An exciting opportunity to explore' },
				{ value: 0.5, label: 'Something worth careful evaluation' },
				{ value: 1, label: 'A potential risk to manage' }
			]
		},
		{
			key: 'uncertainty_control_need',
			instrument: 'uncertainty',
			question: 'You feel most comfortable when...',
			options: [
				{ value: 0, label: 'Things can adapt as circumstances change' },
				{ value: 0.5, label: 'There is a flexible framework in place' },
				{ value: 1, label: 'There is a clear plan and structure' }
			]
		},
		{
			key: 'uncertainty_exploration_drive',
			instrument: 'uncertainty',
			question: 'Given the choice, you would rather...',
			options: [
				{ value: 0, label: 'Optimize what is already working' },
				{ value: 0.5, label: 'Improve current approach with new ideas' },
				{ value: 1, label: 'Explore something completely new' }
			]
		}
	];

	// State
	let currentQuestionIndex = $state(0);
	let responses = $state<Record<string, number>>({});
	let selectedValue = $state<number | null>(null);

	// Computed
	const currentQuestion = $derived(questions[currentQuestionIndex]);
	const progress = $derived(((currentQuestionIndex + 1) / questions.length) * 100);
	const isLastQuestion = $derived(currentQuestionIndex === questions.length - 1);
	const canProceed = $derived(selectedValue !== null);

	// Instrument labels for display
	const instrumentLabels: Record<string, string> = {
		gravity: 'Decision Style',
		friction: 'Decision Friction',
		uncertainty: 'Uncertainty Response'
	};

	function selectOption(value: number) {
		selectedValue = value;
	}

	function nextQuestion() {
		if (selectedValue === null) return;

		// Save response
		responses[currentQuestion.key] = selectedValue;

		if (isLastQuestion) {
			// Complete assessment
			onComplete(responses);
		} else {
			// Move to next question
			currentQuestionIndex++;
			selectedValue = null;
		}
	}

	function previousQuestion() {
		if (currentQuestionIndex > 0) {
			currentQuestionIndex--;
			// Restore previous answer if exists
			selectedValue = responses[questions[currentQuestionIndex].key] ?? null;
		}
	}
</script>

<div class="max-w-xl mx-auto">
	<!-- Progress bar -->
	{#if showProgress}
		<div class="mb-6">
			<div class="flex justify-between text-sm text-slate-600 dark:text-slate-400 mb-2">
				<span>{instrumentLabels[currentQuestion.instrument]}</span>
				<span>Question {currentQuestionIndex + 1} of {questions.length}</span>
			</div>
			<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
				<div
					class="h-full bg-brand-600 transition-all duration-300"
					style="width: {progress}%"
				></div>
			</div>
		</div>
	{/if}

	<!-- Question -->
	<div class="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
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
							? 'border-brand-600 bg-brand-50 dark:bg-brand-900/20'
							: 'border-slate-200 dark:border-slate-700 hover:border-brand-300 dark:hover:border-brand-700'
					].join(' ')}
				>
					<div class="flex items-center gap-3">
						<div
							class={[
								'w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0',
								selectedValue === option.value
									? 'border-brand-600 bg-brand-600'
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
				<Button variant="secondary" onclick={previousQuestion}>
					Back
				</Button>
			{:else if onCancel}
				<Button variant="secondary" onclick={onCancel}>
					Cancel
				</Button>
			{:else}
				<div></div>
			{/if}
		</div>

		<Button variant="brand" onclick={nextQuestion} disabled={!canProceed}>
			{isLastQuestion ? 'Complete' : 'Next'}
		</Button>
	</div>
</div>
