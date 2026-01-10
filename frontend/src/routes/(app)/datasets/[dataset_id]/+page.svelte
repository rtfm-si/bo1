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

	// Tab components
	import OverviewTab from '$lib/components/dataset/tabs/OverviewTab.svelte';
	import AnalyseTab from '$lib/components/dataset/tabs/AnalyseTab.svelte';
	import ClarifyTab from '$lib/components/dataset/tabs/ClarifyTab.svelte';
	import ChartsTab from '$lib/components/dataset/tabs/ChartsTab.svelte';
	import InsightsTab from '$lib/components/dataset/tabs/InsightsTab.svelte';

	// Objective Analysis components
	import DataStory from '$lib/components/datasets/DataStory.svelte';
	import ObjectiveBar from '$lib/components/datasets/ObjectiveBar.svelte';
	import RelevanceNotice from '$lib/components/datasets/RelevanceNotice.svelte';
	import SuggestedQuestions from '$lib/components/datasets/SuggestedQuestions.svelte';
	import NoContextFallback from '$lib/components/datasets/NoContextFallback.svelte';

	// Report Builder component
	import ReportBuilder from '$lib/components/datasets/ReportBuilder.svelte';

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

	// Report Builder state
	let reportPanelOpen = $state(false);
	let reportInsights = $state<SelectedInsight[]>([]);

	// Objective Analysis state
	let objectiveAnalysis = $state<ObjectiveAnalysisResponse | null>(null);
	let objectiveAnalysisLoading = $state(false);
	let objectiveAnalysisError = $state<string | null>(null);
	let showAdvancedMode = $state(false);

	// Feature discovery state (for "What's New" callout)
	let showFeatureCallout = $state(false);
	let featureCalloutDismissed = $state(false);

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

	function handleReportGenerated(report: DatasetReport) {
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
		// Switch to clarify tab to edit objectives
		activeTab = 'clarify';
		showAdvancedMode = true;
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
		// Navigate to context page or open clarify tab
		activeTab = 'clarify';
		showAdvancedMode = true;
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

	// Check feature callout on mount
	function checkFeatureCallout() {
		if (typeof localStorage !== 'undefined') {
			const dismissed = localStorage.getItem('story_view_callout_dismissed');
			if (!dismissed) {
				showFeatureCallout = true;
			} else {
				featureCalloutDismissed = true;
			}
		}
	}

	function dismissFeatureCallout() {
		showFeatureCallout = false;
		featureCalloutDismissed = true;
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem('story_view_callout_dismissed', 'true');
		}
	}

	onMount(() => {
		datasetData.fetch();
		fetchAnalyses();
		fetchBusinessContext();
		checkFeatureCallout();

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

			<!-- Feature Discovery Callout -->
			{#if showFeatureCallout && !featureCalloutDismissed && !showAdvancedMode}
				<div class="mb-4 bg-gradient-to-r from-brand-50 to-purple-50 dark:from-brand-900/20 dark:to-purple-900/20 rounded-lg border border-brand-200 dark:border-brand-800 p-4">
					<div class="flex items-start gap-3">
						<div class="flex-shrink-0 p-1.5 rounded-lg bg-brand-100 dark:bg-brand-900/40">
							<svg class="w-5 h-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
						</div>
						<div class="flex-1 min-w-0">
							<p class="text-sm font-medium text-brand-800 dark:text-brand-200">
								<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-semibold bg-brand-200 dark:bg-brand-800 text-brand-700 dark:text-brand-300 mr-1">New</span>
								Your data now tells a story
							</p>
							<p class="mt-1 text-sm text-brand-600 dark:text-brand-400">
								See insights aligned to your business objectives. Switch to Advanced Mode for detailed statistics.
							</p>
						</div>
						<button
							onclick={dismissFeatureCallout}
							class="flex-shrink-0 p-1 rounded hover:bg-brand-100 dark:hover:bg-brand-900/30 text-brand-500 dark:text-brand-400 transition-colors"
							aria-label="Dismiss"
						>
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
							</svg>
						</button>
					</div>
				</div>
			{/if}

			<!-- View Toggle & Relevance Badge -->
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

				<!-- Polished View Toggle -->
				<div class="inline-flex items-center rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-100 dark:bg-neutral-800 p-1" role="tablist" aria-label="View mode">
					<button
						role="tab"
						aria-selected={!showAdvancedMode}
						onclick={() => showAdvancedMode = false}
						class="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200
							{!showAdvancedMode
								? 'bg-white dark:bg-neutral-700 text-brand-700 dark:text-brand-300 shadow-sm'
								: 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
						</svg>
						Story View
					</button>
					<button
						role="tab"
						aria-selected={showAdvancedMode}
						onclick={() => showAdvancedMode = true}
						class="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200
							{showAdvancedMode
								? 'bg-white dark:bg-neutral-700 text-brand-700 dark:text-brand-300 shadow-sm'
								: 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
						</svg>
						Advanced
					</button>
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

			{#if showAdvancedMode}
				<!-- Advanced Mode: Tab Navigation -->
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
			{:else}
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
										Try again or switch to Advanced Mode for detailed statistics.
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
								<button
									onclick={() => showAdvancedMode = true}
									class="inline-flex items-center gap-2 px-4 py-2 text-error-700 dark:text-error-300 hover:bg-error-100 dark:hover:bg-error-900/30 rounded-lg text-sm font-medium transition-colors"
								>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
									</svg>
									Switch to Advanced Mode
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
			{/if}

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
