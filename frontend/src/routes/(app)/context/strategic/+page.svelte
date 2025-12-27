<script lang="ts">
	/**
	 * Strategic Context - Layer 2 (Products, Competitors, ICP)
	 * Deep strategic intelligence for better expert recommendations.
	 */
	import { onMount } from 'svelte';
	import { apiClient, type MarketTrend, type DetectedCompetitor } from '$lib/api/client';
	import type { UserContext, CompetitorInsight, TrendInsight } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Dropdown, { type DropdownItem } from '$lib/components/ui/Dropdown.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import CompetitorInsightCard from '$lib/components/context/CompetitorInsightCard.svelte';
	import TrendInsightCard from '$lib/components/context/TrendInsightCard.svelte';
	import TrendSummaryCard from '$lib/components/context/TrendSummaryCard.svelte';
	import CompetitorManager from '$lib/components/context/CompetitorManager.svelte';
	import GoalHistory from '$lib/components/context/GoalHistory.svelte';
	import type { ManagedCompetitor } from '$lib/api/types';

	// Trend Summary types (inline until OpenAPI regenerated)
	interface TrendSummary {
		summary: string;
		key_trends: string[];
		opportunities: string[];
		threats: string[];
		generated_at: string;
		industry: string;
		timeframe?: string;
		available_timeframes?: string[];
	}

	type Timeframe = 'now' | '3m' | '12m' | '24m';

	// Form state - Value Proposition & Positioning
	let mainValueProposition = $state('');
	let brandPositioning = $state('');
	let brandTone = $state<string | undefined>(undefined);
	let pricingModel = $state('');

	// Form state - Competitors (stored as comma-separated string for simplicity)
	let competitorsText = $state('');
	let detectedCompetitorNames = $state<string[]>([]);
	let detectedCompetitorData = $state<DetectedCompetitor[]>([]);

	// Managed competitors state
	let managedCompetitors = $state<ManagedCompetitor[]>([]);

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

	// Competitor Insights state
	let competitorInsights = $state<CompetitorInsight[]>([]);
	let insightsTotalCount = $state(0);
	let insightsVisibleCount = $state(0);
	let insightsUpgradePrompt = $state<string | null>(null);
	let generatingInsightFor = $state<string | null>(null);

	// Trend Insights state
	let trendInsights = $state<TrendInsight[]>([]);
	let trendUrlInput = $state('');
	let isAnalyzingTrend = $state(false);
	let isLoadingTrendInsights = $state(false);
	let trendInsightsError = $state<string | null>(null);

	// Trend Summary state (AI-generated industry summary with timeframe support)
	let trendSummary = $state<TrendSummary | null>(null);
	let trendSummaryStale = $state(false);
	let trendSummaryNeedsIndustry = $state(false);
	let isLoadingTrendSummary = $state(false);
	let isRefreshingTrendSummary = $state(false);
	let trendSummaryError = $state<string | null>(null);
	let selectedTimeframe = $state<Timeframe>('now');
	let availableTimeframes = $state<string[]>(['now', '3m']);
	let forecastUpgradePrompt = $state<string | null>(null);
	let canRefreshNow = $state(true);
	let refreshBlockedReason = $state<string | null>(null);

	// UI state
	let isLoading = $state(true);
	let isSaving = $state(false);
	let saveError = $state<string | null>(null);
	let saveSuccess = $state(false);
	let isDetectingCompetitors = $state(false);
	let isRefreshingTrends = $state(false);
	let isLoadingInsights = $state(false);
	let detectError = $state<string | null>(null);
	let trendsError = $state<string | null>(null);
	let insightsError = $state<string | null>(null);

	// Auto-detect status
	let needsCompetitorRefresh = $state(false);
	let competitorCount = $state(0);

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
				detectedCompetitorNames = ctx.detected_competitors || [];
				// ICP
				idealCustomerProfile = ctx.ideal_customer_profile || '';
				targetGeography = ctx.target_geography || '';
				teamSize = ctx.team_size ?? undefined;
				// Constraints
				budgetConstraints = ctx.budget_constraints || '';
				timeConstraints = ctx.time_constraints || '';
				regulatoryConstraints = ctx.regulatory_constraints || '';
			}
			// Get auto-detect status (uses new response fields)
			needsCompetitorRefresh = (response as { needs_competitor_refresh?: boolean }).needs_competitor_refresh ?? false;
			competitorCount = (response as { competitor_count?: number }).competitor_count ?? 0;

			// Load competitor insights, trend insights, and trend summary in parallel
			await Promise.all([loadCompetitorInsights(), loadTrendInsights(), loadTrendSummary()]);
		} catch (error) {
			console.error('Failed to load context:', error);
		} finally {
			isLoading = false;
		}
	});

	async function loadCompetitorInsights() {
		isLoadingInsights = true;
		insightsError = null;
		try {
			const response = await apiClient.listCompetitorInsights();
			if (response.success) {
				competitorInsights = response.insights;
				insightsTotalCount = response.total_count;
				insightsVisibleCount = response.visible_count;
				insightsUpgradePrompt = response.upgrade_prompt;
			} else {
				insightsError = response.error || 'Failed to load insights';
			}
		} catch (error) {
			console.error('Failed to load competitor insights:', error);
			insightsError = error instanceof Error ? error.message : 'Failed to load insights';
		} finally {
			isLoadingInsights = false;
		}
	}

	async function handleGenerateInsight(competitorName: string) {
		generatingInsightFor = competitorName;
		insightsError = null;

		try {
			const response = await apiClient.generateCompetitorInsight(competitorName);
			if (response.success && response.insight) {
				// Reload the full list to get updated tier-gated results
				await loadCompetitorInsights();
			} else {
				insightsError = response.error || 'Failed to generate insight';
			}
		} catch (error) {
			console.error('Failed to generate insight:', error);
			insightsError = error instanceof Error ? error.message : 'Failed to generate insight';
		} finally {
			generatingInsightFor = null;
		}
	}

	async function handleRefreshInsight(competitorName: string) {
		generatingInsightFor = competitorName;
		insightsError = null;

		try {
			const response = await apiClient.generateCompetitorInsight(competitorName, true);
			if (response.success && response.insight) {
				await loadCompetitorInsights();
			} else {
				insightsError = response.error || 'Failed to refresh insight';
			}
		} catch (error) {
			console.error('Failed to refresh insight:', error);
			insightsError = error instanceof Error ? error.message : 'Failed to refresh insight';
		} finally {
			generatingInsightFor = null;
		}
	}

	async function handleDeleteInsight(competitorName: string) {
		try {
			await apiClient.deleteCompetitorInsight(competitorName);
			await loadCompetitorInsights();
		} catch (error) {
			console.error('Failed to delete insight:', error);
			insightsError = error instanceof Error ? error.message : 'Failed to delete insight';
		}
	}

	// Trend Forecast functions (with timeframe support)
	async function loadTrendForecast(timeframe: Timeframe = selectedTimeframe) {
		isLoadingTrendSummary = true;
		trendSummaryError = null;
		forecastUpgradePrompt = null;
		try {
			// 'now' uses the summary endpoint, forecasts use the forecast endpoint
			const endpoint = timeframe === 'now'
				? '/api/v1/context/trends/summary'
				: `/api/v1/context/trends/forecast?timeframe=${timeframe}`;
			const response = await fetch(endpoint, {
				credentials: 'include'
			});
			const data = await response.json();
			if (data.success) {
				trendSummary = data.summary;
				trendSummaryStale = data.stale;
				trendSummaryNeedsIndustry = data.needs_industry;
				// For 'now', derive available timeframes from tier (now is always available)
				availableTimeframes = timeframe === 'now'
					? ['now', ...(data.available_timeframes || ['3m'])]
					: data.available_timeframes || ['now', '3m'];
				forecastUpgradePrompt = data.upgrade_prompt || null;
				// Extract refresh gating fields for "Now" view
				canRefreshNow = data.can_refresh_now ?? true;
				refreshBlockedReason = data.refresh_blocked_reason ?? null;
			} else if (data.upgrade_prompt) {
				// Tier-gated - show upgrade prompt
				forecastUpgradePrompt = data.upgrade_prompt;
				availableTimeframes = data.available_timeframes || ['now', '3m'];
			} else {
				trendSummaryError = data.error || 'Failed to load trend forecast';
			}
		} catch (error) {
			console.error('Failed to load trend forecast:', error);
			trendSummaryError = error instanceof Error ? error.message : 'Failed to load trend forecast';
		} finally {
			isLoadingTrendSummary = false;
		}
	}

	// Alias for backwards compatibility
	const loadTrendSummary = () => loadTrendForecast(selectedTimeframe);

	async function handleRefreshTrendForecast() {
		isRefreshingTrendSummary = true;
		trendSummaryError = null;
		try {
			// 'now' uses the summary refresh endpoint, forecasts use the forecast refresh endpoint
			const endpoint = selectedTimeframe === 'now'
				? '/api/v1/context/trends/summary/refresh'
				: `/api/v1/context/trends/forecast/refresh?timeframe=${selectedTimeframe}`;
			const response = await fetch(endpoint, {
				method: 'POST',
				credentials: 'include'
			});
			const data = await response.json();
			if (data.success && data.summary) {
				trendSummary = data.summary;
				trendSummaryStale = false;
				availableTimeframes = selectedTimeframe === 'now'
					? ['now', ...(data.available_timeframes || ['3m'])]
					: data.available_timeframes || ['now', '3m'];
				forecastUpgradePrompt = null;
			} else if (response.status === 403) {
				trendSummaryError = data.detail || 'Upgrade required to access this timeframe.';
			} else {
				trendSummaryError = data.error || 'Failed to refresh trend forecast';
			}
		} catch (error) {
			console.error('Failed to refresh trend forecast:', error);
			trendSummaryError =
				error instanceof Error ? error.message : 'Failed to refresh trend forecast';
		} finally {
			isRefreshingTrendSummary = false;
		}
	}

	// Alias for backwards compatibility
	const handleRefreshTrendSummary = handleRefreshTrendForecast;

	async function handleTimeframeChange(newTimeframe: Timeframe) {
		if (newTimeframe === selectedTimeframe) return;
		selectedTimeframe = newTimeframe;
		await loadTrendForecast(newTimeframe);
	}

	// Trend Insight functions
	async function loadTrendInsights() {
		isLoadingTrendInsights = true;
		trendInsightsError = null;
		try {
			const response = await apiClient.listTrendInsights();
			if (response.success) {
				trendInsights = response.insights;
			} else {
				trendInsightsError = response.error || 'Failed to load trend insights';
			}
		} catch (error) {
			console.error('Failed to load trend insights:', error);
			trendInsightsError = error instanceof Error ? error.message : 'Failed to load trend insights';
		} finally {
			isLoadingTrendInsights = false;
		}
	}

	async function handleAnalyzeTrend() {
		const url = trendUrlInput.trim();
		if (!url) return;

		isAnalyzingTrend = true;
		trendInsightsError = null;

		try {
			const response = await apiClient.analyzeTrendUrl(url);
			if (response.success && response.insight) {
				// Reload the full list to get updated results
				await loadTrendInsights();
				trendUrlInput = ''; // Clear input on success
			} else {
				trendInsightsError = response.error || 'Failed to analyze trend';
			}
		} catch (error) {
			console.error('Failed to analyze trend:', error);
			trendInsightsError = error instanceof Error ? error.message : 'Failed to analyze trend';
		} finally {
			isAnalyzingTrend = false;
		}
	}

	async function handleRefreshTrendInsight(url: string) {
		isAnalyzingTrend = true;
		trendInsightsError = null;

		try {
			const response = await apiClient.analyzeTrendUrl(url, true);
			if (response.success && response.insight) {
				await loadTrendInsights();
			} else {
				trendInsightsError = response.error || 'Failed to refresh trend insight';
			}
		} catch (error) {
			console.error('Failed to refresh trend insight:', error);
			trendInsightsError =
				error instanceof Error ? error.message : 'Failed to refresh trend insight';
		} finally {
			isAnalyzingTrend = false;
		}
	}

	async function handleDeleteTrendInsight(url: string) {
		try {
			await apiClient.deleteTrendInsight(url);
			await loadTrendInsights();
		} catch (error) {
			console.error('Failed to delete trend insight:', error);
			trendInsightsError =
				error instanceof Error ? error.message : 'Failed to delete trend insight';
		}
	}

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
				detected_competitors: detectedCompetitorNames.length > 0 ? detectedCompetitorNames : undefined,
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
		if (name && !detectedCompetitorNames.includes(name)) {
			detectedCompetitorNames = [...detectedCompetitorNames, name];
		}
	}

	function removeDetectedCompetitor(index: number) {
		detectedCompetitorNames = detectedCompetitorNames.filter((_, i) => i !== index);
		detectedCompetitorData = detectedCompetitorData.filter((_, i) => i !== index);
	}

	async function handleDetectCompetitors() {
		isDetectingCompetitors = true;
		detectError = null;

		try {
			const response = await apiClient.detectCompetitors();
			if (response.success && response.competitors.length > 0) {
				// Add newly detected competitors to the list (with full relevance data)
				const existingNames = new Set(detectedCompetitorNames);
				const uniqueNew = response.competitors.filter((c) => !existingNames.has(c.name));
				detectedCompetitorData = [...detectedCompetitorData, ...uniqueNew];
				detectedCompetitorNames = [...detectedCompetitorNames, ...uniqueNew.map((c) => c.name)];
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

		<!-- Goal History Section -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="flex items-center gap-3 mb-4">
				<span class="text-2xl">🎯</span>
				<div>
					<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
						Goal Evolution
					</h3>
					<p class="text-sm text-slate-500 dark:text-slate-400">
						Track how your north star goal has evolved over time
					</p>
				</div>
			</div>
			<GoalHistory limit={10} />
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

			{#if needsCompetitorRefresh && competitorCount === 0}
				<Alert variant="info" class="mb-4">
					<span>Click <strong>Auto-Detect</strong> above to find competitors based on your business context.</span>
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

				{#if detectedCompetitorData.length > 0}
					<div>
						<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
							Auto-Detected Competitors
						</span>
						<div class="flex flex-wrap gap-2">
							{#each detectedCompetitorData as competitor, index}
								{@const score = competitor.relevance_score}
								{@const pillColor = score === null ? 'bg-slate-100 dark:bg-slate-700' : score >= 0.66 ? 'bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700' : score >= 0.33 ? 'bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700' : 'bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700'}
								<span
									class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm {pillColor}"
									title={competitor.relevance_warning || (competitor.relevance_flags ? `Similar product: ${competitor.relevance_flags.similar_product ? 'Yes' : 'No'}, Same ICP: ${competitor.relevance_flags.same_icp ? 'Yes' : 'No'}, Same market: ${competitor.relevance_flags.same_market ? 'Yes' : 'No'}` : '')}
								>
									{#if score !== null}
										<span class="text-xs font-medium {score >= 0.66 ? 'text-green-700 dark:text-green-300' : score >= 0.33 ? 'text-yellow-700 dark:text-yellow-300' : 'text-red-700 dark:text-red-300'}">
											{score >= 0.66 ? '✓' : score >= 0.33 ? '~' : '?'}
										</span>
									{/if}
									{competitor.name}
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
							<span class="inline-flex items-center gap-1"><span class="text-green-600">✓</span> High relevance</span>
							<span class="inline-flex items-center gap-1 ml-3"><span class="text-yellow-600">~</span> Partial match</span>
							<span class="inline-flex items-center gap-1 ml-3"><span class="text-red-600">?</span> Low relevance</span>
						</p>
					</div>
				{/if}

				<!-- Managed Competitors -->
				<div class="pt-4 border-t border-slate-200 dark:border-slate-700">
					<CompetitorManager
						initialCompetitors={managedCompetitors}
						onUpdate={(updated) => (managedCompetitors = updated)}
					/>
				</div>
			</div>
		</div>

		<!-- Competitor Insights Section -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-3">
					<span class="text-2xl">📊</span>
					<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
						Competitor Insights
					</h3>
					{#if insightsTotalCount > 0}
						<span class="text-sm text-slate-500 dark:text-slate-400">
							({insightsVisibleCount} of {insightsTotalCount})
						</span>
					{/if}
				</div>
			</div>

			{#if insightsError}
				<Alert variant="warning" class="mb-4">
					{insightsError}
				</Alert>
			{/if}

			{#if insightsUpgradePrompt}
				<Alert variant="info" class="mb-4">
					{insightsUpgradePrompt}
					<a href="/settings/billing" class="font-medium underline ml-1">Upgrade now</a>
				</Alert>
			{/if}

			<div class="space-y-4">
				{#if isLoadingInsights}
					<div class="flex items-center justify-center py-8">
						<div class="animate-spin h-6 w-6 border-2 border-brand-600 border-t-transparent rounded-full"></div>
					</div>
				{:else if competitorInsights.length > 0}
					<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
						{#each competitorInsights as insight}
							<CompetitorInsightCard
								{insight}
								isGenerating={generatingInsightFor === insight.name}
								onRefresh={() => handleRefreshInsight(insight.name)}
								onDelete={() => handleDeleteInsight(insight.name)}
							/>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-slate-500 dark:text-slate-400">
						No competitor insights yet. Click on a detected competitor above to generate an AI-powered analysis.
					</p>
				{/if}

				<!-- Generate insight for detected competitors without insights -->
				{#if detectedCompetitorNames.length > 0}
					{@const insightNames = new Set(competitorInsights.map((i) => i.name))}
					{@const missingInsights = detectedCompetitorNames.filter((c) => !insightNames.has(c))}
					{#if missingInsights.length > 0}
						<div class="pt-4 border-t border-slate-200 dark:border-slate-700">
							<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
								Generate insights for:
							</span>
							<div class="flex flex-wrap gap-2">
								{#each missingInsights as competitor}
									<Button
										variant="outline"
										size="sm"
										onclick={() => handleGenerateInsight(competitor)}
										disabled={generatingInsightFor !== null}
										loading={generatingInsightFor === competitor}
									>
										{generatingInsightFor === competitor ? 'Generating...' : competitor}
									</Button>
								{/each}
							</div>
						</div>
					{/if}
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

		<!-- Trend Forecast Section (AI-generated industry summary with timeframe selector) -->
		<TrendSummaryCard
			summary={trendSummary}
			isStale={trendSummaryStale}
			needsIndustry={trendSummaryNeedsIndustry}
			isLoading={isLoadingTrendSummary}
			isRefreshing={isRefreshingTrendSummary}
			error={trendSummaryError}
			{selectedTimeframe}
			{availableTimeframes}
			upgradePrompt={forecastUpgradePrompt}
			canRefresh={canRefreshNow}
			refreshBlockedReason={refreshBlockedReason}
			onRefresh={handleRefreshTrendForecast}
			onTimeframeChange={handleTimeframeChange}
		/>

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

		<!-- Trend Insights Section -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="flex items-center gap-3 mb-4">
				<span class="text-2xl">🔍</span>
				<div>
					<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
						Trend Insights
					</h3>
					<p class="text-sm text-slate-500 dark:text-slate-400">
						Paste article URLs to get AI-powered analysis of market trends
					</p>
				</div>
			</div>

			{#if trendInsightsError}
				<Alert variant="warning" class="mb-4">
					{trendInsightsError}
				</Alert>
			{/if}

			<!-- URL Input -->
			<div class="flex gap-2 mb-6">
				<input
					type="url"
					bind:value={trendUrlInput}
					placeholder="Paste a trend article URL (e.g., https://techcrunch.com/...)"
					class="flex-1 px-4 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-200"
					onkeydown={(e) => e.key === 'Enter' && handleAnalyzeTrend()}
				/>
				<Button
					onclick={handleAnalyzeTrend}
					disabled={isAnalyzingTrend || !trendUrlInput.trim()}
					loading={isAnalyzingTrend}
				>
					{isAnalyzingTrend ? 'Analyzing...' : 'Analyze'}
				</Button>
			</div>

			<!-- Trend Insights Grid -->
			{#if isLoadingTrendInsights}
				<div class="flex items-center justify-center py-8">
					<div class="animate-spin h-6 w-6 border-2 border-brand-600 border-t-transparent rounded-full"></div>
				</div>
			{:else if trendInsights.length > 0}
				<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
					{#each trendInsights as insight}
						<TrendInsightCard
							{insight}
							isGenerating={isAnalyzingTrend}
							onRefresh={() => handleRefreshTrendInsight(insight.url)}
							onDelete={() => handleDeleteTrendInsight(insight.url)}
						/>
					{/each}
				</div>
			{:else}
				<div class="text-center py-8 text-slate-500 dark:text-slate-400">
					<p class="text-sm">No trend insights yet.</p>
					<p class="text-xs mt-1">Paste a URL above to analyze a market trend article.</p>
				</div>
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
