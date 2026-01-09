<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { apiClient } from '$lib/api/client';
	import type {
		DatasetDetailResponse,
		DatasetAnalysis,
		DatasetInsights,
		ColumnSemantic,
		DatasetReport,
		DatasetInvestigation,
		DatasetBusinessContext
	} from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button, Tabs } from '$lib/components/ui';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { setBreadcrumbLabel, clearBreadcrumbLabel } from '$lib/stores/breadcrumbLabels';

	// Component imports
	import DatasetHeader from '$lib/components/dataset/DatasetHeader.svelte';
	import DatasetChat from '$lib/components/dataset/DatasetChat.svelte';
	import DatasetChatHistory from '$lib/components/dataset/DatasetChatHistory.svelte';
	import ColumnReferenceSidebar from '$lib/components/dataset/ColumnReferenceSidebar.svelte';
	import QueryTemplates from '$lib/components/dataset/QueryTemplates.svelte';
	import AnalysisGallery from '$lib/components/dataset/AnalysisGallery.svelte';

	// Tab components
	import OverviewTab from '$lib/components/dataset/tabs/OverviewTab.svelte';
	import AnalyseTab from '$lib/components/dataset/tabs/AnalyseTab.svelte';
	import ClarifyTab from '$lib/components/dataset/tabs/ClarifyTab.svelte';
	import ChartsTab from '$lib/components/dataset/tabs/ChartsTab.svelte';
	import InsightsTab from '$lib/components/dataset/tabs/InsightsTab.svelte';

	const datasetId = $derived(page.params.dataset_id || '');

	// Use data fetch utility
	const datasetData = useDataFetch(() => apiClient.getDataset(datasetId));

	// Derived state
	const dataset = $derived<DatasetDetailResponse | null>(datasetData.data || null);
	const isLoading = $derived(datasetData.isLoading);
	const error = $derived(datasetData.error);

	// Tab state
	type TabId = 'overview' | 'analyse' | 'clarify' | 'charts' | 'insights';
	let activeTab = $state<TabId>('overview');

	const tabs: { id: TabId; label: string; icon: string }[] = [
		{ id: 'overview', label: 'Overview', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
		{ id: 'analyse', label: 'Analyse', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01' },
		{ id: 'clarify', label: 'Clarify', icon: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
		{ id: 'charts', label: 'Charts', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
		{ id: 'insights', label: 'Insights', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' }
	];

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

	// Analysis history state
	let analyses = $state<DatasetAnalysis[]>([]);
	let analysesLoading = $state(false);
	let analysesError = $state<string | null>(null);

	// Reference to chat component for asking questions
	let chatComponent = $state<{ askQuestion: (q: string) => void } | null>(null);

	// Conversation history state
	let selectedConversationId = $state<string | null>(null);
	let historyComponent = $state<{ refresh: () => void } | null>(null);

	// Column sidebar state
	let showColumnSidebar = $state(false);

	// Mobile history sidebar state
	let showMobileHistory = $state(false);

	// Chat expanded state for persistent bottom bar
	let chatExpanded = $state(false);

	// Generated report state
	let generatedReport = $state<DatasetReport | null>(null);

	function handleReportGenerated(report: DatasetReport) {
		generatedReport = report;
		window.location.href = `/datasets/${datasetId}/report/${report.id}`;
	}

	// Derive column semantics from insights
	const columnSemantics = $derived<ColumnSemantic[]>(insights?.column_semantics ?? []);

	// Derived: is dataset profiled?
	const isProfiled = $derived((dataset?.profiles?.length ?? 0) > 0);

	function handleConversationSelect(id: string) {
		selectedConversationId = id;
		chatExpanded = true;
	}

	function handleNewConversation() {
		selectedConversationId = null;
	}

	function handleConversationChange(newId: string | null) {
		if (newId) {
			selectedConversationId = newId;
			historyComponent?.refresh();
		}
	}

	function handleTemplateSelect(query: string) {
		if (chatComponent?.askQuestion) {
			chatComponent.askQuestion(query);
			chatExpanded = true;
		}
	}

	function toggleColumnSidebar() {
		showColumnSidebar = !showColumnSidebar;
	}

	function handleQuestionClick(question: string) {
		if (chatComponent?.askQuestion) {
			chatComponent.askQuestion(question);
			chatExpanded = true;
		}
	}

	async function fetchInsights(regenerate = false) {
		insightsError = null;

		const cacheKey = `insights:${datasetId}`;
		if (!regenerate && typeof sessionStorage !== 'undefined') {
			try {
				const cached = sessionStorage.getItem(cacheKey);
				if (cached) {
					insights = JSON.parse(cached);
				}
			} catch {
				// Ignore cache errors
			}
		}

		if (!insights) {
			insightsLoading = true;
		}

		try {
			const response = await apiClient.getEnhancedInsights(datasetId, regenerate);
			insights = response.insights;
			if (response.insights && typeof sessionStorage !== 'undefined') {
				try {
					sessionStorage.setItem(cacheKey, JSON.stringify(response.insights));
				} catch {
					// Ignore storage errors
				}
			}
		} catch (err: unknown) {
			const status = (err as { status?: number }).status;
			const errMsg = err instanceof Error ? err.message : String(err);
			const isNotProfiled = status === 422 || errMsg.includes('profiled') || errMsg.includes('422');

			if (isNotProfiled) {
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
		investigationLoading = true;

		try {
			if (!runNew) {
				try {
					investigation = await apiClient.getDatasetInvestigation(datasetId);
					return;
				} catch {
					// No cached investigation
				}
			}
			investigation = await apiClient.investigateDataset(datasetId);
		} catch (err: unknown) {
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

	async function updateColumnRole(columnName: string, newRole: string) {
		try {
			investigation = await apiClient.updateColumnRole(
				datasetId,
				columnName,
				newRole as 'metric' | 'dimension' | 'id' | 'timestamp' | 'unknown'
			);
		} catch (err) {
			console.error('[Investigation] Failed to update column role:', err);
			throw err;
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

	async function handleProfile() {
		isProfiling = true;
		profileError = null;

		try {
			await apiClient.profileDataset(datasetId);
			await datasetData.fetch();
			await Promise.all([fetchInsights(), fetchInvestigation(true)]);
		} catch (err) {
			profileError = err instanceof Error ? err.message : 'Profiling failed';
		} finally {
			isProfiling = false;
		}
	}

	onMount(() => {
		datasetData.fetch();
		fetchAnalyses();
		fetchBusinessContext();
		setTimeout(() => {
			fetchInsights();
			fetchInvestigation();
		}, 100);
	});

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

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800 pb-20">
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
			<!-- Dataset Header -->
			<div class="mb-6">
				<DatasetHeader {dataset} {datasetId} />
			</div>

			<!-- Tab Navigation -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 mb-6">
				<nav class="flex border-b border-neutral-200 dark:border-neutral-700 overflow-x-auto" aria-label="Dataset tabs">
					{#each tabs as tab}
						<button
							onclick={() => activeTab = tab.id}
							class="flex items-center gap-2 px-5 py-4 text-sm font-medium whitespace-nowrap transition-colors border-b-2 -mb-px
								{activeTab === tab.id
									? 'border-brand-500 text-brand-600 dark:text-brand-400 bg-brand-50/50 dark:bg-brand-900/10'
									: 'border-transparent text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-50 dark:hover:bg-neutral-700/50'}"
						>
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={tab.icon} />
							</svg>
							{tab.label}
						</button>
					{/each}
				</nav>

				<!-- Tab Content -->
				<div class="p-6">
					{#if activeTab === 'overview'}
						<OverviewTab
							{dataset}
							{datasetId}
							{insights}
							{insightsLoading}
							{insightsError}
							{isProfiling}
							{profileError}
							onProfile={handleProfile}
							onRefreshInsights={() => fetchInsights(true)}
							onQuestionClick={handleQuestionClick}
						/>
					{:else if activeTab === 'analyse'}
						{#if !isProfiled}
							<div class="text-center py-12">
								<svg class="w-16 h-16 mx-auto text-neutral-300 dark:text-neutral-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
								</svg>
								<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">Profile Required</h3>
								<p class="text-neutral-600 dark:text-neutral-400 mb-4">Generate a profile first to access analysis features.</p>
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
							</div>
						{:else}
							<AnalyseTab
								{dataset}
								{investigation}
								{investigationLoading}
								{investigationError}
								profiles={dataset.profiles ?? []}
								{isProfiling}
								{profileError}
								onRefreshInvestigation={() => fetchInvestigation(true)}
								onProfile={handleProfile}
								onUpdateColumnRole={updateColumnRole}
							/>
						{/if}
					{:else if activeTab === 'clarify'}
						<ClarifyTab
							context={businessContext}
							loading={contextLoading}
							saving={contextSaving}
							onSave={saveBusinessContext}
						/>
					{:else if activeTab === 'charts'}
						<ChartsTab
							{datasetId}
							profiles={dataset.profiles ?? []}
							onReportGenerated={handleReportGenerated}
						/>
					{:else if activeTab === 'insights'}
						<InsightsTab
							{datasetId}
							{insights}
							{investigation}
							loading={insightsLoading}
							error={insightsError}
							onQuestionClick={handleQuestionClick}
							onRefresh={() => fetchInsights(true)}
						/>
					{/if}
				</div>
			</div>

			<!-- Analysis History Section -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700">
				<div class="p-4 border-b border-neutral-200 dark:border-neutral-700">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
						<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						Analysis History
					</h2>
				</div>
				<div class="p-6">
					<AnalysisGallery {analyses} {datasetId} loading={analysesLoading} error={analysesError} />
				</div>
			</div>
		{/if}
	</main>

	<!-- Persistent Chat Bar -->
	{#if dataset}
		<div class="fixed bottom-0 left-0 right-0 z-40">
			<!-- Collapsed bar -->
			{#if !chatExpanded}
				<div class="bg-white dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700 shadow-lg">
					<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
						<button
							onclick={() => chatExpanded = true}
							class="w-full py-4 flex items-center justify-between hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors"
						>
							<div class="flex items-center gap-3">
								<span class="p-2 rounded-lg bg-brand-100 dark:bg-brand-900/30">
									<svg class="w-5 h-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
									</svg>
								</span>
								<span class="text-neutral-900 dark:text-white font-medium">Ask a question about your data...</span>
							</div>
							<svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
							</svg>
						</button>
					</div>
				</div>
			{:else}
				<!-- Expanded chat -->
				<div class="bg-white dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700 shadow-lg">
					<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
						<!-- Header -->
						<div class="flex items-center justify-between py-3 border-b border-neutral-100 dark:border-neutral-700">
							<div class="flex items-center gap-3">
								<span class="text-sm font-medium text-neutral-900 dark:text-white">Chat with your data</span>
								{#if columnSemantics.length > 0}
									<button
										onclick={toggleColumnSidebar}
										class="text-xs text-brand-600 dark:text-brand-400 hover:underline"
									>
										{columnSemantics.length} columns available
									</button>
								{/if}
							</div>
							<button
								onclick={() => chatExpanded = false}
								class="p-1.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-500"
								aria-label="Collapse chat"
							>
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
								</svg>
							</button>
						</div>

						<!-- Chat content -->
						<div class="flex gap-4 py-4" style="height: 400px;">
							<!-- History sidebar (desktop) -->
							<div class="hidden lg:block w-48 flex-shrink-0 bg-neutral-50 dark:bg-neutral-700/30 rounded-lg overflow-hidden">
								<DatasetChatHistory
									{datasetId}
									selectedId={selectedConversationId}
									onSelect={handleConversationSelect}
									onNew={handleNewConversation}
									bind:this={historyComponent}
								/>
							</div>

							<!-- Chat interface -->
							<div class="flex-1 min-w-0">
								{#if columnSemantics.length > 0}
									<div class="mb-3">
										<QueryTemplates
											{columnSemantics}
											onSelectTemplate={handleTemplateSelect}
										/>
									</div>
								{/if}
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

							<!-- Column sidebar -->
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
				</div>
			{/if}
		</div>
	{/if}
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
