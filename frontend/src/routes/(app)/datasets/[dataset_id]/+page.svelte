<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { apiClient } from '$lib/api/client';
	import type {
		DatasetDetailResponse,
		DatasetAnalysis,
		DatasetInsights,
		ColumnSemantic,
		DatasetReportResponse,
		DatasetInvestigation,
		DatasetBusinessContext,
		ObjectiveAnalysisResponse,
		ObjectiveInsight,
		DataQualityIssue,
		DatasetFixResponse,
		ConversationMessage,
		AnalyzeDatasetRequest
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


	// Objective Analysis components
	import DataStory from '$lib/components/datasets/DataStory.svelte';
	import ObjectiveBar from '$lib/components/datasets/ObjectiveBar.svelte';
	import RelevanceNotice from '$lib/components/datasets/RelevanceNotice.svelte';
	import SuggestedQuestions from '$lib/components/datasets/SuggestedQuestions.svelte';
	import NoContextFallback from '$lib/components/datasets/NoContextFallback.svelte';

	// Report Builder component
	import ReportBuilder from '$lib/components/datasets/ReportBuilder.svelte';

	// Similar Datasets component
	import SimilarDatasetsPanel from '$lib/components/datasets/SimilarDatasetsPanel.svelte';

	// Type for report items
	interface SelectedInsight {
		id: string;
		type: 'insight' | 'chat_message' | 'favourite';
		headline?: string;
		content: string;
		chart_spec?: object;
		figure_json?: object;
		included: boolean;
	}

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
	let generatedReport = $state<DatasetReportResponse | null>(null);

	// Report Builder state
	let reportPanelOpen = $state(false);
	let reportInsights = $state<SelectedInsight[]>([]);

	// Objective Analysis state
	let objectiveAnalysis = $state<ObjectiveAnalysisResponse | null>(null);
	let objectiveAnalysisLoading = $state(false);
	let objectiveAnalysisError = $state<string | null>(null);

	// Derived: objectives from analysis
	const objectiveNames = $derived<string[]>(
		objectiveAnalysis?.data_story?.objective_sections?.map((s) => s.objective_name) ?? []
	);

	// Derived: data quality issues from investigation
	const dataQualityIssues = $derived<DataQualityIssue[]>(
		investigation?.data_quality?.issues ?? []
	);

	// Derived: suggested questions from analysis
	const suggestedQuestions = $derived<string[]>(
		objectiveAnalysis?.data_story?.suggested_questions ?? []
	);

	// Derived: objective context for chat
	const objectiveContext = $derived(
		objectiveAnalysis
			? {
					objectives: objectiveNames,
					analysisMode: objectiveAnalysis.analysis_mode,
					relevanceScore: objectiveAnalysis.relevance_score ?? undefined
				}
			: null
	);

	function handleReportGenerated(report: DatasetReportResponse) {
		generatedReport = report;
		window.location.href = `/datasets/${datasetId}/report/${report.id}`;
	}

	// Derive column semantics from insights
	const columnSemantics = $derived<ColumnSemantic[]>(insights?.column_semantics ?? []);

	// Derived: column names for suggested questions
	const dataColumnNames = $derived<string[]>(
		columnSemantics.map((c) => c.column_name)
	);

	// Derived: is dataset profiled?
	const isProfiled = $derived((dataset?.profiles?.length ?? 0) > 0);

	// Derived: has business context set up?
	const hasBusinessContext = $derived(
		!!(businessContext?.business_goal || businessContext?.objectives?.length)
	);

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

	async function fetchObjectiveAnalysis() {
		objectiveAnalysisError = null;
		objectiveAnalysisLoading = true;

		try {
			const response = await apiClient.getObjectiveAnalysis(datasetId);
			objectiveAnalysis = response;
		} catch (err: unknown) {
			const status = (err as { status?: number }).status;
			// 404 means no analysis yet - not an error
			if (status === 404) {
				objectiveAnalysis = null;
				objectiveAnalysisError = null;
			} else {
				console.error('[ObjectiveAnalysis] Error:', err);
				objectiveAnalysisError = err instanceof Error ? err.message : 'Failed to load analysis';
			}
		} finally {
			objectiveAnalysisLoading = false;
		}
	}

	async function triggerObjectiveAnalysis(objectiveIndex?: number) {
		objectiveAnalysisError = null;
		objectiveAnalysisLoading = true;

		try {
			const request: AnalyzeDatasetRequest = {
				include_context: true
			};
			// If an objective index was passed (from "What Data Do I Need?" flow), use it
			if (objectiveIndex !== undefined) {
				request.objective_id = String(objectiveIndex);
				request.force_mode = 'objective_focused';
			}
			await apiClient.analyzeDatasetForObjectives(datasetId, request);
			// Fetch the results after triggering
			await fetchObjectiveAnalysis();
		} catch (err) {
			console.error('[ObjectiveAnalysis] Trigger error:', err);
			objectiveAnalysisError = err instanceof Error ? err.message : 'Failed to trigger analysis';
			objectiveAnalysisLoading = false;
		}
	}

	function handleInsightAddToReport(insight: ObjectiveInsight) {
		// Add insight to report builder
		const existingIndex = reportInsights.findIndex(
			(i) => i.type === 'insight' && i.headline === insight.headline
		);
		if (existingIndex === -1) {
			reportInsights = [
				...reportInsights,
				{
					id: crypto.randomUUID(),
					type: 'insight',
					headline: insight.headline,
					content: insight.narrative,
					chart_spec: insight.visualization as object | undefined,
					included: true
				}
			];
		}
		reportPanelOpen = true;
	}

	function handleInsightCreateAction(insight: ObjectiveInsight) {
		// TODO: Implement action creation from insight
		console.log('Create action:', insight);
	}

	function handleInsightExploreMore(insight: ObjectiveInsight) {
		// Open chat with follow-up question
		if (insight.follow_up_questions?.length > 0) {
			handleQuestionClick(insight.follow_up_questions[0]);
		}
	}

	function handleInsightShareWithBoard(insight: ObjectiveInsight) {
		// Navigate to new meeting with insight as context
		const insightContext = encodeURIComponent(JSON.stringify({
			headline: insight.headline,
			narrative: insight.narrative,
			objective_name: insight.objective_name,
			recommendation: insight.recommendation
		}));
		// Include objective_id if the insight is linked to one
		const params = new URLSearchParams();
		params.set('insight_context', insightContext);
		if (insight.objective_name) {
			params.set('objective', insight.objective_name);
		}
		window.location.href = `/meetings/new?${params.toString()}`;
	}

	function handleChangeObjectives() {
		// Navigate to context page to edit objectives
		window.location.href = '/context/strategic';
	}

	function handleDataFixed(result: DatasetFixResponse) {
		// Re-fetch dataset to get updated row count and profiles
		if (result.success && result.reanalysis_required) {
			// Refresh dataset info
			datasetData.fetch();
			// Re-trigger objective analysis
			fetchObjectiveAnalysis();
		}
	}

	function handleChatMessageAddToReport(message: ConversationMessage) {
		// Add chat message to report builder
		// Generate unique ID from content hash since ConversationMessage doesn't have an id field
		const messageId = `msg_${message.timestamp}_${message.content.slice(0, 20)}`;
		const existingIndex = reportInsights.findIndex(
			(i) => i.type === 'chat_message' && i.headline === (message.content?.slice(0, 60) + (message.content && message.content.length > 60 ? '...' : ''))
		);
		if (existingIndex === -1) {
			reportInsights = [
				...reportInsights,
				{
					id: messageId,
					type: 'chat_message',
					headline: message.content?.slice(0, 60) + (message.content && message.content.length > 60 ? '...' : ''),
					content: message.content || '',
					chart_spec: message.chart_spec as object | undefined,
					included: true
				}
			];
		}
		reportPanelOpen = true;
	}

	function handleReportBuilderClose() {
		reportPanelOpen = false;
	}

	function handleReportExport(format: 'markdown' | 'pdf') {
		console.log('[Dataset] Report exported as:', format);
	}

	// No context fallback handlers
	function handleSetupContext() {
		// Navigate to context page to set up business context
		window.location.href = '/context/strategic';
	}

	function handleAnalyzeAnyway() {
		// Trigger open exploration analysis without context
		triggerObjectiveAnalysis();
	}

	async function handleQuickGoalSubmit(goal: string) {
		// Save the quick goal as business context and trigger analysis
		contextSaving = true;
		try {
			const context: DatasetBusinessContext = {
				business_goal: goal,
				key_metrics: [],
				kpis: [],
				objectives: goal,
				industry: businessContext?.industry || '',
				additional_context: ''
			};
			await apiClient.setDatasetBusinessContext(datasetId, context);
			businessContext = context;
			// Trigger objective-focused analysis
			await triggerObjectiveAnalysis();
		} catch (err) {
			console.error('Failed to save quick goal:', err);
		} finally {
			contextSaving = false;
		}
	}

	onMount(() => {
		datasetData.fetch();
		fetchAnalyses();
		fetchBusinessContext();

		// Check for objective_index from "What Data Do I Need?" flow
		const objectiveIndexParam = page.url.searchParams.get('objective_index');
		if (objectiveIndexParam !== null) {
			// Auto-trigger objective-focused analysis with the selected objective
			const objectiveIndex = parseInt(objectiveIndexParam, 10);
			if (!isNaN(objectiveIndex)) {
				triggerObjectiveAnalysis(objectiveIndex);
			} else {
				fetchObjectiveAnalysis();
			}
		} else {
			fetchObjectiveAnalysis();
		}

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

			<!-- Header Bar with Relevance Badge and Report Button -->
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-3">
					{#if objectiveAnalysis?.relevance_score != null}
						<RelevanceNotice
							relevanceScore={objectiveAnalysis.relevance_score}
							relevanceAssessment={objectiveAnalysis.relevance_assessment}
							compact={true}
						/>
					{/if}
				</div>

				<!-- Report Builder Button -->
				<button
					onclick={() => reportPanelOpen = true}
					class="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors
						{reportInsights.length > 0
							? 'bg-brand-600 hover:bg-brand-700 text-white border-brand-600'
							: 'bg-white dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 border-neutral-200 dark:border-neutral-600 hover:bg-neutral-50 dark:hover:bg-neutral-600'}"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
					</svg>
					Report
					{#if reportInsights.length > 0}
						<span class="px-1.5 py-0.5 text-xs font-semibold rounded-full bg-white/20">
							{reportInsights.length}
						</span>
					{/if}
				</button>
			</div>

			<!-- Story View: Data Story with Objective Analysis -->
				<div class="space-y-6 mb-6">
					<!-- Objective Bar -->
					{#if objectiveNames.length > 0 || objectiveAnalysis}
						<ObjectiveBar
							objectives={objectiveNames}
							relevanceScore={objectiveAnalysis?.relevance_score}
							analysisMode={objectiveAnalysis?.analysis_mode ?? 'open_exploration'}
							onChangeObjectives={handleChangeObjectives}
						/>
					{/if}

					<!-- Loading state -->
					{#if objectiveAnalysisLoading}
						<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-8">
							<div class="flex flex-col items-center justify-center space-y-4">
								<div class="animate-spin w-8 h-8 border-4 border-brand-200 border-t-brand-600 rounded-full"></div>
								<p class="text-neutral-600 dark:text-neutral-400">Analyzing your data...</p>
							</div>
						</div>
					{:else if objectiveAnalysisError}
						<!-- Error state with helpful messaging -->
						<div class="bg-error-50 dark:bg-error-900/20 rounded-lg border border-error-200 dark:border-error-800 p-6">
							<div class="flex items-start gap-4">
								<div class="flex-shrink-0 p-2 rounded-lg bg-error-100 dark:bg-error-900/30">
									<svg class="w-6 h-6 text-error-600 dark:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
								</div>
								<div class="flex-1">
									<h3 class="font-semibold text-error-900 dark:text-error-200">Something went wrong</h3>
									<p class="text-sm text-error-700 dark:text-error-300 mt-1">{objectiveAnalysisError}</p>
									<p class="text-sm text-error-600 dark:text-error-400 mt-2">
										Please try again. If the issue persists, try refreshing the page.
									</p>
								</div>
							</div>
							<div class="flex items-center gap-3 mt-4 pt-4 border-t border-error-200 dark:border-error-700">
								<button
									onclick={fetchObjectiveAnalysis}
									class="inline-flex items-center gap-2 px-4 py-2 bg-error-600 hover:bg-error-700 text-white rounded-lg text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-error-500 focus-visible:ring-offset-2"
								>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
									</svg>
									Try Again
								</button>
							</div>
						</div>
					{:else if objectiveAnalysis}
						<!-- Data Story -->
						<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
							<DataStory
								datasetId={dataset.id}
								dataStory={objectiveAnalysis.data_story}
								insights={objectiveAnalysis.insights}
								analysisMode={objectiveAnalysis.analysis_mode}
								{dataQualityIssues}
								loading={objectiveAnalysisLoading}
								onAddToReport={handleInsightAddToReport}
								onCreateAction={handleInsightCreateAction}
								onExploreMore={handleInsightExploreMore}
								onShareWithBoard={handleInsightShareWithBoard}
								onAskQuestion={handleQuestionClick}
								onDataFixed={handleDataFixed}
							/>
						</div>

						<!-- Conversation Section - Elevated in Story View -->
						<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
							<div class="flex items-center gap-3 mb-4">
								<div class="p-2 rounded-lg bg-brand-100 dark:bg-brand-900/30">
									<svg class="w-5 h-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
									</svg>
								</div>
								<div>
									<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Explore Your Data</h2>
									<p class="text-sm text-neutral-500 dark:text-neutral-400">Ask questions to dive deeper into your insights</p>
								</div>
							</div>

							<!-- Suggested Questions -->
							<div class="mb-4">
								<SuggestedQuestions
									analysisMode={objectiveAnalysis.analysis_mode}
									{suggestedQuestions}
									objectives={objectiveNames}
									dataColumns={dataColumnNames}
									onAskQuestion={handleQuestionClick}
								/>
							</div>

							<!-- Inline Chat -->
							<DatasetChat
								{datasetId}
								{selectedConversationId}
								{columnSemantics}
								{objectiveContext}
								onConversationChange={handleConversationChange}
								onShowColumns={toggleColumnSidebar}
								onAnalysisCreated={fetchAnalyses}
								onAddToReport={handleChatMessageAddToReport}
								bind:this={chatComponent}
							/>
						</div>
					{:else if isProfiled}
						<!-- No analysis yet - show context fallback or analyze prompt -->
						{#if !hasBusinessContext}
							<NoContextFallback
								onSetupContext={handleSetupContext}
								onAnalyzeAnyway={handleAnalyzeAnyway}
								onQuickGoalSubmit={handleQuickGoalSubmit}
								loading={objectiveAnalysisLoading || contextSaving}
							/>
						{:else}
							<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-8 text-center">
								<svg class="w-16 h-16 mx-auto text-neutral-300 dark:text-neutral-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
								</svg>
								<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">Ready for Objective Analysis</h3>
								<p class="text-neutral-600 dark:text-neutral-400 mb-4 max-w-md mx-auto">
									Analyze your data with your business objectives in mind. Get insights that directly connect to what matters to you.
								</p>
								<Button variant="brand" size="md" onclick={() => triggerObjectiveAnalysis()}>
									{#snippet children()}
										<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
										</svg>
										Analyze with Your Objectives
									{/snippet}
								</Button>
							</div>
						{/if}
					{:else}
						<!-- Profile required first -->
						<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-8 text-center">
							<svg class="w-16 h-16 mx-auto text-neutral-300 dark:text-neutral-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
							</svg>
							<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">Profile Your Data First</h3>
							<p class="text-neutral-600 dark:text-neutral-400 mb-4">
								Generate a profile to understand your data before running objective analysis.
							</p>
							<Button variant="brand" size="md" onclick={handleProfile} disabled={isProfiling}>
								{#snippet children()}
									{#if isProfiling}
										<svg class="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
											<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
											<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
										</svg>
										Generating Profile...
									{:else}
										Generate Profile
									{/if}
								{/snippet}
							</Button>
						</div>
					{/if}
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

			<!-- Similar Datasets Panel -->
			<SimilarDatasetsPanel {datasetId} />
		{/if}
	</main>

	<!-- Floating chat bar removed - using inline chat in Story View instead -->
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

<!-- Report Builder Panel -->
{#if dataset}
	<ReportBuilder
		{datasetId}
		datasetName={dataset.name}
		isOpen={reportPanelOpen}
		selectedInsights={reportInsights}
		onClose={handleReportBuilderClose}
		onExport={handleReportExport}
		onReportGenerated={handleReportGenerated}
	/>
{/if}
