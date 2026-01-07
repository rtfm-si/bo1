<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { apiClient } from '$lib/api/client';
	import type { DatasetDetailResponse, DatasetAnalysis, DatasetInsights, ColumnSemantic } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import Breadcrumb from '$lib/components/ui/Breadcrumb.svelte';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import DatasetChat from '$lib/components/dataset/DatasetChat.svelte';
	import DatasetChatHistory from '$lib/components/dataset/DatasetChatHistory.svelte';
	import AnalysisGallery from '$lib/components/dataset/AnalysisGallery.svelte';
	import DataInsightsPanel from '$lib/components/dataset/DataInsightsPanel.svelte';
	import ColumnReferenceSidebar from '$lib/components/dataset/ColumnReferenceSidebar.svelte';
	import QueryTemplates from '$lib/components/dataset/QueryTemplates.svelte';

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
	let showColumnSidebar = $state(true);

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
		// Fetch insights after a small delay to let profile load first
		setTimeout(() => fetchInsights(), 100);
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
			// Fetch insights after profiling
			await fetchInsights();
		} catch (err) {
			profileError = err instanceof Error ? err.message : 'Profiling failed';
		} finally {
			isProfiling = false;
		}
	}

	const breadcrumbs = $derived([
		{ label: 'Datasets', href: '/datasets' },
		{ label: dataset?.name || 'Loading...', href: `/datasets/${datasetId}`, isCurrent: true }
	]);
</script>

<svelte:head>
	<title>{dataset?.name || 'Dataset'} - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Breadcrumb -->
		<div class="mb-6">
			<Breadcrumb items={breadcrumbs} />
		</div>

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
					<span class="px-3 py-1 text-sm font-medium rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400 uppercase">
						{dataset.source_type}
					</span>
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

				<div class="flex gap-4">
					<!-- Chat History Sidebar -->
					<div class="w-56 flex-shrink-0 bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 h-[500px]">
						<DatasetChatHistory
							{datasetId}
							selectedId={selectedConversationId}
							onSelect={handleConversationSelect}
							onNew={handleNewConversation}
							bind:this={historyComponent}
						/>
					</div>

					<!-- Chat Interface -->
					<div class="flex-1">
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

					<!-- Column Reference Sidebar -->
					{#if columnSemantics.length > 0}
						<div class="w-52 flex-shrink-0 h-[500px]">
							<ColumnReferenceSidebar
								columns={columnSemantics}
								isOpen={showColumnSidebar}
								onToggle={toggleColumnSidebar}
							/>
						</div>
					{/if}
				</div>
			</div>

			<!-- Analysis History Section -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6 mt-6">
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4 flex items-center gap-2">
					<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
					</svg>
					Analysis History
				</h2>
				<AnalysisGallery {analyses} {datasetId} loading={analysesLoading} error={analysesError} />
			</div>
		{/if}
	</main>
</div>
