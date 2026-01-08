<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { apiClient } from '$lib/api/client';
	import type { DatasetDetailResponse, DatasetAnalysis, DatasetInsights, ColumnSemantic, DatasetResponse } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { setBreadcrumbLabel, clearBreadcrumbLabel } from '$lib/stores/breadcrumbLabels';
	import DatasetChat from '$lib/components/dataset/DatasetChat.svelte';
	import DatasetChatHistory from '$lib/components/dataset/DatasetChatHistory.svelte';
	import AnalysisGallery from '$lib/components/dataset/AnalysisGallery.svelte';
	import DataInsightsPanel from '$lib/components/dataset/DataInsightsPanel.svelte';
	import KeyInsightsPanel from '$lib/components/dataset/KeyInsightsPanel.svelte';
	import BusinessContextForm from '$lib/components/dataset/BusinessContextForm.svelte';
	import ColumnReferenceSidebar from '$lib/components/dataset/ColumnReferenceSidebar.svelte';
	import QueryTemplates from '$lib/components/dataset/QueryTemplates.svelte';
	import FavouritesTab from '$lib/components/dataset/FavouritesTab.svelte';
	import type { DatasetReport, DatasetInvestigation, DatasetBusinessContext } from '$lib/api/types';

	const datasetId = $derived(page.params.dataset_id || '');

	// Use data fetch utility
	const datasetData = useDataFetch(() => apiClient.getDataset(datasetId));

	// Derived state
	const dataset = $derived<DatasetDetailResponse | null>(datasetData.data || null);
	const isLoading = $derived(datasetData.isLoading);
	const error = $derived(datasetData.error);

	// Profiling state
	let isProfiling = $state(false);
	let profileError = $state<string | null>(null);

	// Insights state
	let insights = $state<DatasetInsights | null>(null);
	let insightsLoading = $state(false);
	let insightsError = $state<string | null>(null);

	// Investigation state (deterministic analyses)
	let investigation = $state<DatasetInvestigation | null>(null);
	let investigationLoading = $state(false);
	let investigationError = $state<string | null>(null);

	// Business context state
	let businessContext = $state<DatasetBusinessContext | null>(null);
	let contextLoading = $state(false);
	let contextSaving = $state(false);
	let showContextForm = $state(false);

	// Analysis history state
	let analyses = $state<DatasetAnalysis[]>([]);
	let analysesLoading = $state(false);
	let analysesError = $state<string | null>(null);

	// Reference to chat component for asking questions
	let chatComponent = $state<{ askQuestion: (q: string) => void } | null>(null);

	// Conversation history state
	let selectedConversationId = $state<string | null>(null);
	let historyComponent = $state<{ refresh: () => void } | null>(null);

	// Column sidebar state - hidden by default for expanded chat area
	let showColumnSidebar = $state(false);

	// Mobile history sidebar state
	let showMobileHistory = $state(false);

	// Tab state for Analysis History / Favourites
	let activeTab = $state<'history' | 'favourites'>('history');

	// Generated report state
	let generatedReport = $state<DatasetReport | null>(null);

	// Compare state
	let showCompareDropdown = $state(false);
	let otherDatasets = $state<DatasetResponse[]>([]);
	let loadingOtherDatasets = $state(false);

	function handleReportGenerated(report: DatasetReport) {
		generatedReport = report;
		// Navigate to report view
		window.location.href = `/datasets/${datasetId}/report/${report.id}`;
	}

	async function loadOtherDatasets() {
		if (otherDatasets.length > 0) return; // Already loaded
		loadingOtherDatasets = true;
		try {
			const response = await apiClient.getDatasets({ limit: 50 });
			otherDatasets = (response.datasets ?? []).filter((d) => d.id !== datasetId);
		} catch (err) {
			console.error('Failed to load datasets for comparison:', err);
		} finally {
			loadingOtherDatasets = false;
		}
	}

	function handleCompareClick() {
		showCompareDropdown = !showCompareDropdown;
		if (showCompareDropdown) {
			loadOtherDatasets();
		}
	}

	function startComparison(otherDatasetId: string) {
		showCompareDropdown = false;
		goto(`/datasets/${datasetId}/compare/${otherDatasetId}`);
	}

	// Derive column semantics from insights
	const columnSemantics = $derived<ColumnSemantic[]>(
		insights?.column_semantics ?? []
	);

	function handleConversationSelect(id: string) {
		selectedConversationId = id;
	}

	function handleNewConversation() {
		selectedConversationId = null;
	}

	function handleConversationChange(newId: string | null) {
		if (newId) {
			selectedConversationId = newId;
			// Refresh history to show new conversation
			historyComponent?.refresh();
		}
	}

	function handleTemplateSelect(query: string) {
		// Use the chat component's method to set the question
		if (chatComponent?.askQuestion) {
			chatComponent.askQuestion(query);
		}
	}

	function toggleColumnSidebar() {
		showColumnSidebar = !showColumnSidebar;
	}

	async function fetchInsights(regenerate = false) {
		insightsError = null;

		// Stale-while-revalidate: try to show cached data immediately
		const cacheKey = `insights:${datasetId}`;
		if (!regenerate && typeof sessionStorage !== 'undefined') {
			try {
				const cached = sessionStorage.getItem(cacheKey);
				if (cached) {
					insights = JSON.parse(cached);
					// Don't show loading if we have cached data
				}
			} catch {
				// Ignore cache errors
			}
		}

		// Only show loading if we have no cached data
		if (!insights) {
			insightsLoading = true;
		}

		try {
			const response = await apiClient.getDatasetInsights(datasetId, regenerate);
			insights = response.insights;
			// Cache for future visits
			if (response.insights && typeof sessionStorage !== 'undefined') {
				try {
					sessionStorage.setItem(cacheKey, JSON.stringify(response.insights));
				} catch {
					// Ignore storage errors
				}
			}
		} catch (err: unknown) {
			// Check for 422 status (not profiled yet) - silently skip, not an error
			const status = (err as { status?: number }).status;
			const errMsg = err instanceof Error ? err.message : String(err);
			const isNotProfiled = status === 422 || errMsg.includes('profiled') || errMsg.includes('422');

			if (isNotProfiled) {
				// Dataset not profiled yet - expected state, don't log as error
				insights = null;
				insightsError = null;
			} else {
				console.error('[Insights] Error fetching insights:', err);
				insightsError = errMsg || 'Failed to load insights';
			}
		} finally {
			insightsLoading = false;
		}
	}

	async function fetchInvestigation(runNew = false) {
		investigationError = null;

		// Try to get cached investigation first
		if (!runNew) {
			try {
				investigationLoading = true;
				investigation = await apiClient.getDatasetInvestigation(datasetId);
				return;
			} catch {
				// No cached investigation, will try to run new one
			}
		}

		// Run new investigation
		investigationLoading = true;
		try {
			investigation = await apiClient.investigateDataset(datasetId);
		} catch (err: unknown) {
			// Check for 422 status (not profiled yet) - silently skip
			const status = (err as { status?: number }).status;
			const errMsg = err instanceof Error ? err.message : String(err);
			const isNotProfiled = status === 422 || errMsg.includes('profiled') || errMsg.includes('422');

			if (isNotProfiled) {
				investigation = null;
				investigationError = null;
			} else {
				console.error('[Investigation] Error:', err);
				investigationError = errMsg || 'Failed to run investigation';
			}
		} finally {
			investigationLoading = false;
		}
	}

	async function fetchBusinessContext() {
		contextLoading = true;
		try {
			const response = await apiClient.getDatasetBusinessContext(datasetId);
			businessContext = {
				business_goal: response.business_goal,
				key_metrics: response.key_metrics,
				kpis: response.kpis,
				objectives: response.objectives,
				industry: response.industry,
				additional_context: response.additional_context
			};
		} catch {
			// No context saved yet - that's fine
			businessContext = null;
		} finally {
			contextLoading = false;
		}
	}

	async function saveBusinessContext(context: DatasetBusinessContext) {
		contextSaving = true;
		try {
			await apiClient.setDatasetBusinessContext(datasetId, context);
			businessContext = context;
			showContextForm = false;
			// Regenerate insights with new context
			await fetchInsights(true);
		} catch (err) {
			console.error('Failed to save business context:', err);
		} finally {
			contextSaving = false;
		}
	}

	async function fetchAnalyses() {
		analysesLoading = true;
		analysesError = null;
		try {
			const response = await apiClient.getDatasetAnalyses(datasetId);
			analyses = (response.analyses ?? []) as typeof analyses;
		} catch (err) {
			analysesError = err instanceof Error ? err.message : 'Failed to load analyses';
		} finally {
			analysesLoading = false;
		}
	}

	function handleQuestionClick(question: string) {
		// Scroll to chat and pre-fill question
		const chatSection = document.getElementById('dataset-chat');
		if (chatSection) {
			chatSection.scrollIntoView({ behavior: 'smooth' });
		}
		// Use the chat component's method if available
		if (chatComponent?.askQuestion) {
			chatComponent.askQuestion(question);
		}
	}

	onMount(() => {
		datasetData.fetch();
		fetchAnalyses();
		fetchBusinessContext();
		// Fetch insights and investigation after a small delay to let profile load first
		setTimeout(() => {
			fetchInsights();
			fetchInvestigation();
		}, 100);
	});

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatBytes(bytes: number | null): string {
		if (!bytes) return '—';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	function formatValue(value: unknown): string {
		if (value === null || value === undefined) return '—';
		if (typeof value === 'number') {
			return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
		}
		return String(value);
	}

	function getTypeColor(type: string): string {
		switch (type.toLowerCase()) {
			case 'integer':
			case 'float':
			case 'numeric':
				return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
			case 'string':
			case 'text':
				return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
			case 'date':
			case 'datetime':
			case 'timestamp':
				return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300';
			case 'boolean':
				return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300';
			case 'currency':
				return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300';
			case 'percentage':
				return 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300';
			default:
				return 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300';
		}
	}

	async function handleProfile() {
		isProfiling = true;
		profileError = null;

		try {
			await apiClient.profileDataset(datasetId);
			await datasetData.fetch();
			// Fetch insights and investigation after profiling
			await Promise.all([fetchInsights(), fetchInvestigation(true)]);
		} catch (err) {
			profileError = err instanceof Error ? err.message : 'Profiling failed';
		} finally {
			isProfiling = false;
		}
	}

	// Set breadcrumb label when dataset loads
	$effect(() => {
		if (dataset?.name) {
			setBreadcrumbLabel(`/datasets/${datasetId}`, dataset.name);
		}
		return () => clearBreadcrumbLabel(`/datasets/${datasetId}`);
	});
</script>

<svelte:head>
	<title>{dataset?.name || 'Dataset'} - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if isLoading}
			<div class="space-y-6">
				<ShimmerSkeleton type="card" />
				<ShimmerSkeleton type="card" />
			</div>
		{:else if error}
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-6">
				<div class="flex items-center gap-3">
					<svg class="w-6 h-6 text-error-600 dark:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<div>
						<h3 class="text-lg font-semibold text-error-900 dark:text-error-200">Error Loading Dataset</h3>
						<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
					</div>
				</div>
				<div class="mt-4">
					<Button variant="danger" size="md" onclick={() => datasetData.fetch()}>
						{#snippet children()}
							Retry
						{/snippet}
					</Button>
				</div>
			</div>
		{:else if dataset}
			<!-- Header -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6 mb-6">
				<div class="flex items-start justify-between">
					<div class="flex items-center gap-4">
						<span class="w-12 h-12 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg class="w-6 h-6 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
							</svg>
						</span>
						<div>
							<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">{dataset.name}</h1>
							{#if dataset.description}
								<p class="text-neutral-600 dark:text-neutral-400 mt-1">{dataset.description}</p>
							{/if}
						</div>
					</div>
					<div class="flex items-center gap-3">
						<!-- Compare Button -->
						<div class="relative">
							<button
								onclick={handleCompareClick}
								class="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-600 transition-colors"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
								</svg>
								Compare
								<svg class="w-4 h-4 transition-transform {showCompareDropdown ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
								</svg>
							</button>
							{#if showCompareDropdown}
								<div class="absolute right-0 mt-2 w-64 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 shadow-lg z-50">
									<div class="p-2 border-b border-neutral-100 dark:border-neutral-700">
										<p class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Compare with</p>
									</div>
									<div class="max-h-64 overflow-y-auto">
										{#if loadingOtherDatasets}
											<div class="p-4 text-center">
												<div class="animate-spin w-5 h-5 border-2 border-neutral-300 border-t-primary-500 rounded-full mx-auto"></div>
											</div>
										{:else if otherDatasets.length === 0}
											<div class="p-4 text-center text-sm text-neutral-500 dark:text-neutral-400">
												No other datasets available
											</div>
										{:else}
											{#each otherDatasets as otherDataset}
												<button
													onclick={() => startComparison(otherDataset.id)}
													class="w-full px-4 py-2 text-left text-sm hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
												>
													<span class="font-medium text-neutral-900 dark:text-neutral-100">{otherDataset.name}</span>
													{#if otherDataset.row_count}
														<span class="text-neutral-500 dark:text-neutral-400 ml-2">({otherDataset.row_count.toLocaleString()} rows)</span>
													{/if}
												</button>
											{/each}
										{/if}
									</div>
								</div>
							{/if}
						</div>
						<span class="px-3 py-1 text-sm font-medium rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400 uppercase">
							{dataset.source_type}
						</span>
					</div>
				</div>

				<!-- Stats Row -->
				<div class="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
					<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-4">
						<div class="text-sm text-neutral-500 dark:text-neutral-400">Rows</div>
						<div class="text-xl font-semibold text-neutral-900 dark:text-white">
							{dataset.row_count?.toLocaleString() || '—'}
						</div>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-4">
						<div class="text-sm text-neutral-500 dark:text-neutral-400">Columns</div>
						<div class="text-xl font-semibold text-neutral-900 dark:text-white">
							{dataset.column_count || '—'}
						</div>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-4">
						<div class="text-sm text-neutral-500 dark:text-neutral-400">File Size</div>
						<div class="text-xl font-semibold text-neutral-900 dark:text-white">
							{formatBytes(dataset.file_size_bytes ?? null)}
						</div>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-4">
						<div class="text-sm text-neutral-500 dark:text-neutral-400">Updated</div>
						<div class="text-sm font-semibold text-neutral-900 dark:text-white">
							{formatDate(dataset.updated_at)}
						</div>
					</div>
				</div>
			</div>

			<!-- Data Insights Section -->
			{#if (dataset.profiles?.length ?? 0) > 0}
				<div class="mb-6">
					<DataInsightsPanel
						{insights}
						{datasetId}
						loading={insightsLoading}
						error={insightsError}
						onQuestionClick={handleQuestionClick}
						onRefresh={() => fetchInsights(true)}
					/>
				</div>
			{/if}

			<!-- Key Insights (Deterministic Analyses) -->
			{#if (dataset.profiles?.length ?? 0) > 0}
				<div class="mb-6">
					<KeyInsightsPanel
						{investigation}
						loading={investigationLoading}
						error={investigationError}
						onRefresh={() => fetchInvestigation(true)}
					/>
				</div>
			{/if}

			<!-- Business Context Section -->
			{#if (dataset.profiles?.length ?? 0) > 0}
				<div class="mb-6">
					{#if showContextForm}
						<BusinessContextForm
							context={businessContext}
							loading={contextLoading}
							saving={contextSaving}
							onSave={saveBusinessContext}
							onCancel={() => showContextForm = false}
						/>
					{:else}
						<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
							<div class="flex items-center justify-between">
								<div class="flex items-center gap-3">
									<span class="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
										<svg class="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
										</svg>
									</span>
									<div>
										<h3 class="font-medium text-neutral-900 dark:text-white">Business Context</h3>
										{#if businessContext?.business_goal}
											<p class="text-sm text-neutral-500 dark:text-neutral-400 truncate max-w-md">
												{businessContext.business_goal}
											</p>
										{:else}
											<p class="text-sm text-neutral-500 dark:text-neutral-400">
												Add your goals and KPIs for smarter insights
											</p>
										{/if}
									</div>
								</div>
								<Button variant="secondary" size="sm" onclick={() => showContextForm = true}>
									{#snippet children()}
										{#if businessContext}
											Edit Context
										{:else}
											Add Context
										{/if}
									{/snippet}
								</Button>
							</div>
							{#if businessContext}
								<div class="mt-3 flex flex-wrap gap-2">
									{#if businessContext.industry}
										<span class="px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
											{businessContext.industry}
										</span>
									{/if}
									{#if businessContext.key_metrics?.length}
										{#each businessContext.key_metrics.slice(0, 3) as metric}
											<span class="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
												{metric}
											</span>
										{/each}
										{#if businessContext.key_metrics.length > 3}
											<span class="px-2 py-1 text-xs text-neutral-500">+{businessContext.key_metrics.length - 3} more</span>
										{/if}
									{/if}
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/if}

			<!-- Column Profiles -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
						<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
						</svg>
						Column Profiles
					</h2>
					{#if (dataset.profiles?.length ?? 0) === 0}
						<Button variant="brand" size="md" onclick={handleProfile} disabled={isProfiling}>
							{#snippet children()}
								{#if isProfiling}
									<svg class="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
									Generating...
								{:else}
									Generate Profile
								{/if}
							{/snippet}
						</Button>
					{/if}
				</div>

				{#if profileError}
					<div class="mb-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4">
						<p class="text-sm text-error-700 dark:text-error-300">{profileError}</p>
					</div>
				{/if}

				{#if (dataset.profiles?.length ?? 0) === 0}
					<div class="text-center py-8">
						<svg class="w-12 h-12 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
						<p class="text-neutral-600 dark:text-neutral-400">
							No profile data yet. Click "Generate Profile" to analyze this dataset.
						</p>
					</div>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b border-neutral-200 dark:border-neutral-700">
									<th class="text-left py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Column</th>
									<th class="text-left py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Type</th>
									<th class="text-right py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Nulls</th>
									<th class="text-right py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Unique</th>
									<th class="text-right py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Min</th>
									<th class="text-right py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Max</th>
									<th class="text-right py-3 px-4 font-medium text-neutral-600 dark:text-neutral-400">Mean</th>
								</tr>
							</thead>
							<tbody>
								{#each dataset.profiles as profile (profile.id)}
									<tr class="border-b border-neutral-100 dark:border-neutral-700/50 hover:bg-neutral-50 dark:hover:bg-neutral-700/30">
										<td class="py-3 px-4 font-medium text-neutral-900 dark:text-white">
											{profile.column_name}
										</td>
										<td class="py-3 px-4">
											<span class="px-2 py-1 text-xs font-medium rounded {getTypeColor(profile.data_type)}">
												{profile.data_type}
											</span>
										</td>
										<td class="py-3 px-4 text-right text-neutral-600 dark:text-neutral-400">
											{formatValue(profile.null_count)}
										</td>
										<td class="py-3 px-4 text-right text-neutral-600 dark:text-neutral-400">
											{formatValue(profile.unique_count)}
										</td>
										<td class="py-3 px-4 text-right text-neutral-600 dark:text-neutral-400">
											{formatValue(profile.min_value)}
										</td>
										<td class="py-3 px-4 text-right text-neutral-600 dark:text-neutral-400">
											{formatValue(profile.max_value)}
										</td>
										<td class="py-3 px-4 text-right text-neutral-600 dark:text-neutral-400">
											{formatValue(profile.mean_value)}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>

			<!-- Chat Section with History Sidebar and Column Reference -->
			<div id="dataset-chat" class="mt-6">
				<!-- Query Templates -->
				{#if columnSemantics.length > 0}
					<div class="mb-4">
						<QueryTemplates
							{columnSemantics}
							onSelectTemplate={handleTemplateSelect}
						/>
					</div>
				{/if}

				<!-- Mobile History Toggle -->
				<div class="lg:hidden mb-3 flex items-center gap-2">
					<button
						onclick={() => showMobileHistory = true}
						class="flex items-center gap-2 px-3 py-2 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						History
					</button>
					<button
						onclick={handleNewConversation}
						class="flex items-center gap-1 px-3 py-2 text-sm font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
						</svg>
						New
					</button>
				</div>

				<!-- Mobile History Drawer -->
				{#if showMobileHistory}
					<button
						onclick={() => showMobileHistory = false}
						class="fixed inset-0 bg-black/20 dark:bg-black/40 z-40 lg:hidden"
						aria-label="Close history"
					></button>
					<div class="fixed left-0 top-0 h-full w-72 z-50 bg-white dark:bg-neutral-800 border-r border-neutral-200 dark:border-neutral-700 shadow-xl lg:hidden">
						<div class="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
							<h3 class="font-semibold text-neutral-900 dark:text-white">Chat History</h3>
							<button
								onclick={() => showMobileHistory = false}
								class="p-1.5 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-500"
								aria-label="Close history"
							>
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
								</svg>
							</button>
						</div>
						<div class="h-[calc(100%-56px)]">
							<DatasetChatHistory
								{datasetId}
								selectedId={selectedConversationId}
								onSelect={(id) => { handleConversationSelect(id); showMobileHistory = false; }}
								onNew={() => { handleNewConversation(); showMobileHistory = false; }}
							/>
						</div>
					</div>
				{/if}

				<div class="flex gap-4 relative">
					<!-- Chat History Sidebar - narrower, hidden on mobile -->
					<div class="hidden lg:block w-48 flex-shrink-0 bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 min-h-[400px]">
						<DatasetChatHistory
							{datasetId}
							selectedId={selectedConversationId}
							onSelect={handleConversationSelect}
							onNew={handleNewConversation}
							bind:this={historyComponent}
						/>
					</div>

					<!-- Chat Interface - flexible height -->
					<div class="flex-1 min-w-0">
						<DatasetChat
							{datasetId}
							{selectedConversationId}
							{columnSemantics}
							onConversationChange={handleConversationChange}
							onShowColumns={toggleColumnSidebar}
							onAnalysisCreated={fetchAnalyses}
							bind:this={chatComponent}
						/>
					</div>

					<!-- Column Reference Sidebar - slide-out drawer on right -->
					{#if columnSemantics.length > 0}
						<ColumnReferenceSidebar
							columns={columnSemantics}
							{datasetId}
							isOpen={showColumnSidebar}
							onToggle={toggleColumnSidebar}
						/>
					{/if}
				</div>
			</div>

			<!-- Analysis History / Favourites Section with Tabs -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 mt-6">
				<!-- Tab Bar -->
				<div class="flex border-b border-neutral-200 dark:border-neutral-700">
					<button
						onclick={() => activeTab = 'history'}
						class="flex items-center gap-2 px-6 py-4 text-sm font-medium transition-colors border-b-2 -mb-px
							{activeTab === 'history'
								? 'border-brand-500 text-brand-600 dark:text-brand-400'
								: 'border-transparent text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
						</svg>
						Analysis History
					</button>
					<button
						onclick={() => activeTab = 'favourites'}
						class="flex items-center gap-2 px-6 py-4 text-sm font-medium transition-colors border-b-2 -mb-px
							{activeTab === 'favourites'
								? 'border-brand-500 text-brand-600 dark:text-brand-400'
								: 'border-transparent text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
						</svg>
						Favourites
					</button>
				</div>

				<!-- Tab Content -->
				<div class="p-6">
					{#if activeTab === 'history'}
						<AnalysisGallery {analyses} {datasetId} loading={analysesLoading} error={analysesError} />
					{:else}
						<FavouritesTab {datasetId} onReportGenerated={handleReportGenerated} />
					{/if}
				</div>
			</div>
		{/if}
	</main>
</div>
