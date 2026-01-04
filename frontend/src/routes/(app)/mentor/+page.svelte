<script lang="ts">
	/**
	 * Unified Mentor Page
	 *
	 * Consolidated interface for:
	 * - AI mentor chat with history
	 * - Data analysis Q&A
	 * - Dataset management (upload, import, list)
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import type { Dataset, MentorPersonaId } from '$lib/api/types';
	import MentorChat from '$lib/components/mentor/MentorChat.svelte';
	import MentorChatHistory from '$lib/components/mentor/MentorChatHistory.svelte';
	import AnalysisChat from '$lib/components/analysis/AnalysisChat.svelte';
	import Breadcrumb from '$lib/components/ui/Breadcrumb.svelte';
	import { Button } from '$lib/components/ui';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { toast } from '$lib/stores/toast';
	import { MessageSquare, BarChart3, Database } from 'lucide-svelte';

	// Tab state - read from URL or default to 'chat'
	type TabId = 'chat' | 'analysis' | 'data';
	const tabParam = $page.url.searchParams.get('tab');
	let activeTab = $state<TabId>(
		tabParam === 'analysis' ? 'analysis' : tabParam === 'data' ? 'data' : 'chat'
	);

	// Read query params for mentor pre-filling
	const initialMessage = $page.url.searchParams.get('message') || undefined;
	const initialPersona = $page.url.searchParams.get('persona') as MentorPersonaId | undefined;

	// Conversation state (Chat tab)
	let selectedConversationId = $state<string | null>(null);
	let historyComponent: { refresh: () => void } | undefined;

	// Datasets state (shared between Analysis and Data tabs)
	let datasets = $state<Dataset[]>([]);
	let datasetsLoading = $state(true);

	// Upload state (Data tab)
	let isUploading = $state(false);
	let uploadProgress = $state(0);
	let isDragging = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);
	let deletingDatasetId = $state<string | null>(null);

	// Google Sheets state
	let sheetsConnected = $state(false);
	let sheetsConnectionLoading = $state(true);
	let sheetsUrl = $state('');
	let isImportingSheets = $state(false);
	let sheetsError = $state<string | null>(null);
	let sheetsConnectionMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);

	const tabs = [
		{ id: 'chat' as TabId, label: 'Chat', icon: MessageSquare },
		{ id: 'analysis' as TabId, label: 'Analysis', icon: BarChart3 },
		{ id: 'data' as TabId, label: 'Data Sources', icon: Database }
	];

	function switchTab(tab: TabId) {
		activeTab = tab;
		// Update URL without navigation
		const url = new URL($page.url);
		if (tab === 'chat') {
			url.searchParams.delete('tab');
		} else {
			url.searchParams.set('tab', tab);
		}
		goto(url.toString(), { replaceState: true, noScroll: true });
	}

	// Chat handlers
	function handleSelectConversation(id: string) {
		selectedConversationId = id;
	}

	function handleNewConversation() {
		selectedConversationId = null;
	}

	function handleConversationChange(id: string | null) {
		if (id) {
			selectedConversationId = id;
			historyComponent?.refresh();
		}
	}

	// Dataset loading
	async function loadDatasets() {
		try {
			const response = await apiClient.getDatasets();
			datasets = response.datasets || [];
		} catch (err) {
			console.error('Failed to load datasets:', err);
			toast.error('Failed to load datasets');
		} finally {
			datasetsLoading = false;
		}
	}

	// Google Sheets
	async function checkSheetsConnection() {
		try {
			const status = await apiClient.getSheetsConnectionStatus();
			sheetsConnected = status.connected;
		} catch (err) {
			console.error('Failed to check sheets connection:', err);
		} finally {
			sheetsConnectionLoading = false;
		}
	}

	function handleUrlParams() {
		const params = $page.url.searchParams;
		const sheetsErrorParam = params.get('sheets_error');
		const sheetsSuccess = params.get('sheets_connected');

		if (sheetsSuccess === 'true') {
			sheetsConnectionMessage = { type: 'success', text: 'Google Sheets connected successfully!' };
			sheetsConnected = true;
			goto('/mentor?tab=data', { replaceState: true });
		} else if (sheetsErrorParam) {
			const errorMessages: Record<string, string> = {
				auth_failed: 'Authentication failed. Please try again.',
				access_denied: 'Access denied. Please contact support.',
				config_error: 'Service configuration error. Please try again later.',
				session_expired: 'Your session has expired. Please try again.',
				rate_limited: 'Too many attempts. Please try again later.'
			};
			sheetsConnectionMessage = {
				type: 'error',
				text: errorMessages[sheetsErrorParam] || 'Connection failed. Please try again.'
			};
			goto('/mentor?tab=data', { replaceState: true });
		}

		if (sheetsConnectionMessage) {
			setTimeout(() => {
				sheetsConnectionMessage = null;
			}, 5000);
		}
	}

	function connectGoogleSheets() {
		window.location.href = apiClient.getSheetsConnectUrl();
	}

	function isValidSheetsUrl(url: string): boolean {
		return /docs\.google\.com\/spreadsheets\/d\/[a-zA-Z0-9_-]+/.test(url);
	}

	async function handleSheetsImport() {
		if (!sheetsUrl.trim()) {
			sheetsError = 'Please enter a Google Sheets URL';
			return;
		}
		if (!isValidSheetsUrl(sheetsUrl)) {
			sheetsError = 'Please enter a valid Google Sheets URL';
			return;
		}

		isImportingSheets = true;
		sheetsError = null;

		try {
			await apiClient.importSheetsDataset(sheetsUrl.trim());
			sheetsUrl = '';
			await loadDatasets();
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Import failed');
		} finally {
			isImportingSheets = false;
		}
	}

	// File upload
	async function handleFileUpload(file: File) {
		if (!file.name.toLowerCase().endsWith('.csv')) {
			toast.error('Only CSV files are supported');
			return;
		}
		if (file.size > 10 * 1024 * 1024) {
			toast.error('File size must be under 10MB');
			return;
		}

		isUploading = true;
		uploadProgress = 0;

		try {
			const name = file.name.replace(/\.csv$/i, '');
			await apiClient.uploadDataset(file, name);
			uploadProgress = 100;
			await loadDatasets();
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Upload failed');
		} finally {
			isUploading = false;
			uploadProgress = 0;
		}
	}

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		isDragging = true;
	}

	function handleDragLeave(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
		const file = e.dataTransfer?.files[0];
		if (file) handleFileUpload(file);
	}

	function handleFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (file) handleFileUpload(file);
		input.value = '';
	}

	async function handleDelete(datasetId: string, event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();

		if (!confirm('Are you sure you want to delete this dataset? This cannot be undone.')) {
			return;
		}

		deletingDatasetId = datasetId;
		try {
			await apiClient.deleteDataset(datasetId);
			await loadDatasets();
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Failed to delete dataset');
		} finally {
			deletingDatasetId = null;
		}
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}

	function formatBytes(bytes: number | null): string {
		if (!bytes) return '—';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	onMount(() => {
		loadDatasets();
		checkSheetsConnection();
		handleUrlParams();
	});
</script>

<svelte:head>
	<title>Mentor | Board of One</title>
	<meta
		name="description"
		content="AI-powered business mentor with data analysis and dataset management"
	/>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
	<!-- Breadcrumb -->
	<div class="mb-6">
		<Breadcrumb
			items={[
				{ label: 'Dashboard', href: '/dashboard' },
				{ label: 'Mentor', href: '/mentor' }
			]}
		/>
	</div>

	<!-- Page Header -->
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">Mentor</h1>
		<p class="mt-1 text-neutral-600 dark:text-neutral-400">
			AI guidance, data analysis, and dataset management in one place.
		</p>
	</div>

	<!-- Tabs -->
	<div class="mb-6 border-b border-neutral-200 dark:border-neutral-700">
		<nav class="flex gap-4" aria-label="Tabs">
			{#each tabs as tab (tab.id)}
				<button
					type="button"
					onclick={() => switchTab(tab.id)}
					class="flex items-center gap-2 px-1 py-3 text-sm font-medium border-b-2 transition-colors {activeTab === tab.id
						? 'border-brand-500 text-brand-600 dark:text-brand-400'
						: 'border-transparent text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-300'}"
				>
					<tab.icon class="w-4 h-4" />
					{tab.label}
				</button>
			{/each}
		</nav>
	</div>

	<!-- Tab Content -->
	{#if activeTab === 'chat'}
		<!-- Chat Tab -->
		<div class="flex gap-6">
			<aside class="hidden lg:block w-64 flex-shrink-0">
				<div class="h-[600px] bg-white dark:bg-neutral-900 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					<MentorChatHistory
						bind:this={historyComponent}
						selectedId={selectedConversationId}
						onSelect={handleSelectConversation}
						onNew={handleNewConversation}
					/>
				</div>
			</aside>
			<div class="flex-1 min-w-0">
				<MentorChat
					{initialMessage}
					{initialPersona}
					loadConversationId={selectedConversationId}
					onConversationChange={handleConversationChange}
				/>
			</div>
		</div>

	{:else if activeTab === 'analysis'}
		<!-- Analysis Tab -->
		<div class="max-w-4xl">
			{#if datasetsLoading}
				<div class="h-[600px] bg-white dark:bg-neutral-900 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-4">
					<ShimmerSkeleton type="chart" />
				</div>
			{:else}
				<AnalysisChat {datasets} />
			{/if}
			<div class="mt-6 p-4 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
				<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Analysis tips</h3>
				<ul class="text-sm text-neutral-600 dark:text-neutral-400 space-y-1">
					<li>Select a dataset above to ask specific questions about your data</li>
					<li>Without a dataset, get general guidance on data analysis best practices</li>
					<li>Ask about trends, comparisons, correlations, or specific metrics</li>
				</ul>
			</div>
		</div>

	{:else if activeTab === 'data'}
		<!-- Data Sources Tab -->
		<div>
			<!-- Upload Zone -->
			<div
				class="mb-8 border-2 border-dashed rounded-lg p-8 text-center transition-colors {isDragging
					? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
					: 'border-neutral-300 dark:border-neutral-600 hover:border-brand-400 dark:hover:border-brand-500'}"
				ondragover={handleDragOver}
				ondragleave={handleDragLeave}
				ondrop={handleDrop}
				role="region"
				aria-label="File upload area"
			>
				{#if isUploading}
					<div class="space-y-4">
						<svg class="w-12 h-12 mx-auto text-brand-500 animate-spin" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						<p class="text-neutral-600 dark:text-neutral-400">Uploading...</p>
					</div>
				{:else}
					<svg class="w-12 h-12 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
					</svg>
					<p class="text-neutral-600 dark:text-neutral-400 mb-2">Drag and drop a CSV file here, or</p>
					<input bind:this={fileInput} type="file" accept=".csv" class="hidden" onchange={handleFileSelect} />
					<Button variant="outline" onclick={() => fileInput?.click()}>Browse Files</Button>
					<p class="text-sm text-neutral-500 dark:text-neutral-500 mt-2">CSV files only, max 10MB</p>
				{/if}
			</div>

			<!-- Google Sheets Connection Message -->
			{#if sheetsConnectionMessage}
				<div
					class="mb-4 p-4 rounded-lg {sheetsConnectionMessage.type === 'success'
						? 'bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800'
						: 'bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800'}"
				>
					<span class="{sheetsConnectionMessage.type === 'success' ? 'text-success-700 dark:text-success-300' : 'text-error-700 dark:text-error-300'}">
						{sheetsConnectionMessage.text}
					</span>
				</div>
			{/if}

			<!-- Google Sheets Import -->
			<div class="mb-8 bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
				<div class="flex items-center justify-between mb-4">
					<h3 class="font-semibold text-neutral-900 dark:text-white">Import from Google Sheets</h3>
					{#if !sheetsConnectionLoading}
						{#if sheetsConnected}
							<span class="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300">
								Connected
							</span>
						{:else}
							<Button variant="outline" size="sm" onclick={connectGoogleSheets}>Connect Google</Button>
						{/if}
					{/if}
				</div>
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
					{sheetsConnected
						? 'Import data from any Google Sheet you have access to.'
						: 'Import data from public Google Sheets. Connect Google to import private sheets.'}
				</p>
				<div class="flex gap-3">
					<input
						type="url"
						bind:value={sheetsUrl}
						placeholder="https://docs.google.com/spreadsheets/d/..."
						class="flex-1 px-4 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:ring-2 focus:ring-brand-500 focus:border-transparent"
						disabled={isImportingSheets}
					/>
					<Button variant="brand" onclick={handleSheetsImport} disabled={isImportingSheets || !sheetsUrl.trim()}>
						{isImportingSheets ? 'Importing...' : 'Import'}
					</Button>
				</div>
				{#if sheetsError}
					<p class="mt-2 text-sm text-error-600 dark:text-error-400">{sheetsError}</p>
				{/if}
			</div>

			<!-- Datasets List -->
			{#if datasetsLoading}
				<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
					{#each Array(6) as _, i (i)}
						<ShimmerSkeleton type="card" />
					{/each}
				</div>
			{:else if datasets.length === 0}
				<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-12 text-center">
					<svg class="w-16 h-16 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
					</svg>
					<h2 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-2">No datasets yet</h2>
					<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-md mx-auto">
						Upload your first CSV file to start exploring your data with AI-powered analysis.
					</p>
				</div>
			{:else}
				<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
					{#each datasets as dataset (dataset.id)}
						<a
							href="/datasets/{dataset.id}"
							class="block bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-200"
						>
							<div class="flex items-start justify-between gap-2 mb-4">
								<div class="flex items-center gap-2">
									<span class="w-10 h-10 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
										<svg class="w-5 h-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
										</svg>
									</span>
									<div>
										<h3 class="font-semibold text-neutral-900 dark:text-white truncate">{dataset.name}</h3>
										<span class="text-xs text-neutral-500 dark:text-neutral-500 uppercase">{dataset.source_type}</span>
									</div>
								</div>
							</div>

							{#if dataset.description}
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4 line-clamp-2">{dataset.description}</p>
							{/if}

							<div class="flex items-center gap-4 text-sm text-neutral-600 dark:text-neutral-400 mb-4">
								<span>{dataset.row_count?.toLocaleString() || '—'} rows</span>
								<span>{dataset.column_count || '—'} cols</span>
								<span>{formatBytes(dataset.file_size_bytes ?? null)}</span>
							</div>

							<div class="pt-4 border-t border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
								<span class="text-xs text-neutral-500 dark:text-neutral-500">Updated {formatDate(dataset.updated_at)}</span>
								<button
									onclick={(e) => handleDelete(dataset.id, e)}
									class="p-1 hover:bg-error-50 dark:hover:bg-error-900/20 rounded transition-colors group disabled:opacity-50"
									title="Delete dataset"
									disabled={deletingDatasetId !== null}
								>
									{#if deletingDatasetId === dataset.id}
										<svg class="w-4 h-4 text-neutral-400 animate-spin" fill="none" viewBox="0 0 24 24">
											<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
											<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
										</svg>
									{:else}
										<svg class="w-4 h-4 text-neutral-400 dark:text-neutral-500 group-hover:text-error-600 dark:group-hover:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
										</svg>
									{/if}
								</button>
							</div>
						</a>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>
