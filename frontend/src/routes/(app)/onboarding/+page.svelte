<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import type { UserContext, BusinessStage, PrimaryObjective } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Dropdown, { type DropdownItem } from '$lib/components/ui/Dropdown.svelte';
	import { startOnboardingTour } from '$lib/tours';
	import {
		trackEvent,
		AnalyticsEvents,
		trackOnboardingStarted,
		trackOnboardingCompleted,
		trackContextEnriched
	} from '$lib/utils/analytics';

	// Step state
	let currentStep = $state(1);
	const totalSteps = 4;

	// Form state
	let companyName = $state('');
	let websiteUrl = $state('');
	let businessStage = $state<BusinessStage | undefined>(undefined);
	let primaryObjective = $state<PrimaryObjective | undefined>(undefined);

	// UI state
	let isEnriching = $state(false);
	let isSaving = $state(false);
	let enrichmentError = $state<string | null>(null);
	let enrichedFields = $state<string[]>([]);
	let showTour = $state(false);

	// Dropdown options
	const businessStageOptions: DropdownItem[] = [
		{ value: 'idea', label: 'Idea Stage', icon: '💡' },
		{ value: 'early', label: 'Early Stage', icon: '🌱' },
		{ value: 'growing', label: 'Growing', icon: '📈' },
		{ value: 'scaling', label: 'Scaling', icon: '🚀' }
	];

	const primaryObjectiveOptions: DropdownItem[] = [
		{ value: 'acquire_customers', label: 'Acquire Customers', icon: '👥' },
		{ value: 'improve_retention', label: 'Improve Retention', icon: '🔄' },
		{ value: 'raise_capital', label: 'Raise Capital', icon: '💰' },
		{ value: 'launch_product', label: 'Launch Product', icon: '🚀' },
		{ value: 'reduce_costs', label: 'Reduce Costs', icon: '📉' }
	];

	onMount(async () => {
		trackOnboardingStarted();

		// Check if user already completed onboarding
		try {
			const status = await apiClient.getOnboardingStatus();
			if (status.onboarding_completed) {
				goto('/dashboard');
				return;
			}

			// Load any existing context
			const contextResponse = await apiClient.getUserContext();
			if (contextResponse.exists && contextResponse.context) {
				const ctx = contextResponse.context;
				companyName = ctx.company_name || '';
				websiteUrl = ctx.website || '';
				businessStage = ctx.business_stage;
				primaryObjective = ctx.primary_objective;
			}

			// Show tour for new users
			if (status.is_new_user && !status.tours_completed.includes('onboarding')) {
				showTour = true;
				setTimeout(() => {
					startOnboardingTour(
						() => {
							apiClient.completeTour('onboarding');
							showTour = false;
						},
						() => {
							showTour = false;
						}
					);
				}, 500);
			}
		} catch (error) {
			console.error('Failed to check onboarding status:', error);
		}
	});

	function nextStep() {
		if (currentStep < totalSteps) {
			currentStep++;
			trackEvent('onboarding_step_completed', { step: currentStep - 1 });
		}
	}

	function prevStep() {
		if (currentStep > 1) {
			currentStep--;
		}
	}

	async function enrichFromWebsite() {
		if (!websiteUrl.trim()) return;

		isEnriching = true;
		enrichmentError = null;

		try {
			const response = await apiClient.enrichContext(websiteUrl.trim());

			if (response.success && response.context) {
				// Update form with enriched data
				const ctx = response.context;
				if (ctx.company_name && !companyName) {
					companyName = ctx.company_name;
				}
				if (ctx.business_stage && !businessStage) {
					businessStage = ctx.business_stage;
				}
				if (ctx.primary_objective && !primaryObjective) {
					primaryObjective = ctx.primary_objective;
				}

				enrichedFields = response.fields_enriched;
				trackContextEnriched({
					source: 'website',
					confidence: response.confidence
				});
			}
		} catch (error) {
			enrichmentError = error instanceof Error ? error.message : 'Failed to enrich from website';
		} finally {
			isEnriching = false;
		}
	}

	async function handleSubmit() {
		if (!canComplete) return;

		isSaving = true;

		try {
			// Save context
			const context: Partial<UserContext> = {
				company_name: companyName.trim(),
				website: websiteUrl.trim() || undefined,
				business_stage: businessStage,
				primary_objective: primaryObjective,
				onboarding_completed: true
			};

			await apiClient.updateUserContext(context as UserContext);

			// Mark onboarding step complete
			await apiClient.completeOnboardingStep('business_context');

			trackOnboardingCompleted({ has_context: true });

			// Redirect to dashboard
			goto('/dashboard');
		} catch (error) {
			console.error('Failed to save onboarding:', error);
		} finally {
			isSaving = false;
		}
	}

	async function handleSkip() {
		try {
			await apiClient.skipOnboarding();
			trackEvent(AnalyticsEvents.ONBOARDING_SKIPPED);
			goto('/dashboard');
		} catch (error) {
			console.error('Failed to skip onboarding:', error);
			goto('/dashboard');
		}
	}

	// Validation
	const canProceedStep1 = $derived(companyName.trim().length >= 2);
	const canProceedStep2 = $derived(true); // Website is optional
	const canProceedStep3 = $derived(!!businessStage);
	const canProceedStep4 = $derived(!!primaryObjective);
	const canComplete = $derived(
		canProceedStep1 && canProceedStep2 && canProceedStep3 && canProceedStep4
	);
</script>

<svelte:head>
	<title>Welcome - Board of One</title>
</svelte:head>

<div
	class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800"
>
	<div class="max-w-2xl mx-auto px-4 py-12">
		<!-- Header -->
		<div id="onboarding-welcome" class="text-center mb-8">
			<h1 class="text-3xl font-bold text-slate-900 dark:text-white mb-2">
				Welcome to Board of One
			</h1>
			<p class="text-slate-600 dark:text-slate-400">
				Let's personalize your experience in a few quick steps
			</p>
		</div>

		<!-- Progress indicator -->
		<div class="mb-8">
			<div class="flex items-center justify-between mb-2">
				{#each Array(totalSteps) as _, i (i)}
					<div class="flex items-center">
						<div
							class={[
								'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors',
								currentStep > i + 1
									? 'bg-green-500 text-white'
									: currentStep === i + 1
										? 'bg-brand-600 text-white'
										: 'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
							].join(' ')}
						>
							{#if currentStep > i + 1}
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M5 13l4 4L19 7"
									/>
								</svg>
							{:else}
								{i + 1}
							{/if}
						</div>
						{#if i < totalSteps - 1}
							<div
								class={[
									'w-16 sm:w-24 h-1 mx-2 rounded transition-colors',
									currentStep > i + 1
										? 'bg-green-500'
										: 'bg-slate-200 dark:bg-slate-700'
								].join(' ')}
							></div>
						{/if}
					</div>
				{/each}
			</div>
			<p class="text-center text-sm text-slate-500 dark:text-slate-400">
				Step {currentStep} of {totalSteps}
			</p>
		</div>

		<!-- Form card -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-8"
		>
			<!-- Step 1: Company Name -->
			{#if currentStep === 1}
				<div class="space-y-6">
					<div>
						<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-2">
							What's your company name?
						</h2>
						<p class="text-sm text-slate-600 dark:text-slate-400">
							This helps us personalize your strategic advice.
						</p>
					</div>

					<div id="company-name-input">
						<Input
							label="Company Name"
							placeholder="e.g., Acme Corp"
							bind:value={companyName}
							required
							helperText="Enter your company or project name"
						/>
					</div>

					<div class="flex items-center justify-between pt-4">
						<button
							type="button"
							onclick={handleSkip}
							class="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
						>
							Skip for now
						</button>
						<Button onclick={nextStep} disabled={!canProceedStep1}>
							Continue
						</Button>
					</div>
				</div>
			{/if}

			<!-- Step 2: Website URL -->
			{#if currentStep === 2}
				<div class="space-y-6">
					<div>
						<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-2">
							What's your website?
						</h2>
						<p class="text-sm text-slate-600 dark:text-slate-400">
							We'll automatically extract business details to save you time. (Optional)
						</p>
					</div>

					<div id="website-url-input" class="space-y-4">
						<Input
							type="url"
							label="Website URL"
							placeholder="https://example.com"
							bind:value={websiteUrl}
							helperText="Enter your company website URL"
						/>

						{#if websiteUrl.trim()}
							<Button
								variant="secondary"
								onclick={enrichFromWebsite}
								disabled={isEnriching}
								loading={isEnriching}
							>
								{#if isEnriching}
									Analyzing website...
								{:else}
									Auto-fill from website
								{/if}
							</Button>
						{/if}

						{#if enrichmentError}
							<div
								class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
							>
								<p class="text-sm text-red-700 dark:text-red-300">{enrichmentError}</p>
							</div>
						{/if}

						{#if enrichedFields.length > 0}
							<div
								class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg"
							>
								<p class="text-sm text-green-700 dark:text-green-300">
									Successfully extracted: {enrichedFields.join(', ')}
								</p>
							</div>
						{/if}
					</div>

					<div class="flex items-center justify-between pt-4">
						<Button variant="ghost" onclick={prevStep}>
							Back
						</Button>
						<Button onclick={nextStep}>
							{websiteUrl.trim() ? 'Continue' : 'Skip & Continue'}
						</Button>
					</div>
				</div>
			{/if}

			<!-- Step 3: Business Stage -->
			{#if currentStep === 3}
				<div class="space-y-6">
					<div>
						<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-2">
							What stage is your business at?
						</h2>
						<p class="text-sm text-slate-600 dark:text-slate-400">
							This helps our experts tailor advice to your current situation.
						</p>
					</div>

					<div id="business-stage-select">
						<span
							class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
							id="business-stage-label"
						>
							Business Stage
						</span>
						<Dropdown
							items={businessStageOptions}
							bind:value={businessStage}
							placeholder="Select your business stage"
						/>
					</div>

					<div class="flex items-center justify-between pt-4">
						<Button variant="ghost" onclick={prevStep}>
							Back
						</Button>
						<Button onclick={nextStep} disabled={!canProceedStep3}>
							Continue
						</Button>
					</div>
				</div>
			{/if}

			<!-- Step 4: Primary Objective -->
			{#if currentStep === 4}
				<div class="space-y-6">
					<div>
						<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-2">
							What's your primary objective?
						</h2>
						<p class="text-sm text-slate-600 dark:text-slate-400">
							What are you focused on achieving right now?
						</p>
					</div>

					<div id="primary-objective-select">
						<span
							class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
							id="primary-objective-label"
						>
							Primary Objective
						</span>
						<Dropdown
							items={primaryObjectiveOptions}
							bind:value={primaryObjective}
							placeholder="Select your main focus"
						/>
					</div>

					<div class="flex items-center justify-between pt-4">
						<Button variant="ghost" onclick={prevStep}>
							Back
						</Button>
						<Button onclick={handleSubmit} disabled={!canComplete || isSaving} loading={isSaving}>
							{#if isSaving}
								Saving...
							{:else}
								Get Started
							{/if}
						</Button>
					</div>
				</div>
			{/if}
		</div>

		<!-- Help text -->
		<p class="text-center text-sm text-slate-500 dark:text-slate-400 mt-6">
			You can update these settings anytime in your profile.
		</p>
	</div>
</div>
