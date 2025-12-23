<script lang="ts">
	/**
	 * Strategic Context - Layer 2 (Products, Competitors, ICP)
	 * Deep strategic intelligence for better expert recommendations.
	 */
	import { onMount } from 'svelte';
	import { apiClient, type MarketTrend, type DetectedCompetitor } from '$lib/api/client';
	import type { UserContext } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Dropdown, { type DropdownItem } from '$lib/components/ui/Dropdown.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';

	// Form state - Value Proposition & Positioning
	let mainValueProposition = $state('');
	let brandPositioning = $state('');
	let brandTone = $state<string | undefined>(undefined);
	let pricingModel = $state('');

	// Form state - Competitors (stored as comma-separated string for simplicity)
	let competitorsText = $state('');
	let detectedCompetitors = $state<string[]>([]);

	// Form state - ICP
	let idealCustomerProfile = $state('');
	let targetGeography = $state('');
	let teamSize = $state<string | undefined>(undefined);

	// Form state - Constraints
	let budgetConstraints = $state('');
	let timeConstraints = $state('');
	let regulatoryConstraints = $state('');

	// Market Trends state
	let marketTrends = $state<MarketTrend[]>([]);

	// UI state
	let isLoading = $state(true);
	let isSaving = $state(false);
	let saveError = $state<string | null>(null);
	let saveSuccess = $state(false);
	let isDetectingCompetitors = $state(false);
	let isRefreshingTrends = $state(false);
	let detectError = $state<string | null>(null);
	let trendsError = $state<string | null>(null);

	// Dropdown options
	const brandToneOptions: DropdownItem[] = [
		{ value: 'professional', label: 'Professional', icon: '👔' },
		{ value: 'friendly', label: 'Friendly', icon: '😊' },
		{ value: 'technical', label: 'Technical', icon: '🔧' },
		{ value: 'casual', label: 'Casual', icon: '🎉' },
		{ value: 'authoritative', label: 'Authoritative', icon: '📚' }
	];

	const teamSizeOptions: DropdownItem[] = [
		{ value: 'solo', label: 'Solo Founder', icon: '👤' },
		{ value: 'small (2-5)', label: 'Small (2-5)', icon: '👥' },
		{ value: 'medium (6-20)', label: 'Medium (6-20)', icon: '🏢' },
		{ value: 'large (20+)', label: 'Large (20+)', icon: '🏛️' }
	];

	onMount(async () => {
		try {
			const response = await apiClient.getUserContext();
			if (response.exists && response.context) {
				const ctx = response.context;
				// Value Proposition
				mainValueProposition = ctx.main_value_proposition || '';
				brandPositioning = ctx.brand_positioning || '';
				brandTone = ctx.brand_tone ?? undefined;
				pricingModel = ctx.pricing_model || '';
				// Competitors
				competitorsText = ctx.competitors || '';
				detectedCompetitors = ctx.detected_competitors || [];
				// ICP
				idealCustomerProfile = ctx.ideal_customer_profile || '';
				targetGeography = ctx.target_geography || '';
				teamSize = ctx.team_size ?? undefined;
				// Constraints
				budgetConstraints = ctx.budget_constraints || '';
				timeConstraints = ctx.time_constraints || '';
				regulatoryConstraints = ctx.regulatory_constraints || '';
			}
		} catch (error) {
			console.error('Failed to load context:', error);
		} finally {
			isLoading = false;
		}
	});

	async function handleSave() {
		isSaving = true;
		saveError = null;
		saveSuccess = false;

		try {
			// First get existing context to merge
			const existingResponse = await apiClient.getUserContext();
			const existingContext = existingResponse.context || {};

			const context: Partial<UserContext> = {
				...existingContext,
				// Value Proposition
				main_value_proposition: mainValueProposition.trim() || undefined,
				brand_positioning: brandPositioning.trim() || undefined,
				brand_tone: brandTone,
				pricing_model: pricingModel.trim() || undefined,
				// Competitors
				competitors: competitorsText.trim() || undefined,
				detected_competitors: detectedCompetitors.length > 0 ? detectedCompetitors : undefined,
				// ICP
				ideal_customer_profile: idealCustomerProfile.trim() || undefined,
				target_geography: targetGeography.trim() || undefined,
				team_size: teamSize,
				// Constraints
				budget_constraints: budgetConstraints.trim() || undefined,
				time_constraints: timeConstraints.trim() || undefined,
				regulatory_constraints: regulatoryConstraints.trim() || undefined
			};

			await apiClient.updateUserContext(context as UserContext);
			saveSuccess = true;

			setTimeout(() => {
				saveSuccess = false;
			}, 3000);
		} catch (error) {
			saveError = error instanceof Error ? error.message : 'Failed to save context';
		} finally {
			isSaving = false;
		}
	}

	function addDetectedCompetitor(name: string) {
		if (name && !detectedCompetitors.includes(name)) {
			detectedCompetitors = [...detectedCompetitors, name];
		}
	}

	function removeDetectedCompetitor(index: number) {
		detectedCompetitors = detectedCompetitors.filter((_, i) => i !== index);
	}

	async function handleDetectCompetitors() {
		isDetectingCompetitors = true;
		detectError = null;

		try {
			const response = await apiClient.detectCompetitors();
			if (response.success && response.competitors.length > 0) {
				// Add newly detected competitors to the list
				const newNames = response.competitors.map((c) => c.name);
				const existingNames = new Set(detectedCompetitors);
				const uniqueNew = newNames.filter((name) => !existingNames.has(name));
				detectedCompetitors = [...detectedCompetitors, ...uniqueNew];
			} else if (!response.success) {
				detectError = response.error || 'Failed to detect competitors';
			} else {
				detectError = 'No competitors found. Try adding more context about your industry.';
			}
		} catch (error) {
			detectError = error instanceof Error ? error.message : 'Failed to detect competitors';
		} finally {
			isDetectingCompetitors = false;
		}
	}

	async function handleRefreshTrends() {
		isRefreshingTrends = true;
		trendsError = null;

		try {
			const response = await apiClient.refreshTrends();
			if (response.success) {
				marketTrends = response.trends;
			} else {
				trendsError = response.error || 'Failed to fetch trends';
			}
		} catch (error) {
			trendsError = error instanceof Error ? error.message : 'Failed to fetch trends';
		} finally {
			isRefreshingTrends = false;
		}
	}
</script>

<svelte:head>
	<title>Strategic Context - Board of One</title>
</svelte:head>

{#if isLoading}
	<div class="flex items-center justify-center py-12">
		<div class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"></div>
	</div>
{:else}
	<div class="space-y-6">
		<!-- Alerts -->
		{#if saveSuccess}
			<Alert variant="success">
				Your strategic context has been saved successfully.
			</Alert>
		{/if}

		{#if saveError}
			<Alert variant="error">
				{saveError}
			</Alert>
		{/if}

		<!-- Header -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-2">
				Strategic Context
			</h2>
			<p class="text-slate-600 dark:text-slate-400">
				Deep strategic intelligence for better expert recommendations. This information helps our AI experts understand your competitive position and target customers.
			</p>
		</div>

		<!-- Value Proposition Section -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="flex items-center gap-3 mb-4">
				<span class="text-2xl">💎</span>
				<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
					Value Proposition & Positioning
				</h3>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div class="md:col-span-2">
					<label
						for="value-proposition"
						class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
					>
						Main Value Proposition
					</label>
					<textarea
						id="value-proposition"
						bind:value={mainValueProposition}
						placeholder="What unique value do you provide to customers? e.g., 'We help B2B SaaS companies reduce churn by 30% through predictive analytics'"
						rows="3"
						class="w-full px-4 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-200"
					></textarea>
					<p class="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
						Your unique value proposition in one sentence
					</p>
				</div>

				<div class="md:col-span-2">
					<label
						for="brand-positioning"
						class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
					>
						Brand Positioning
					</label>
					<textarea
						id="brand-positioning"
						bind:value={brandPositioning}
						placeholder="How do you want to be perceived in the market? e.g., 'The most developer-friendly analytics platform for modern data teams'"
						rows="2"
						class="w-full px-4 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-200"
					></textarea>
				</div>

				<div>
					<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
						Brand Tone
					</span>
					<Dropdown
						items={brandToneOptions}
						bind:value={brandTone}
						placeholder="Select your brand voice"
					/>
				</div>

				<Input
					label="Pricing Model"
					placeholder="e.g., Subscription, Freemium, Usage-based, One-time"
					bind:value={pricingModel}
					helperText="How do you charge customers?"
				/>
			</div>
		</div>

		<!-- Competitors Section -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-3">
					<span class="text-2xl">🎯</span>
					<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
						Competitors
					</h3>
				</div>
				<Button
					variant="outline"
					size="sm"
					onclick={handleDetectCompetitors}
					disabled={isDetectingCompetitors}
					loading={isDetectingCompetitors}
				>
					{isDetectingCompetitors ? 'Detecting...' : 'Auto-Detect'}
				</Button>
			</div>

			{#if detectError}
				<Alert variant="warning" class="mb-4">
					{detectError}
				</Alert>
			{/if}

			<div class="space-y-4">
				<div>
					<label
						for="competitors"
						class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
					>
						Known Competitors
					</label>
					<textarea
						id="competitors"
						bind:value={competitorsText}
						placeholder="List your main competitors (one per line or comma-separated)&#10;e.g., Competitor A - Strong in enterprise, weak in SMB&#10;Competitor B - Great UX but expensive"
						rows="4"
						class="w-full px-4 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-200"
					></textarea>
					<p class="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
						Include strengths and weaknesses if known
					</p>
				</div>

				{#if detectedCompetitors.length > 0}
					<div>
						<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
							Auto-Detected Competitors
						</span>
						<div class="flex flex-wrap gap-2">
							{#each detectedCompetitors as competitor, index}
								<span class="inline-flex items-center gap-1 px-3 py-1 bg-slate-100 dark:bg-slate-700 rounded-full text-sm">
									{competitor}
									<button
										type="button"
										onclick={() => removeDetectedCompetitor(index)}
										class="text-slate-500 hover:text-red-500 transition-colors"
										aria-label="Remove competitor"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
										</svg>
									</button>
								</span>
							{/each}
						</div>
						<p class="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
							Click a competitor to remove it from the list
						</p>
					</div>
				{/if}
			</div>
		</div>

		<!-- ICP Section -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="flex items-center gap-3 mb-4">
				<span class="text-2xl">👤</span>
				<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
					Ideal Customer Profile (ICP)
				</h3>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div class="md:col-span-2">
					<label
						for="icp"
						class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
					>
						Ideal Customer Description
					</label>
					<textarea
						id="icp"
						bind:value={idealCustomerProfile}
						placeholder="Describe your ideal customer...&#10;e.g., Mid-market SaaS companies (50-500 employees) with a dedicated customer success team, struggling with churn rates above 5% monthly, and using a modern tech stack."
						rows="4"
						class="w-full px-4 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-200"
					></textarea>
					<p class="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
						Include demographics, firmographics, pain points, and goals
					</p>
				</div>

				<Input
					label="Target Geography"
					placeholder="e.g., North America, Global, EMEA"
					bind:value={targetGeography}
					helperText="Where are your customers located?"
				/>

				<div>
					<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
						Team Size
					</span>
					<Dropdown
						items={teamSizeOptions}
						bind:value={teamSize}
						placeholder="Select your team size"
					/>
				</div>
			</div>
		</div>

		<!-- Constraints Section -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="flex items-center gap-3 mb-4">
				<span class="text-2xl">⚠️</span>
				<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
					Constraints & Considerations
				</h3>
			</div>
			<p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
				Help our experts understand any limitations that should factor into their recommendations.
			</p>

			<div class="grid grid-cols-1 gap-6">
				<div>
					<label
						for="budget-constraints"
						class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
					>
						Budget Constraints
					</label>
					<textarea
						id="budget-constraints"
						bind:value={budgetConstraints}
						placeholder="e.g., Limited marketing budget of $5k/month, bootstrapped, no paid ads budget"
						rows="2"
						class="w-full px-4 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-200"
					></textarea>
				</div>

				<div>
					<label
						for="time-constraints"
						class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
					>
						Time Constraints
					</label>
					<textarea
						id="time-constraints"
						bind:value={timeConstraints}
						placeholder="e.g., Need to launch in 3 months, limited dev resources, only 10 hours/week for marketing"
						rows="2"
						class="w-full px-4 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-200"
					></textarea>
				</div>

				<div>
					<label
						for="regulatory-constraints"
						class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
					>
						Regulatory Constraints
					</label>
					<textarea
						id="regulatory-constraints"
						bind:value={regulatoryConstraints}
						placeholder="e.g., HIPAA compliance required, GDPR for EU customers, SOC 2 in progress"
						rows="2"
						class="w-full px-4 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-200"
					></textarea>
				</div>
			</div>
		</div>

		<!-- Market Trends Section -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-3">
					<span class="text-2xl">📈</span>
					<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
						Market Trends
					</h3>
				</div>
				<Button
					variant="outline"
					size="sm"
					onclick={handleRefreshTrends}
					disabled={isRefreshingTrends}
					loading={isRefreshingTrends}
				>
					{isRefreshingTrends ? 'Refreshing...' : 'Refresh Trends'}
				</Button>
			</div>

			{#if trendsError}
				<Alert variant="warning" class="mb-4">
					{trendsError}
				</Alert>
			{/if}

			{#if marketTrends.length > 0}
				<div class="space-y-3">
					{#each marketTrends as trend}
						<div class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
							<p class="text-sm text-slate-700 dark:text-slate-300">{trend.trend}</p>
							{#if trend.source_url}
								<a
									href={trend.source_url}
									target="_blank"
									rel="noopener noreferrer"
									class="text-xs text-brand-600 dark:text-brand-400 hover:underline mt-1 inline-block"
								>
									{trend.source || 'Source'} →
								</a>
							{/if}
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-sm text-slate-500 dark:text-slate-400">
					Click "Refresh Trends" to fetch the latest market trends for your industry.
					Make sure you've set your industry in the Overview tab first.
				</p>
			{/if}
		</div>

		<!-- Actions -->
		<div class="flex items-center justify-end">
			<Button onclick={handleSave} disabled={isSaving} loading={isSaving}>
				{isSaving ? 'Saving...' : 'Save Strategic Context'}
			</Button>
		</div>

		<!-- Info Box -->
		<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
			<div class="flex gap-3">
				<svg
					class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5"
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
				<div class="text-sm text-blue-900 dark:text-blue-200">
					<p class="font-semibold mb-1">Why strategic context matters</p>
					<p class="text-blue-800 dark:text-blue-300">
						Strategic context enables our experts to provide deeply relevant recommendations.
						By understanding your competitive landscape, ideal customers, and constraints,
						they can offer advice tailored to your specific situation rather than generic guidance.
					</p>
				</div>
			</div>
		</div>
	</div>
{/if}
