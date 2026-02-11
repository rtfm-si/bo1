<script lang="ts">
	/**
	 * Business Context Overview - Layer 1 (High-Level Context)
	 * Moved from /settings/context/+page.svelte
	 */
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import { CONTEXT_WELCOME_KEY } from '$lib/stores/tour';
	import { toast } from '$lib/stores/toast';
	import type { BusinessContext, BusinessStage, PrimaryObjective } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Dropdown, { type DropdownItem } from '$lib/components/ui/Dropdown.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import ContextRefreshBanner from '$lib/components/ui/ContextRefreshBanner.svelte';
	import GoalHistory from '$lib/components/context/GoalHistory.svelte';
	import { trackEvent, AnalyticsEvents, trackContextEnriched } from '$lib/utils/analytics';

	import { formatDate } from '$lib/utils/time-formatting';
	// Form state
	let companyName = $state('');
	let websiteUrl = $state('');
	let businessStage = $state<BusinessStage | undefined>(undefined);
	let primaryObjective = $state<PrimaryObjective | undefined>(undefined);
	let northStarGoal = $state('');
	let strategicObjectives = $state<string[]>([]);
	let businessModel = $state('');
	let targetMarket = $state('');
	let productDescription = $state('');
	let industry = $state('');

	// UI state
	let isLoading = $state(true);
	let isEnriching = $state(false);
	let isSaving = $state(false);
	let enrichmentError = $state<string | null>(null);
	let saveError = $state<string | null>(null);
	let saveSuccess = $state(false);
	let enrichedFields = $state<string[]>([]);
	let lastUpdated = $state<string | null>(null);
	let showWelcomeBanner = $state(false);
	let isWelcomeFlow = $state(false);

	// Strategic fields from enrichment (to be saved with context)
	let enrichedStrategicFields = $state<{
		main_value_proposition?: string;
		brand_positioning?: string;
		brand_tone?: string;
		ideal_customer_profile?: string;
		detected_competitors?: string[];
		pricing_model?: string;
	}>({});

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
		// Check for welcome query param (from dashboard redirect for new users)
		if (browser) {
			const welcomeParam = $page.url.searchParams.get('welcome');
			if (welcomeParam === 'true') {
				showWelcomeBanner = true;
				isWelcomeFlow = true;
			} else {
				// Fallback: Check for welcome banner flag (set after tour completion)
				const welcomeFlag = localStorage.getItem(CONTEXT_WELCOME_KEY);
				if (welcomeFlag === 'true') {
					showWelcomeBanner = true;
				}
			}
		}

		try {
			const response = await apiClient.getUserContext();
			if (response.exists && response.context) {
				const ctx = response.context;
				companyName = ctx.company_name || '';
				websiteUrl = ctx.website || '';
				businessStage = ctx.business_stage ?? undefined;
				primaryObjective = ctx.primary_objective ?? undefined;
				northStarGoal = ctx.north_star_goal || '';
				strategicObjectives = ctx.strategic_objectives || [];
				businessModel = ctx.business_model || '';
				targetMarket = ctx.target_market || '';
				productDescription = ctx.product_description || '';
				industry = ctx.industry || '';
			}
			if (response.updated_at) {
				lastUpdated = response.updated_at;
			}
		} catch (error) {
			console.error('Failed to load context:', error);
		} finally {
			isLoading = false;
		}
	});

	function dismissWelcomeBanner() {
		showWelcomeBanner = false;
		if (browser) {
			localStorage.removeItem(CONTEXT_WELCOME_KEY);
		}
	}

	async function enrichFromWebsite() {
		if (!websiteUrl.trim()) return;

		isEnriching = true;
		enrichmentError = null;
		enrichedFields = [];

		try {
			const response = await apiClient.enrichContext(websiteUrl.trim());

			if (response.success && response.context) {
				const ctx = response.context;
				const updated: string[] = [];

				// Update form with enriched data (only if not already set)
				if (ctx.company_name && !companyName) {
					companyName = ctx.company_name;
					updated.push('Company Name');
				}
				if (ctx.business_stage && !businessStage) {
					businessStage = ctx.business_stage;
					updated.push('Business Stage');
				}
				if (ctx.primary_objective && !primaryObjective) {
					primaryObjective = ctx.primary_objective;
					updated.push('Primary Objective');
				}
				if (ctx.business_model && !businessModel) {
					businessModel = ctx.business_model;
					updated.push('Business Model');
				}
				if (ctx.target_market && !targetMarket) {
					targetMarket = ctx.target_market;
					updated.push('Target Market');
				}
				if (ctx.product_description && !productDescription) {
					productDescription = ctx.product_description;
					updated.push('Product Description');
				}
				if (ctx.industry && !industry) {
					industry = ctx.industry;
					updated.push('Industry');
				}

				// Store strategic fields from enrichment to be saved with context
				const strategicUpdates: string[] = [];
				if (ctx.main_value_proposition) {
					enrichedStrategicFields.main_value_proposition = ctx.main_value_proposition;
					strategicUpdates.push('Value Proposition');
				}
				if (ctx.brand_positioning) {
					enrichedStrategicFields.brand_positioning = ctx.brand_positioning;
					strategicUpdates.push('Brand Positioning');
				}
				if (ctx.brand_tone) {
					enrichedStrategicFields.brand_tone = ctx.brand_tone;
					strategicUpdates.push('Brand Tone');
				}
				if (ctx.ideal_customer_profile) {
					enrichedStrategicFields.ideal_customer_profile = ctx.ideal_customer_profile;
					strategicUpdates.push('Ideal Customer Profile');
				}
				if (ctx.detected_competitors && ctx.detected_competitors.length > 0) {
					enrichedStrategicFields.detected_competitors = ctx.detected_competitors;
					strategicUpdates.push(`${ctx.detected_competitors.length} Competitors`);
				}
				if (ctx.pricing_model) {
					enrichedStrategicFields.pricing_model = ctx.pricing_model;
					strategicUpdates.push('Pricing Model');
				}

				if (strategicUpdates.length > 0) {
					updated.push(`Strategic: ${strategicUpdates.join(', ')}`);
				}

				enrichedFields = updated;
				trackContextEnriched({
					source: 'website',
					confidence: response.confidence || 'medium'
				});
			} else if (response.error) {
				enrichmentError = response.error;
			}
		} catch (error) {
			enrichmentError = error instanceof Error ? error.message : 'Failed to enrich from website';
		} finally {
			isEnriching = false;
		}
	}

	async function handleSave() {
		isSaving = true;
		saveError = null;
		saveSuccess = false;

		try {
			const context: Partial<BusinessContext> = {
				company_name: companyName.trim() || undefined,
				website: websiteUrl.trim() || undefined,
				business_stage: businessStage,
				primary_objective: primaryObjective,
				north_star_goal: northStarGoal.trim() || undefined,
				strategic_objectives:
					strategicObjectives.filter((o) => o.trim()).length > 0
						? strategicObjectives.filter((o) => o.trim())
						: undefined,
				business_model: businessModel.trim() || undefined,
				target_market: targetMarket.trim() || undefined,
				product_description: productDescription.trim() || undefined,
				industry: industry.trim() || undefined,
				// Include enriched strategic fields if available
				...enrichedStrategicFields
			};

			await apiClient.updateUserContext(context as BusinessContext);
			// Clear enriched fields after save
			enrichedStrategicFields = {};
			trackEvent(AnalyticsEvents.CONTEXT_UPDATED);

			// If this is the welcome flow (new user first-time setup), redirect to dashboard
			if (isWelcomeFlow) {
				toast.success("Business context saved! Let's start your first meeting.");
				goto('/dashboard');
				return;
			}

			saveSuccess = true;
			lastUpdated = new Date().toISOString();

			// Clear success message after 3 seconds
			setTimeout(() => {
				saveSuccess = false;
			}, 3000);
		} catch (error) {
			saveError = error instanceof Error ? error.message : 'Failed to save context';
		} finally {
			isSaving = false;
		}
	}

	async function handleDelete() {
		if (!confirm('Are you sure you want to delete your business context? This cannot be undone.')) {
			return;
		}

		try {
			await apiClient.deleteUserContext();
			// Reset form
			companyName = '';
			websiteUrl = '';
			businessStage = undefined;
			primaryObjective = undefined;
			northStarGoal = '';
			strategicObjectives = [];
			businessModel = '';
			targetMarket = '';
			productDescription = '';
			industry = '';
			lastUpdated = null;
			saveSuccess = true;
			setTimeout(() => {
				saveSuccess = false;
			}, 3000);
		} catch (error) {
			saveError = error instanceof Error ? error.message : 'Failed to delete context';
		}
	}

</script>

<svelte:head>
	<title>Business Context - Board of One</title>
</svelte:head>

{#if isLoading}
	<div class="flex items-center justify-center py-12">
		<Spinner size="lg" />
	</div>
{:else}
	<div class="space-y-6">
		<!-- Context Refresh Banner -->
		<ContextRefreshBanner />

		<!-- Welcome Banner (shown for new users or after onboarding tour) -->
		{#if showWelcomeBanner}
			<div class="bg-brand-50 dark:bg-brand-900/20 border-2 border-brand-300 dark:border-brand-700 rounded-lg p-5 {isWelcomeFlow ? 'ring-2 ring-brand-400 ring-offset-2 dark:ring-offset-neutral-800' : ''}">
				<div class="flex items-start gap-4">
					<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-100 dark:bg-brand-800 flex items-center justify-center">
						<svg
							class="w-6 h-6 text-brand-600 dark:text-brand-400"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
							/>
						</svg>
					</div>
					<div class="flex-1">
						<h3 class="text-lg font-semibold text-brand-900 dark:text-brand-100 mb-1">
							{isWelcomeFlow ? "Welcome! Let's set up your business context" : 'Welcome! Set up your business context'}
						</h3>
						<p class="text-sm text-brand-700 dark:text-brand-300 mb-3">
							{isWelcomeFlow
								? "Before your first meeting, tell us about your business. This helps our AI experts provide advice tailored to your specific situation."
								: "Adding your business context helps our AI experts provide tailored advice specific to your situation. Fill in your company details below to get more personalized recommendations."}
						</p>
						{#if isWelcomeFlow}
							<p class="text-xs text-brand-600 dark:text-brand-400 flex items-center gap-1">
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
								</svg>
								Fill in at least your industry and product description, then click "Save Changes" to continue.
							</p>
						{/if}
					</div>
					{#if !isWelcomeFlow}
						<button
							onclick={dismissWelcomeBanner}
							class="p-1 text-brand-500 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-200 rounded transition-colors"
							aria-label="Dismiss welcome message"
						>
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
							</svg>
						</button>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Alerts -->
		{#if saveSuccess}
			<Alert variant="success">
				Your business context has been saved successfully.
			</Alert>
		{/if}

		{#if saveError}
			<Alert variant="error">
				{saveError}
			</Alert>
		{/if}

		<!-- Last Updated -->
		{#if lastUpdated}
			<p class="text-sm text-neutral-500 dark:text-neutral-400">
				Last updated: {formatDate(lastUpdated)}
			</p>
		{/if}

		<!-- Company Information Section -->
		<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
				Company Information
			</h2>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<Input
					label="Company Name"
					placeholder="e.g., Acme Corp"
					bind:value={companyName}
					helperText="Your company or project name"
				/>

				<Input
					label="Industry"
					placeholder="e.g., SaaS, Healthcare, E-commerce"
					bind:value={industry}
					helperText="What industry are you in?"
				/>

				<div class="md:col-span-2">
					<div class="flex items-end gap-4">
						<div class="flex-1">
							<Input
								type="url"
								label="Website URL"
								placeholder="https://example.com"
								bind:value={websiteUrl}
								helperText="Your company website"
							/>
						</div>
						{#if websiteUrl.trim()}
							<Button
								variant="secondary"
								onclick={enrichFromWebsite}
								disabled={isEnriching}
								loading={isEnriching}
							>
								{isEnriching ? 'Analyzing...' : 'Auto-fill'}
							</Button>
						{/if}
					</div>

					{#if enrichmentError}
						<p class="mt-2 text-sm text-error-600 dark:text-error-400">{enrichmentError}</p>
					{/if}

					{#if enrichedFields.length > 0}
						<p class="mt-2 text-sm text-success-600 dark:text-success-400">
							Extracted: {enrichedFields.join(', ')}
						</p>
					{/if}
				</div>
			</div>
		</div>

		<!-- Business Details Section -->
		<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
				Business Details
			</h2>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div>
					<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
						Business Stage
					</span>
					<Dropdown
						items={businessStageOptions}
						bind:value={businessStage}
						placeholder="Select your stage"
					/>
				</div>

				<div>
					<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
						Primary Objective
					</span>
					<Dropdown
						items={primaryObjectiveOptions}
						bind:value={primaryObjective}
						placeholder="Select your focus"
					/>
				</div>

				<div class="md:col-span-2">
					<Input
						label="North Star Goal"
						placeholder="e.g., 10K MRR by Q2, 100 paying customers by March"
						bind:value={northStarGoal}
						helperText="Your primary objective for the next 3-6 months"
						maxlength={200}
					/>
				</div>

				<!-- Strategic Objectives -->
				<div class="md:col-span-2">
					<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
						Strategic Objectives
					</span>
					<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-3">
						Define up to 5 supporting objectives that help achieve your north star goal.
					</p>
					<div class="space-y-2">
						{#each strategicObjectives as _, i}
							<div class="flex items-center gap-2">
								<div class="flex-1">
									<Input
										placeholder={`Objective ${i + 1} (e.g., Increase conversion rate)`}
										bind:value={strategicObjectives[i]}
									/>
								</div>
								<button
									type="button"
									onclick={() => {
										strategicObjectives = strategicObjectives.filter((_, idx) => idx !== i);
									}}
									class="p-2 text-error-600 hover:text-error-700 dark:text-error-400 dark:hover:text-error-300 hover:bg-error-50 dark:hover:bg-error-900/20 rounded-md transition-colors"
									aria-label="Remove objective"
								>
									<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</div>
						{/each}
						{#if strategicObjectives.length < 5}
							<button
								type="button"
								onclick={() => {
									strategicObjectives = [...strategicObjectives, ''];
								}}
								class="flex items-center gap-2 text-sm text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 font-medium"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
								</svg>
								Add Objective
							</button>
						{/if}
					</div>
				</div>

				<Input
					label="Business Model"
					placeholder="e.g., B2B SaaS, Marketplace, D2C"
					bind:value={businessModel}
					helperText="How do you make money?"
				/>

				<Input
					label="Target Market"
					placeholder="e.g., SMBs, Enterprise, Consumers"
					bind:value={targetMarket}
					helperText="Who are your customers?"
				/>

				<div class="md:col-span-2">
					<label
						for="product-description"
						class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
					>
						Product Description
					</label>
					<textarea
						id="product-description"
						bind:value={productDescription}
						placeholder="Describe your product or service..."
						rows="3"
						class="w-full px-4 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-200"
					></textarea>
					<p class="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
						Brief description of what you offer
					</p>
				</div>
			</div>
		</div>

		<!-- Goal History -->
		<GoalHistory />

		<!-- Actions -->
		<div class="flex items-center justify-between">
			<Button variant="danger" onclick={handleDelete}>
				Delete Context
			</Button>

			<Button onclick={handleSave} disabled={isSaving} loading={isSaving}>
				{isSaving ? 'Saving...' : 'Save Changes'}
			</Button>
		</div>

		<!-- Info Box -->
		<div class="bg-info-50 dark:bg-info-900/20 border border-info-200 dark:border-info-800 rounded-lg p-4">
			<div class="flex gap-3">
				<svg
					class="w-5 h-5 text-info-600 dark:text-info-400 flex-shrink-0 mt-0.5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<div class="text-sm text-info-900 dark:text-info-200">
					<p class="font-semibold mb-1">Why provide business context?</p>
					<p class="text-info-800 dark:text-info-300">
						Your business context helps our AI experts provide more relevant, tailored advice
						for your specific situation. The more context you provide, the better the
						recommendations will be.
					</p>
				</div>
			</div>
		</div>
	</div>
{/if}
