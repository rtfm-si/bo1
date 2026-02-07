<script lang="ts">
	import { onMount } from 'svelte';
	import {
		BarChart3,
		Download,
		RefreshCw,
		DollarSign,
		Calendar,
		Users,
		TrendingUp,
		PieChart,
		Server,
		Plus,
		Zap,
		Pencil,
		Trash2,
		Check,
		X,
		Lightbulb,
		Cpu,
		Layers,
		AlertCircle,
		Target
	} from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import {
		adminApi,
		type CostSummaryResponse,
		type UserCostsResponse,
		type DailyCostsResponse,
		type CostsByProviderResponse,
		type FixedCostsResponse,
		type PerUserCostResponse,
		type UnifiedCacheMetricsResponse,
		type FixedCostItem,
		type CostAggregationsResponse,
		type InternalCostsResponse,
		type CacheEffectivenessResponse,
		type ModelImpactResponse,
		type FeatureEfficiencyResponse,
		type TuningRecommendationsResponse,
		type QualityIndicatorsResponse,
		type CostAveragesResponse
	} from '$lib/api/admin';

	// State
	let summary = $state<CostSummaryResponse | null>(null);
	let userCosts = $state<UserCostsResponse | null>(null);
	let dailyCosts = $state<DailyCostsResponse | null>(null);
	let providerCosts = $state<CostsByProviderResponse | null>(null);
	let fixedCosts = $state<FixedCostsResponse | null>(null);
	let perUserCosts = $state<PerUserCostResponse | null>(null);
	let cacheMetrics = $state<UnifiedCacheMetricsResponse | null>(null);
	let costAggregations = $state<CostAggregationsResponse | null>(null);
	let internalCosts = $state<InternalCostsResponse | null>(null);
	let costAverages = $state<CostAveragesResponse | null>(null);
	// Insights state
	let cacheEffectiveness = $state<CacheEffectivenessResponse | null>(null);
	let modelImpact = $state<ModelImpactResponse | null>(null);
	let featureEfficiency = $state<FeatureEfficiencyResponse | null>(null);
	let tuningRecommendations = $state<TuningRecommendationsResponse | null>(null);
	let qualityIndicators = $state<QualityIndicatorsResponse | null>(null);
	let insightsLoading = $state(false);
	let insightsPeriod = $state<'day' | 'week' | 'month'>('week');
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'overview' | 'providers' | 'fixed' | 'internal' | 'insights'>('overview');

	// Chart state
	let chartMaxValue = $state(0);

	// Fixed costs edit state
	let editingCostId = $state<number | null>(null);
	let editAmount = $state<number>(0);
	let editNotes = $state<string>('');
	let showAddModal = $state(false);
	let deleteConfirmId = $state<number | null>(null);
	let payingUsersCount = $state<number>(0);

	// Add form state
	let newCost = $state({
		provider: '',
		description: '',
		monthly_amount_usd: 0,
		category: 'compute',
		notes: ''
	});
	let addingCost = $state(false);
	let addError = $state<string | null>(null);

	// Provider colors
	const providerColors: Record<string, string> = {
		anthropic: 'bg-orange-500',
		voyage: 'bg-blue-500',
		brave: 'bg-red-500',
		tavily: 'bg-green-500',
		openai: 'bg-emerald-500'
	};

	async function loadData() {
		try {
			loading = true;
			const [summaryData, usersData, dailyData, providerData, fixedData, perUserData, cacheData, payingData, aggregationsData, internalData, averagesData] =
				await Promise.all([
					adminApi.getCostSummary(),
					adminApi.getUserCosts({ limit: 10 }),
					adminApi.getDailyCosts(),
					adminApi.getCostsByProvider(30),
					adminApi.getFixedCosts(),
					adminApi.getPerUserCosts({ days: 30, limit: 20 }),
					adminApi.getUnifiedCacheMetrics().catch(() => null),
					adminApi.getPayingUsersCount().catch(() => ({ paying_users_count: 0 })),
					adminApi.getCostAggregations(30).catch(() => null),
					adminApi.getInternalCosts().catch(() => null),
					adminApi.getCostAverages().catch(() => null)
				]);
			summary = summaryData;
			userCosts = usersData;
			dailyCosts = dailyData;
			providerCosts = providerData;
			fixedCosts = fixedData;
			perUserCosts = perUserData;
			cacheMetrics = cacheData;
			payingUsersCount = payingData.paying_users_count;
			costAggregations = aggregationsData;
			internalCosts = internalData;
			costAverages = averagesData;
			error = null;

			// Calculate max for chart scaling
			if (dailyData.days.length > 0) {
				chartMaxValue = Math.max(...dailyData.days.map((d) => d.total_cost));
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load cost data';
		} finally {
			loading = false;
		}
	}

	function formatPercent(value: number | null | undefined): string {
		if (value == null) return '0.0%';
		return `${(value * 100).toFixed(1)}%`;
	}

	async function loadInsights() {
		try {
			insightsLoading = true;
			const [cacheData, modelData, featureData, tuningData, qualityData] = await Promise.all([
				adminApi.getCacheEffectiveness(insightsPeriod).catch(() => null),
				adminApi.getModelImpact(insightsPeriod).catch(() => null),
				adminApi.getFeatureEfficiency(insightsPeriod).catch(() => null),
				adminApi.getTuningRecommendations().catch(() => null),
				adminApi.getQualityIndicators(insightsPeriod).catch(() => null)
			]);
			cacheEffectiveness = cacheData;
			modelImpact = modelData;
			featureEfficiency = featureData;
			tuningRecommendations = tuningData;
			qualityIndicators = qualityData;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load insights data';
		} finally {
			insightsLoading = false;
		}
	}

	// Load insights when tab changes to insights or period changes
	$effect(() => {
		if (activeTab === 'insights' && !cacheEffectiveness) {
			loadInsights();
		}
	});

	$effect(() => {
		if (activeTab === 'insights') {
			// eslint-disable-next-line @typescript-eslint/no-unused-expressions
			insightsPeriod; // Track period changes
			loadInsights();
		}
	});

	async function seedFixedCosts() {
		try {
			const result = await adminApi.seedFixedCosts();
			fixedCosts = result;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to seed fixed costs';
		}
	}

	function startEdit(cost: FixedCostItem) {
		editingCostId = cost.id;
		editAmount = cost.monthly_amount_usd;
		editNotes = cost.notes || '';
	}

	function cancelEdit() {
		editingCostId = null;
		editAmount = 0;
		editNotes = '';
	}

	async function saveEdit(costId: number) {
		try {
			const updated = await adminApi.updateFixedCost(costId, {
				monthly_amount_usd: editAmount,
				notes: editNotes || undefined
			});
			// Update local state
			if (fixedCosts) {
				const idx = fixedCosts.costs.findIndex((c) => c.id === costId);
				if (idx >= 0) {
					fixedCosts.costs[idx] = updated;
					fixedCosts.monthly_total = fixedCosts.costs
						.filter((c) => c.active)
						.reduce((sum, c) => sum + c.monthly_amount_usd, 0);
				}
			}
			cancelEdit();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update cost';
		}
	}

	async function deleteCost(costId: number) {
		try {
			await adminApi.deleteFixedCost(costId);
			// Remove from local state
			if (fixedCosts) {
				fixedCosts.costs = fixedCosts.costs.filter((c) => c.id !== costId);
				fixedCosts.monthly_total = fixedCosts.costs
					.filter((c) => c.active)
					.reduce((sum, c) => sum + c.monthly_amount_usd, 0);
			}
			deleteConfirmId = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete cost';
		}
	}

	async function addFixedCost() {
		if (!newCost.provider.trim() || !newCost.description.trim() || newCost.monthly_amount_usd <= 0) {
			addError = 'Please fill in all required fields';
			return;
		}
		try {
			addingCost = true;
			addError = null;
			const created = await adminApi.createFixedCost({
				provider: newCost.provider.trim(),
				description: newCost.description.trim(),
				monthly_amount_usd: newCost.monthly_amount_usd,
				category: newCost.category,
				notes: newCost.notes.trim() || undefined
			});
			// Add to local state
			if (fixedCosts) {
				fixedCosts.costs = [...fixedCosts.costs, created];
				fixedCosts.monthly_total += created.monthly_amount_usd;
			}
			// Reset form
			newCost = {
				provider: '',
				description: '',
				monthly_amount_usd: 0,
				category: 'compute',
				notes: ''
			};
			showAddModal = false;
		} catch (e) {
			addError = e instanceof Error ? e.message : 'Failed to create fixed cost';
		} finally {
			addingCost = false;
		}
	}

	function closeAddModal() {
		showAddModal = false;
		addError = null;
		newCost = {
			provider: '',
			description: '',
			monthly_amount_usd: 0,
			category: 'compute',
			notes: ''
		};
	}

	function formatCurrency(value: number | null | undefined): string {
		if (value == null) return '$0.00';
		return `$${value.toFixed(2)}`;
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	function downloadCsv() {
		if (!userCosts || !dailyCosts) return;

		let csv = 'Type,Date/User,Cost,Sessions\n';

		for (const day of dailyCosts.days) {
			csv += `Daily,${day.date},${day.total_cost.toFixed(4)},${day.session_count}\n`;
		}

		for (const user of userCosts.users) {
			csv += `User,${user.email || user.user_id},${user.total_cost.toFixed(4)},${user.session_count}\n`;
		}

		const blob = new Blob([csv], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `cost-report-${new Date().toISOString().split('T')[0]}.csv`;
		a.click();
		URL.revokeObjectURL(url);
	}

	function getBarHeight(value: number): number {
		if (chartMaxValue === 0) return 0;
		const height = (value / chartMaxValue) * 100;
		return value > 0 ? Math.max(height, 2) : 0;
	}

	onMount(() => {
		loadData();
	});
</script>

<svelte:head>
	<title>Cost Analytics - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/admin"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
						aria-label="Back to admin"
					>
						<svg
							class="w-5 h-5 text-neutral-600 dark:text-neutral-400"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 19l-7-7m0 0l7-7m-7 7h18"
							/>
						</svg>
					</a>
					<div class="flex items-center gap-3">
						<BarChart3 class="w-6 h-6 text-success-600 dark:text-success-400" />
						<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">Cost Analytics</h1>
					</div>
				</div>
				<div class="flex items-center gap-3">
					<Button variant="secondary" size="sm" onclick={loadData}>
						<RefreshCw class="w-4 h-4" />
						Refresh
					</Button>
					<Button
						variant="brand"
						size="sm"
						onclick={downloadCsv}
						disabled={!userCosts || !dailyCosts}
					>
						<Download class="w-4 h-4" />
						Export CSV
					</Button>
				</div>
			</div>

			<!-- Tabs -->
			<div class="flex gap-4 mt-4">
				<button
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors {activeTab ===
					'overview'
						? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
						: 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-700'}"
					onclick={() => (activeTab = 'overview')}
				>
					Overview
				</button>
				<button
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors {activeTab ===
					'providers'
						? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
						: 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-700'}"
					onclick={() => (activeTab = 'providers')}
				>
					By Provider
				</button>
				<button
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors {activeTab === 'fixed'
						? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
						: 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-700'}"
					onclick={() => (activeTab = 'fixed')}
				>
					Fixed Costs
				</button>
				<button
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors {activeTab === 'internal'
						? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
						: 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-700'}"
					onclick={() => (activeTab = 'internal')}
				>
					Internal Costs
				</button>
				<button
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors {activeTab === 'insights'
						? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
						: 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-700'}"
					onclick={() => (activeTab = 'insights')}
				>
					<span class="flex items-center gap-1.5">
						<Lightbulb class="w-4 h-4" />
						Insights
					</span>
				</button>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if error}
			<Alert variant="error" class="mb-6">{error}</Alert>
		{/if}

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
			</div>
		{:else if activeTab === 'overview' && summary}
			<!-- Summary Cards -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Today</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{formatCurrency(summary.today)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_today} sessions</p>
						</div>
						<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
							<DollarSign class="w-6 h-6 text-success-600 dark:text-success-400" />
						</div>
					</div>
				</div>
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">This Week</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{formatCurrency(summary.this_week)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_week} sessions</p>
						</div>
						<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
							<Calendar class="w-6 h-6 text-brand-600 dark:text-brand-400" />
						</div>
					</div>
				</div>
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">This Month</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{formatCurrency(summary.this_month)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_month} sessions</p>
						</div>
						<div class="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
							<TrendingUp class="w-6 h-6 text-amber-600 dark:text-amber-400" />
						</div>
					</div>
				</div>
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">All Time</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{formatCurrency(summary.all_time)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_total} sessions</p>
						</div>
						<div class="p-3 bg-neutral-100 dark:bg-neutral-700 rounded-lg">
							<BarChart3 class="w-6 h-6 text-neutral-600 dark:text-neutral-400" />
						</div>
					</div>
				</div>
			</div>

			<!-- Multi-Period Averages -->
			{#if costAverages}
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
					<!-- Avg Cost Per Meeting -->
					<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
						<div class="flex items-center gap-3 mb-4">
							<BarChart3 class="w-5 h-5 text-brand-600" />
							<h3 class="text-lg font-medium text-neutral-900 dark:text-white">Avg Cost Per Meeting</h3>
						</div>
						<div class="grid grid-cols-3 gap-3">
							{#each costAverages.periods as period}
								<div class="text-center p-3 bg-brand-50 dark:bg-brand-900/20 rounded-lg">
									<p class="text-xs text-neutral-500 mb-1">{period.label}</p>
									<p class="text-lg font-semibold text-brand-600 dark:text-brand-400">
										{formatCurrency(period.avg_per_meeting)}
									</p>
									<p class="text-xs text-neutral-500 mt-1">
										{period.unique_sessions} mtg{period.unique_sessions !== 1 ? 's' : ''}
									</p>
								</div>
							{/each}
						</div>
					</div>

					<!-- Total Spend Per Period -->
					<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
						<div class="flex items-center gap-3 mb-4">
							<DollarSign class="w-5 h-5 text-green-600" />
							<h3 class="text-lg font-medium text-neutral-900 dark:text-white">Total Spend</h3>
						</div>
						<div class="grid grid-cols-3 gap-3">
							{#each costAverages.periods as period}
								<div class="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
									<p class="text-xs text-neutral-500 mb-1">{period.label}</p>
									<p class="text-lg font-semibold text-green-600 dark:text-green-400">
										{formatCurrency(period.total_cost)}
									</p>
									<p class="text-xs text-neutral-500 mt-1">
										{period.unique_sessions} session{period.unique_sessions !== 1 ? 's' : ''}
									</p>
								</div>
							{/each}
						</div>
					</div>
				</div>
			{/if}

			<!-- Cache Performance Card -->
			{#if cacheMetrics}
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 mb-8"
				>
					<div class="flex items-center gap-3 mb-4">
						<Zap class="w-5 h-5 text-amber-500" />
						<h3 class="text-lg font-medium text-neutral-900 dark:text-white">
							Cache Performance (7d)
						</h3>
					</div>

					<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
						<!-- Prompt Cache -->
						<div class="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
							<p class="text-xs text-neutral-500 mb-1">Prompt Cache</p>
							<p class="text-xl font-semibold text-orange-600 dark:text-orange-400">
								{formatPercent(cacheMetrics.prompt.hit_rate)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">
								{cacheMetrics.prompt.hits.toLocaleString()} / {cacheMetrics.prompt.total.toLocaleString()}
							</p>
						</div>

						<!-- Research Cache -->
						<div class="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
							<p class="text-xs text-neutral-500 mb-1">Research Cache</p>
							<p class="text-xl font-semibold text-blue-600 dark:text-blue-400">
								{formatPercent(cacheMetrics.research.hit_rate)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">
								{cacheMetrics.research.hits.toLocaleString()} / {cacheMetrics.research.total.toLocaleString()}
							</p>
						</div>

						<!-- LLM Cache -->
						<div class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
							<p class="text-xs text-neutral-500 mb-1">LLM Cache</p>
							<p class="text-xl font-semibold text-green-600 dark:text-green-400">
								{formatPercent(cacheMetrics.llm.hit_rate)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">
								{cacheMetrics.llm.hits.toLocaleString()} / {cacheMetrics.llm.total.toLocaleString()}
							</p>
						</div>

						<!-- Aggregate -->
						<div class="p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg">
							<p class="text-xs text-neutral-500 mb-1">Aggregate</p>
							<p class="text-xl font-semibold text-brand-600 dark:text-brand-400">
								{formatPercent(cacheMetrics.aggregate.hit_rate)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">
								{cacheMetrics.aggregate.total_hits.toLocaleString()} / {cacheMetrics.aggregate.total_requests.toLocaleString()}
							</p>
						</div>
					</div>
				</div>
			{/if}

			<!-- Daily Costs Chart -->
			{#if dailyCosts && dailyCosts.days.length > 0}
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 mb-8"
				>
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
						Daily Costs (Last 30 Days)
					</h2>
					<div class="h-48 flex items-end gap-1">
						{#each dailyCosts.days as day, i (day.date)}
							<div class="flex-1 flex flex-col items-center gap-1 min-w-0">
								<div
									class="w-full bg-brand-500 dark:bg-brand-400 rounded-t transition-all hover:bg-brand-600 dark:hover:bg-brand-300"
									style="height: {getBarHeight(day.total_cost)}%"
									title="{formatDate(day.date)}: {formatCurrency(day.total_cost)} ({day.session_count} sessions)"
								></div>
								{#if i % 5 === 0 || i === dailyCosts.days.length - 1}
									<span
										class="text-xs text-neutral-500 transform -rotate-45 origin-top-left whitespace-nowrap"
									>
										{formatDate(day.date)}
									</span>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Top Users Table -->
			{#if userCosts && userCosts.users.length > 0}
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden"
				>
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Top Users by Cost
						</h2>
					</div>
					<table class="w-full">
						<thead class="bg-neutral-50 dark:bg-neutral-700">
							<tr>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
									>Rank</th
								>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
									>User</th
								>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
									>Sessions</th
								>
								<th
									class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
									>Total Cost</th
								>
								<th
									class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
									>Avg/Session</th
								>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each userCosts.users as user, i (user.user_id)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors">
									<td class="px-6 py-4">
										<span
											class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium {i ===
											0
												? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400'
												: i === 1
													? 'bg-neutral-200 text-neutral-800 dark:bg-neutral-600 dark:text-neutral-300'
													: i === 2
														? 'bg-amber-700/20 text-amber-700 dark:bg-amber-800/30 dark:text-amber-500'
														: 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400'}"
										>
											{i + 1}
										</span>
									</td>
									<td class="px-6 py-4">
										<div class="flex items-center gap-2">
											<Users class="w-4 h-4 text-neutral-400" />
											<span
												class="text-sm text-neutral-900 dark:text-white truncate max-w-[200px]"
												title={user.email || user.user_id}
											>
												{user.email || user.user_id}
											</span>
										</div>
									</td>
									<td class="px-6 py-4 text-sm text-neutral-700 dark:text-neutral-300">
										{user.session_count}
									</td>
									<td class="px-6 py-4 text-right">
										<span class="text-sm font-medium text-neutral-900 dark:text-white">
											{formatCurrency(user.total_cost)}
										</span>
									</td>
									<td class="px-6 py-4 text-right">
										<span class="text-sm text-neutral-600 dark:text-neutral-400">
											{formatCurrency(
												user.session_count > 0 ? user.total_cost / user.session_count : 0
											)}
										</span>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		{:else if activeTab === 'providers' && providerCosts}
			<!-- Provider Breakdown -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<!-- Provider Pie Chart (visual representation) -->
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6"
				>
					<div class="flex items-center gap-2 mb-4">
						<PieChart class="w-5 h-5 text-brand-600" />
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Cost Distribution by Provider
						</h2>
					</div>

					<div class="space-y-4">
						{#each providerCosts.providers as provider (provider.provider)}
							{@const agg = costAggregations?.categories.find(c => c.category === provider.provider)}
							<div>
								<div class="flex justify-between text-sm mb-1">
									<span class="text-neutral-700 dark:text-neutral-300 capitalize"
										>{provider.provider}</span
									>
									<span class="text-neutral-900 dark:text-white font-medium">
										{formatCurrency(provider.amount_usd)} ({provider.percentage}%)
									</span>
								</div>
								<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
									<div
										class="{providerColors[provider.provider] ||
											'bg-neutral-500'} h-full rounded-full transition-all"
										style="width: {provider.percentage}%"
									></div>
								</div>
								<div class="flex items-center justify-between mt-1">
									<p class="text-xs text-neutral-500">
										{provider.request_count.toLocaleString()} requests
									</p>
									{#if agg}
										<p class="text-xs text-neutral-500">
											<span title="Avg per meeting">📅 {agg.avg_per_meeting !== null ? formatCurrency(agg.avg_per_meeting) : 'N/A'}</span>
											<span class="mx-1">·</span>
											<span title="Avg per user">👤 {agg.avg_per_user !== null ? formatCurrency(agg.avg_per_user) : 'N/A'}</span>
										</p>
									{/if}
								</div>
							</div>
						{/each}
					</div>

					<div class="mt-6 pt-4 border-t border-neutral-200 dark:border-neutral-700 space-y-2">
						<div class="flex justify-between">
							<span class="text-neutral-600 dark:text-neutral-400">Total (30d)</span>
							<span class="text-lg font-semibold text-neutral-900 dark:text-white">
								{formatCurrency(providerCosts.total_usd)}
							</span>
						</div>
						{#if costAggregations?.overall}
							<div class="flex justify-between text-sm">
								<span class="text-neutral-500">Avg per meeting</span>
								<span class="text-neutral-700 dark:text-neutral-300">
									{costAggregations.overall.avg_per_meeting !== null ? formatCurrency(costAggregations.overall.avg_per_meeting) : 'N/A'}
									<span class="text-xs text-neutral-400">({costAggregations.overall.meeting_count} meetings)</span>
								</span>
							</div>
							<div class="flex justify-between text-sm">
								<span class="text-neutral-500">Avg per paying user</span>
								<span class="text-neutral-700 dark:text-neutral-300">
									{costAggregations.overall.avg_per_user !== null ? formatCurrency(costAggregations.overall.avg_per_user) : 'N/A'}
									<span class="text-xs text-neutral-400">({costAggregations.overall.user_count} users)</span>
								</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Provider Table -->
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden"
				>
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Provider Details</h2>
					</div>
					<div class="overflow-x-auto">
						<table class="w-full">
							<thead class="bg-neutral-50 dark:bg-neutral-700">
								<tr>
									<th
										class="px-4 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
										>Provider</th
									>
									<th
										class="px-4 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
										>Requests</th
									>
									<th
										class="px-4 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
										>Cost</th
									>
									<th
										class="px-4 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
										>Avg/Req</th
									>
									<th
										class="px-4 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
										>Avg/Meet</th
									>
									<th
										class="px-4 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
										>Avg/User</th
									>
								</tr>
							</thead>
							<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
								{#each providerCosts.providers as provider (provider.provider)}
									{@const agg = costAggregations?.categories.find(c => c.category === provider.provider)}
									<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
										<td class="px-4 py-4">
											<div class="flex items-center gap-2">
												<div
													class="w-3 h-3 rounded-full {providerColors[provider.provider] ||
														'bg-neutral-500'}"
												></div>
												<span class="text-sm font-medium text-neutral-900 dark:text-white capitalize">
													{provider.provider}
												</span>
											</div>
										</td>
										<td class="px-4 py-4 text-right text-sm text-neutral-700 dark:text-neutral-300">
											{provider.request_count.toLocaleString()}
										</td>
										<td class="px-4 py-4 text-right text-sm font-medium text-neutral-900 dark:text-white">
											{formatCurrency(provider.amount_usd)}
										</td>
										<td class="px-4 py-4 text-right text-sm text-neutral-600 dark:text-neutral-400">
											{formatCurrency(
												provider.request_count > 0
													? provider.amount_usd / provider.request_count
													: 0
											)}
										</td>
										<td class="px-4 py-4 text-right text-sm text-neutral-600 dark:text-neutral-400">
											{agg?.avg_per_meeting !== null && agg?.avg_per_meeting !== undefined ? formatCurrency(agg.avg_per_meeting) : '—'}
										</td>
										<td class="px-4 py-4 text-right text-sm text-neutral-600 dark:text-neutral-400">
											{agg?.avg_per_user !== null && agg?.avg_per_user !== undefined ? formatCurrency(agg.avg_per_user) : '—'}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			</div>
		{:else if activeTab === 'fixed' && fixedCosts}
			<!-- Fixed Costs -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700"
			>
				<div
					class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between"
				>
					<div class="flex items-center gap-2">
						<Server class="w-5 h-5 text-brand-600" />
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Fixed Infrastructure Costs
						</h2>
					</div>
					<div class="flex items-center gap-2">
						{#if fixedCosts.costs.length === 0}
							<Button variant="secondary" size="sm" onclick={seedFixedCosts}>
								<Plus class="w-4 h-4" />
								Seed Defaults
							</Button>
						{/if}
						<Button variant="brand" size="sm" onclick={() => (showAddModal = true)}>
							<Plus class="w-4 h-4" />
							Add Fixed Cost
						</Button>
					</div>
				</div>

				{#if fixedCosts.costs.length === 0}
					<div class="p-8 text-center">
						<Server class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
						<p class="text-neutral-600 dark:text-neutral-400">No fixed costs configured</p>
						<p class="text-sm text-neutral-500 mt-1">Click "Add Fixed Cost" or "Seed Defaults" to get started</p>
					</div>
				{:else}
					<table class="w-full">
						<thead class="bg-neutral-50 dark:bg-neutral-700">
							<tr>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Provider</th
								>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Description</th
								>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Category</th
								>
								<th
									class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Monthly Cost</th
								>
								<th
									class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Actions</th
								>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each fixedCosts.costs as cost (cost.id)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
									<td class="px-6 py-4">
										<span class="text-sm font-medium text-neutral-900 dark:text-white capitalize">
											{cost.provider}
										</span>
									</td>
									<td class="px-6 py-4 text-sm text-neutral-700 dark:text-neutral-300">
										{cost.description}
										{#if cost.notes}
											<p class="text-xs text-neutral-500 mt-1">{cost.notes}</p>
										{/if}
									</td>
									<td class="px-6 py-4">
										<span
											class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300 capitalize"
										>
											{cost.category}
										</span>
									</td>
									<td class="px-6 py-4 text-right">
										{#if editingCostId === cost.id}
											<div class="flex items-center justify-end gap-2">
												<span class="text-sm text-neutral-500">$</span>
												<input
													type="number"
													step="0.01"
													min="0"
													bind:value={editAmount}
													class="w-24 px-2 py-1 text-sm text-right border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
												/>
											</div>
										{:else}
											<span class="text-sm font-medium text-neutral-900 dark:text-white">
												{formatCurrency(cost.monthly_amount_usd)}
											</span>
										{/if}
									</td>
									<td class="px-6 py-4 text-right">
										{#if editingCostId === cost.id}
											<div class="flex items-center justify-end gap-1">
												<button
													onclick={() => saveEdit(cost.id)}
													class="p-1.5 text-success-600 hover:bg-success-100 dark:hover:bg-success-900/30 rounded transition-colors"
													title="Save"
												>
													<Check class="w-4 h-4" />
												</button>
												<button
													onclick={cancelEdit}
													class="p-1.5 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded transition-colors"
													title="Cancel"
												>
													<X class="w-4 h-4" />
												</button>
											</div>
										{:else if deleteConfirmId === cost.id}
											<div class="flex items-center justify-end gap-1">
												<span class="text-xs text-danger-600 mr-1">Delete?</span>
												<button
													onclick={() => deleteCost(cost.id)}
													class="p-1.5 text-danger-600 hover:bg-danger-100 dark:hover:bg-danger-900/30 rounded transition-colors"
													title="Confirm Delete"
												>
													<Check class="w-4 h-4" />
												</button>
												<button
													onclick={() => (deleteConfirmId = null)}
													class="p-1.5 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded transition-colors"
													title="Cancel"
												>
													<X class="w-4 h-4" />
												</button>
											</div>
										{:else}
											<div class="flex items-center justify-end gap-1">
												<button
													onclick={() => startEdit(cost)}
													class="p-1.5 text-neutral-500 hover:text-brand-600 hover:bg-brand-100 dark:hover:bg-brand-900/30 rounded transition-colors"
													title="Edit"
												>
													<Pencil class="w-4 h-4" />
												</button>
												<button
													onclick={() => (deleteConfirmId = cost.id)}
													class="p-1.5 text-neutral-500 hover:text-danger-600 hover:bg-danger-100 dark:hover:bg-danger-900/30 rounded transition-colors"
													title="Delete"
												>
													<Trash2 class="w-4 h-4" />
												</button>
											</div>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
						<tfoot class="bg-neutral-50 dark:bg-neutral-700">
							<tr>
								<td colspan="3" class="px-6 py-4 text-sm font-medium text-neutral-900 dark:text-white">
									Total Monthly Fixed Costs
								</td>
								<td class="px-6 py-4 text-right text-lg font-semibold text-neutral-900 dark:text-white">
									{formatCurrency(fixedCosts.monthly_total)}
								</td>
								<td></td>
							</tr>
						</tfoot>
					</table>
				{/if}

				<!-- Fixed vs Variable Comparison -->
				{#if summary && fixedCosts.costs.length > 0}
					<div class="p-6 border-t border-neutral-200 dark:border-neutral-700">
						<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-4">
							Fixed vs Variable (This Month)
						</h3>
						<div class="grid grid-cols-2 lg:grid-cols-3 gap-4">
							<div class="p-4 bg-neutral-50 dark:bg-neutral-700 rounded-lg">
								<p class="text-xs text-neutral-500 mb-1">Fixed Costs</p>
								<p class="text-xl font-semibold text-neutral-900 dark:text-white">
									{formatCurrency(fixedCosts.monthly_total)}
								</p>
							</div>
							<div class="p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg">
								<p class="text-xs text-neutral-500 mb-1">Variable Costs (API)</p>
								<p class="text-xl font-semibold text-brand-700 dark:text-brand-400">
									{formatCurrency(summary.this_month)}
								</p>
							</div>
							<div class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
								<p class="text-xs text-neutral-500 mb-1">Fixed per Paying User</p>
								{#if payingUsersCount > 0}
									<p class="text-xl font-semibold text-amber-700 dark:text-amber-400">
										{formatCurrency(fixedCosts.monthly_total / payingUsersCount)}
									</p>
									<p class="text-xs text-neutral-500 mt-1">{payingUsersCount} paying user{payingUsersCount !== 1 ? 's' : ''}</p>
								{:else}
									<p class="text-xl font-semibold text-neutral-400">N/A</p>
									<p class="text-xs text-neutral-500 mt-1">No paying users</p>
								{/if}
							</div>
						</div>
						<div class="mt-4 p-4 bg-neutral-100 dark:bg-neutral-600 rounded-lg">
							<div class="flex justify-between items-center">
								<span class="text-sm text-neutral-600 dark:text-neutral-300"
									>Estimated Total Monthly</span
								>
								<span class="text-xl font-bold text-neutral-900 dark:text-white">
									{formatCurrency(fixedCosts.monthly_total + summary.this_month)}
								</span>
							</div>
						</div>
					</div>
				{/if}
			</div>
		{:else if activeTab === 'internal' && internalCosts}
			<!-- Internal Costs -->
			<div class="space-y-6">
				<!-- Period Summary Cards -->
				<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
					<div class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<p class="text-sm text-neutral-500 mb-1">Today</p>
						<p class="text-xl font-semibold text-neutral-900 dark:text-white">
							{formatCurrency(internalCosts.by_period.today)}
						</p>
					</div>
					<div class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<p class="text-sm text-neutral-500 mb-1">This Week</p>
						<p class="text-xl font-semibold text-neutral-900 dark:text-white">
							{formatCurrency(internalCosts.by_period.week)}
						</p>
					</div>
					<div class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<p class="text-sm text-neutral-500 mb-1">This Month</p>
						<p class="text-xl font-semibold text-neutral-900 dark:text-white">
							{formatCurrency(internalCosts.by_period.month)}
						</p>
					</div>
					<div class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<p class="text-sm text-neutral-500 mb-1">All Time</p>
						<p class="text-xl font-semibold text-neutral-900 dark:text-white">
							{formatCurrency(internalCosts.by_period.all_time)}
						</p>
						<p class="text-xs text-neutral-400 mt-1">{internalCosts.total_requests.toLocaleString()} requests</p>
					</div>
				</div>

				<!-- SEO Costs -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">SEO Content Generation</h2>
						<p class="text-sm text-neutral-500 mt-1">Costs for automated blog post generation</p>
					</div>
					{#if internalCosts.seo.length === 0}
						<div class="p-8 text-center">
							<p class="text-neutral-500">No SEO costs recorded yet</p>
						</div>
					{:else}
						<table class="w-full">
							<thead class="bg-neutral-50 dark:bg-neutral-700">
								<tr>
									<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Provider</th>
									<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Prompt Type</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Requests</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Tokens</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Cost</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
								{#each internalCosts.seo as item}
									<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
										<td class="px-6 py-4 text-sm font-medium text-neutral-900 dark:text-white capitalize">{item.provider}</td>
										<td class="px-6 py-4 text-sm text-neutral-700 dark:text-neutral-300">{item.prompt_type || 'N/A'}</td>
										<td class="px-6 py-4 text-sm text-right text-neutral-700 dark:text-neutral-300">{item.request_count.toLocaleString()}</td>
										<td class="px-6 py-4 text-sm text-right text-neutral-700 dark:text-neutral-300">
											{(item.input_tokens + item.output_tokens).toLocaleString()}
										</td>
										<td class="px-6 py-4 text-sm text-right font-medium text-neutral-900 dark:text-white">{formatCurrency(item.total_cost)}</td>
									</tr>
								{/each}
							</tbody>
							<tfoot class="bg-neutral-50 dark:bg-neutral-700">
								<tr>
									<td colspan="4" class="px-6 py-3 text-sm font-medium text-neutral-900 dark:text-white">Total SEO Costs</td>
									<td class="px-6 py-3 text-right text-sm font-semibold text-neutral-900 dark:text-white">
										{formatCurrency(internalCosts.seo.reduce((sum, item) => sum + item.total_cost, 0))}
									</td>
								</tr>
							</tfoot>
						</table>
					{/if}
				</div>

				<!-- System Costs -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">System / Background Jobs</h2>
						<p class="text-sm text-neutral-500 mt-1">Costs for background processing and system tasks</p>
					</div>
					{#if internalCosts.system.length === 0}
						<div class="p-8 text-center">
							<p class="text-neutral-500">No system costs recorded yet</p>
						</div>
					{:else}
						<table class="w-full">
							<thead class="bg-neutral-50 dark:bg-neutral-700">
								<tr>
									<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Provider</th>
									<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Prompt Type</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Requests</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Tokens</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Cost</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
								{#each internalCosts.system as item}
									<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
										<td class="px-6 py-4 text-sm font-medium text-neutral-900 dark:text-white capitalize">{item.provider}</td>
										<td class="px-6 py-4 text-sm text-neutral-700 dark:text-neutral-300">{item.prompt_type || 'N/A'}</td>
										<td class="px-6 py-4 text-sm text-right text-neutral-700 dark:text-neutral-300">{item.request_count.toLocaleString()}</td>
										<td class="px-6 py-4 text-sm text-right text-neutral-700 dark:text-neutral-300">
											{(item.input_tokens + item.output_tokens).toLocaleString()}
										</td>
										<td class="px-6 py-4 text-sm text-right font-medium text-neutral-900 dark:text-white">{formatCurrency(item.total_cost)}</td>
									</tr>
								{/each}
							</tbody>
							<tfoot class="bg-neutral-50 dark:bg-neutral-700">
								<tr>
									<td colspan="4" class="px-6 py-3 text-sm font-medium text-neutral-900 dark:text-white">Total System Costs</td>
									<td class="px-6 py-3 text-right text-sm font-semibold text-neutral-900 dark:text-white">
										{formatCurrency(internalCosts.system.reduce((sum, item) => sum + item.total_cost, 0))}
									</td>
								</tr>
							</tfoot>
						</table>
					{/if}
				</div>

				<!-- Data Analysis Costs -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Data Analysis (Dataset Q&A)</h2>
						<p class="text-sm text-neutral-500 mt-1">Costs for user dataset analysis and insights</p>
					</div>
					{#if internalCosts.data_analysis.length === 0}
						<div class="p-8 text-center">
							<p class="text-neutral-500">No data analysis costs recorded yet</p>
						</div>
					{:else}
						<table class="w-full">
							<thead class="bg-neutral-50 dark:bg-neutral-700">
								<tr>
									<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Provider</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Requests</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Users</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Tokens</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Cost</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
								{#each internalCosts.data_analysis as item}
									<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
										<td class="px-6 py-4 text-sm font-medium text-neutral-900 dark:text-white capitalize">{item.provider}</td>
										<td class="px-6 py-4 text-sm text-right text-neutral-700 dark:text-neutral-300">{item.request_count.toLocaleString()}</td>
										<td class="px-6 py-4 text-sm text-right text-neutral-700 dark:text-neutral-300">{item.user_count.toLocaleString()}</td>
										<td class="px-6 py-4 text-sm text-right text-neutral-700 dark:text-neutral-300">
											{(item.input_tokens + item.output_tokens).toLocaleString()}
										</td>
										<td class="px-6 py-4 text-sm text-right font-medium text-neutral-900 dark:text-white">{formatCurrency(item.total_cost)}</td>
									</tr>
								{/each}
							</tbody>
							<tfoot class="bg-neutral-50 dark:bg-neutral-700">
								<tr>
									<td colspan="4" class="px-6 py-3 text-sm font-medium text-neutral-900 dark:text-white">Total Data Analysis Costs</td>
									<td class="px-6 py-3 text-right text-sm font-semibold text-neutral-900 dark:text-white">
										{formatCurrency(internalCosts.data_analysis.reduce((sum, item) => sum + item.total_cost, 0))}
									</td>
								</tr>
							</tfoot>
						</table>
					{/if}
				</div>

				<!-- Mentor Chat Costs -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Mentor Chat</h2>
						<p class="text-sm text-neutral-500 mt-1">Costs for AI mentor conversations</p>
					</div>
					{#if internalCosts.mentor_chat.length === 0}
						<div class="p-8 text-center">
							<p class="text-neutral-500">No mentor chat costs recorded yet</p>
						</div>
					{:else}
						<table class="w-full">
							<thead class="bg-neutral-50 dark:bg-neutral-700">
								<tr>
									<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Provider</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Requests</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Users</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Tokens</th>
									<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Cost</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
								{#each internalCosts.mentor_chat as item}
									<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
										<td class="px-6 py-4 text-sm font-medium text-neutral-900 dark:text-white capitalize">{item.provider}</td>
										<td class="px-6 py-4 text-sm text-right text-neutral-700 dark:text-neutral-300">{item.request_count.toLocaleString()}</td>
										<td class="px-6 py-4 text-sm text-right text-neutral-700 dark:text-neutral-300">{item.user_count.toLocaleString()}</td>
										<td class="px-6 py-4 text-sm text-right text-neutral-700 dark:text-neutral-300">
											{(item.input_tokens + item.output_tokens).toLocaleString()}
										</td>
										<td class="px-6 py-4 text-sm text-right font-medium text-neutral-900 dark:text-white">{formatCurrency(item.total_cost)}</td>
									</tr>
								{/each}
							</tbody>
							<tfoot class="bg-neutral-50 dark:bg-neutral-700">
								<tr>
									<td colspan="4" class="px-6 py-3 text-sm font-medium text-neutral-900 dark:text-white">Total Mentor Chat Costs</td>
									<td class="px-6 py-3 text-right text-sm font-semibold text-neutral-900 dark:text-white">
										{formatCurrency(internalCosts.mentor_chat.reduce((sum, item) => sum + item.total_cost, 0))}
									</td>
								</tr>
							</tfoot>
						</table>
					{/if}
				</div>
			</div>
		{:else if activeTab === 'insights'}
			<!-- Insights Tab -->
			<div class="space-y-6">
				<!-- Period Selector -->
				<div class="flex items-center justify-between">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
						<Lightbulb class="w-5 h-5 text-amber-500" />
						Cost Optimization Insights
					</h2>
					<div class="flex items-center gap-2">
						<select
							bind:value={insightsPeriod}
							class="px-3 py-1.5 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
						>
							<option value="day">Last 24 Hours</option>
							<option value="week">Last 7 Days</option>
							<option value="month">Last 30 Days</option>
						</select>
						<Button variant="secondary" size="sm" onclick={loadInsights} disabled={insightsLoading}>
							<RefreshCw class="w-4 h-4 {insightsLoading ? 'animate-spin' : ''}" />
						</Button>
					</div>
				</div>

				{#if insightsLoading}
					<div class="flex items-center justify-center py-12">
						<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
					</div>
				{:else}
					<!-- Tuning Recommendations -->
					{#if tuningRecommendations && tuningRecommendations.recommendations.length > 0}
						<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
							<div class="flex items-center gap-2 mb-4">
								<Target class="w-5 h-5 text-brand-600" />
								<h3 class="text-lg font-medium text-neutral-900 dark:text-white">Recommendations</h3>
								<span class="text-xs px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400">
									{tuningRecommendations.data_quality} data
								</span>
							</div>
							<div class="space-y-4">
								{#each tuningRecommendations.recommendations as rec}
									<div class="p-4 rounded-lg {rec.area === 'cache' ? 'bg-orange-50 dark:bg-orange-900/20' : rec.area === 'model' ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-green-50 dark:bg-green-900/20'}">
										<div class="flex items-start justify-between mb-2">
											<div class="flex items-center gap-2">
												{#if rec.area === 'cache'}
													<Zap class="w-4 h-4 text-orange-600 dark:text-orange-400" />
												{:else if rec.area === 'model'}
													<Cpu class="w-4 h-4 text-blue-600 dark:text-blue-400" />
												{:else}
													<Layers class="w-4 h-4 text-green-600 dark:text-green-400" />
												{/if}
												<span class="text-sm font-medium text-neutral-900 dark:text-white capitalize">{rec.area}</span>
												<span class="text-xs px-1.5 py-0.5 rounded {rec.confidence === 'high' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : rec.confidence === 'medium' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' : 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400'}">
													{rec.confidence}
												</span>
											</div>
											{#if rec.estimated_savings_usd}
												<span class="text-sm font-semibold text-success-600 dark:text-success-400">
													Est. ${rec.estimated_savings_usd.toFixed(2)}/mo
												</span>
											{/if}
										</div>
										<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-2">{rec.impact_description}</p>
										<div class="flex items-center gap-4 text-xs">
											<span class="text-neutral-500">Current: <span class="text-neutral-700 dark:text-neutral-300">{rec.current_value}</span></span>
											<span class="text-neutral-500">Target: <span class="text-brand-600 dark:text-brand-400 font-medium">{rec.recommended_value}</span></span>
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Cache Effectiveness -->
					{#if cacheEffectiveness}
						<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
							<div class="flex items-center justify-between mb-4">
								<div class="flex items-center gap-2">
									<Zap class="w-5 h-5 text-orange-500" />
									<h3 class="text-lg font-medium text-neutral-900 dark:text-white">Cache Effectiveness</h3>
								</div>
								<div class="text-right">
									<p class="text-2xl font-semibold text-orange-600 dark:text-orange-400">
										{formatPercent(cacheEffectiveness.overall_hit_rate)}
									</p>
									<p class="text-xs text-neutral-500">Overall Hit Rate</p>
								</div>
							</div>
							{#if cacheEffectiveness.min_sample_warning}
								<Alert variant="warning" class="mb-4">{cacheEffectiveness.min_sample_warning}</Alert>
							{/if}
							<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
								{#each cacheEffectiveness.buckets as bucket}
									<div class="p-3 rounded-lg bg-neutral-50 dark:bg-neutral-700">
										<p class="text-xs text-neutral-500 mb-1">{bucket.bucket_label} Hit Rate</p>
										<p class="text-lg font-semibold text-neutral-900 dark:text-white">{bucket.session_count}</p>
										<p class="text-xs text-neutral-500">sessions</p>
										<p class="text-xs text-success-600 dark:text-success-400 mt-1">
											Saved: {formatCurrency(bucket.total_saved)}
										</p>
									</div>
								{/each}
							</div>
							<div class="flex items-center justify-between pt-4 border-t border-neutral-200 dark:border-neutral-700">
								<div class="text-sm">
									<span class="text-neutral-500">Total Sessions:</span>
									<span class="text-neutral-900 dark:text-white font-medium ml-1">{cacheEffectiveness.total_sessions}</span>
								</div>
								<div class="text-sm">
									<span class="text-neutral-500">Total Saved:</span>
									<span class="text-success-600 dark:text-success-400 font-semibold ml-1">{formatCurrency(cacheEffectiveness.total_saved)}</span>
								</div>
							</div>
						</div>
					{/if}

					<!-- Model Impact -->
					{#if modelImpact}
						<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
							<div class="flex items-center justify-between mb-4">
								<div class="flex items-center gap-2">
									<Cpu class="w-5 h-5 text-blue-500" />
									<h3 class="text-lg font-medium text-neutral-900 dark:text-white">Model Impact Analysis</h3>
								</div>
								<div class="text-right">
									<p class="text-sm text-neutral-500">Savings from model mix</p>
									<p class="text-xl font-semibold text-success-600 dark:text-success-400">
										{formatCurrency(modelImpact.savings_from_model_mix)}
									</p>
								</div>
							</div>
							<div class="overflow-x-auto">
								<table class="w-full">
									<thead class="bg-neutral-50 dark:bg-neutral-700">
										<tr>
											<th class="px-4 py-2 text-left text-xs font-medium text-neutral-500 uppercase">Model</th>
											<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Requests</th>
											<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Cost</th>
											<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Avg/Req</th>
											<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Cache Hit</th>
										</tr>
									</thead>
									<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
										{#each modelImpact.models as model}
											<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
												<td class="px-4 py-3 text-sm font-medium text-neutral-900 dark:text-white">{model.model_display}</td>
												<td class="px-4 py-3 text-sm text-right text-neutral-700 dark:text-neutral-300">{model.request_count.toLocaleString()}</td>
												<td class="px-4 py-3 text-sm text-right font-medium text-neutral-900 dark:text-white">{formatCurrency(model.total_cost)}</td>
												<td class="px-4 py-3 text-sm text-right text-neutral-600 dark:text-neutral-400">{formatCurrency(model.avg_cost_per_request)}</td>
												<td class="px-4 py-3 text-sm text-right text-neutral-600 dark:text-neutral-400">{formatPercent(model.cache_hit_rate)}</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
							<div class="flex items-center justify-between pt-4 mt-4 border-t border-neutral-200 dark:border-neutral-700 text-sm">
								<div>
									<span class="text-neutral-500">If all Opus:</span>
									<span class="text-danger-600 dark:text-danger-400 font-medium ml-1">{formatCurrency(modelImpact.cost_if_all_opus)}</span>
								</div>
								<div>
									<span class="text-neutral-500">If all Haiku:</span>
									<span class="text-success-600 dark:text-success-400 font-medium ml-1">{formatCurrency(modelImpact.cost_if_all_haiku)}</span>
								</div>
								<div>
									<span class="text-neutral-500">Actual:</span>
									<span class="text-neutral-900 dark:text-white font-semibold ml-1">{formatCurrency(modelImpact.total_cost)}</span>
								</div>
							</div>
						</div>
					{/if}

					<!-- Feature Efficiency -->
					{#if featureEfficiency && featureEfficiency.features.length > 0}
						<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
							<div class="flex items-center gap-2 mb-4">
								<Layers class="w-5 h-5 text-green-500" />
								<h3 class="text-lg font-medium text-neutral-900 dark:text-white">Feature Efficiency</h3>
							</div>
							<div class="overflow-x-auto">
								<table class="w-full">
									<thead class="bg-neutral-50 dark:bg-neutral-700">
										<tr>
											<th class="px-4 py-2 text-left text-xs font-medium text-neutral-500 uppercase">Feature</th>
											<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Requests</th>
											<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Cost</th>
											<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Avg/Req</th>
											<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Cache Hit</th>
											<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Sessions</th>
											<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 uppercase">Cost/Session</th>
										</tr>
									</thead>
									<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
										{#each featureEfficiency.features as feature}
											<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
												<td class="px-4 py-3 text-sm font-medium text-neutral-900 dark:text-white">{feature.feature}</td>
												<td class="px-4 py-3 text-sm text-right text-neutral-700 dark:text-neutral-300">{feature.request_count.toLocaleString()}</td>
												<td class="px-4 py-3 text-sm text-right font-medium text-neutral-900 dark:text-white">{formatCurrency(feature.total_cost)}</td>
												<td class="px-4 py-3 text-sm text-right text-neutral-600 dark:text-neutral-400">{formatCurrency(feature.avg_cost)}</td>
												<td class="px-4 py-3 text-sm text-right text-neutral-600 dark:text-neutral-400">{formatPercent(feature.cache_hit_rate)}</td>
												<td class="px-4 py-3 text-sm text-right text-neutral-700 dark:text-neutral-300">{feature.unique_sessions.toLocaleString()}</td>
												<td class="px-4 py-3 text-sm text-right text-neutral-600 dark:text-neutral-400">{formatCurrency(feature.cost_per_session)}</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						</div>
					{/if}

					<!-- Quality Indicators -->
					{#if qualityIndicators}
						<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
							<div class="flex items-center gap-2 mb-4">
								<AlertCircle class="w-5 h-5 text-purple-500" />
								<h3 class="text-lg font-medium text-neutral-900 dark:text-white">Quality Indicators</h3>
							</div>
							<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
								<div class="p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20">
									<p class="text-xs text-neutral-500 mb-1">Cache Hit Rate</p>
									<p class="text-xl font-semibold text-orange-600 dark:text-orange-400">
										{formatPercent(qualityIndicators.overall_cache_hit_rate)}
									</p>
								</div>
								<div class="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20">
									<p class="text-xs text-neutral-500 mb-1">Session Continuation</p>
									<p class="text-xl font-semibold text-blue-600 dark:text-blue-400">
										{formatPercent(qualityIndicators.session_continuation_rate)}
									</p>
								</div>
								<div class="p-3 rounded-lg bg-green-50 dark:bg-green-900/20">
									<p class="text-xs text-neutral-500 mb-1">Cached Continuation</p>
									<p class="text-xl font-semibold text-green-600 dark:text-green-400">
										{qualityIndicators.cached_continuation_rate !== null ? formatPercent(qualityIndicators.cached_continuation_rate) : 'N/A'}
									</p>
								</div>
								<div class="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20">
									<p class="text-xs text-neutral-500 mb-1">Uncached Continuation</p>
									<p class="text-xl font-semibold text-purple-600 dark:text-purple-400">
										{qualityIndicators.uncached_continuation_rate !== null ? formatPercent(qualityIndicators.uncached_continuation_rate) : 'N/A'}
									</p>
								</div>
							</div>
							<div class="p-4 rounded-lg bg-neutral-50 dark:bg-neutral-700">
								<p class="text-sm text-neutral-700 dark:text-neutral-300">{qualityIndicators.quality_assessment}</p>
								<p class="text-xs text-neutral-500 mt-2">Based on {qualityIndicators.sample_size.toLocaleString()} sessions</p>
							</div>
						</div>
					{/if}

					<!-- Empty state if no data -->
					{#if !cacheEffectiveness && !modelImpact && !featureEfficiency && !tuningRecommendations && !qualityIndicators}
						<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-12 text-center">
							<Lightbulb class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
							<p class="text-neutral-600 dark:text-neutral-400">No insight data available yet</p>
							<p class="text-sm text-neutral-500 mt-1">Data will appear once there are API cost records</p>
						</div>
					{/if}
				{/if}
			</div>
		{/if}
	</main>

	<!-- Add Fixed Cost Modal -->
	{#if showAddModal}
		<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" role="dialog" aria-modal="true">
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl w-full max-w-md mx-4">
				<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Add Fixed Cost</h3>
					<button
						onclick={closeAddModal}
						class="p-1 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded transition-colors"
					>
						<X class="w-5 h-5" />
					</button>
				</div>
				<div class="p-6 space-y-4">
					{#if addError}
						<Alert variant="error">{addError}</Alert>
					{/if}
					<div>
						<label for="cost-provider" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
							Provider <span class="text-danger-500">*</span>
						</label>
						<input
							id="cost-provider"
							type="text"
							bind:value={newCost.provider}
							placeholder="e.g., DigitalOcean, Neon, Redis"
							class="w-full px-3 py-2 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
						/>
					</div>
					<div>
						<label for="cost-description" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
							Description <span class="text-danger-500">*</span>
						</label>
						<input
							id="cost-description"
							type="text"
							bind:value={newCost.description}
							placeholder="e.g., Database hosting, CDN bandwidth"
							class="w-full px-3 py-2 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
						/>
					</div>
					<div class="grid grid-cols-2 gap-4">
						<div>
							<label for="cost-amount" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
								Monthly Amount (USD) <span class="text-danger-500">*</span>
							</label>
							<div class="relative">
								<span class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500">$</span>
								<input
									id="cost-amount"
									type="number"
									step="0.01"
									min="0"
									bind:value={newCost.monthly_amount_usd}
									class="w-full pl-7 pr-3 py-2 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
								/>
							</div>
						</div>
						<div>
							<label for="cost-category" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
								Category
							</label>
							<select
								id="cost-category"
								bind:value={newCost.category}
								class="w-full px-3 py-2 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
							>
								<option value="compute">Compute</option>
								<option value="database">Database</option>
								<option value="storage">Storage</option>
								<option value="api">API</option>
								<option value="other">Other</option>
							</select>
						</div>
					</div>
					<div>
						<label for="cost-notes" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
							Notes (optional)
						</label>
						<textarea
							id="cost-notes"
							bind:value={newCost.notes}
							rows="2"
							placeholder="Additional details..."
							class="w-full px-3 py-2 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 resize-none"
						></textarea>
					</div>
				</div>
				<div class="px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 flex justify-end gap-3">
					<Button variant="secondary" size="sm" onclick={closeAddModal} disabled={addingCost}>
						Cancel
					</Button>
					<Button variant="brand" size="sm" onclick={addFixedCost} disabled={addingCost}>
						{#if addingCost}
							<RefreshCw class="w-4 h-4 animate-spin" />
							Adding...
						{:else}
							<Plus class="w-4 h-4" />
							Add Cost
						{/if}
					</Button>
				</div>
			</div>
		</div>
	{/if}
</div>
