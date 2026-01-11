<script lang="ts">
	/**
	 * Advisor - Analyze Page
	 * Data management and analysis tools with compact "Add Data" dropdown
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import type {
		Dataset,
		ObjectiveRequirementsSummary,
		DataRequirements
	} from '$lib/api/types';
	import { Button } from '$lib/components/ui';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { toast } from '$lib/stores/toast';
	import PiiConfirmationModal from '$lib/components/dataset/PiiConfirmationModal.svelte';
	import ObjectiveSelector from '$lib/components/upload/ObjectiveSelector.svelte';
	import DataRequirementsPanel from '$lib/components/upload/DataRequirementsPanel.svelte';
	import AddDataDropdown from '$lib/components/dataset/AddDataDropdown.svelte';
	import UploadDataModal from '$lib/components/dataset/UploadDataModal.svelte';
	import SheetsImportModal from '$lib/components/dataset/SheetsImportModal.svelte';

	// PII warning types (inline for now, will be generated from OpenAPI)
	type PiiType =
		| 'email'
		| 'ssn'
		| 'phone'
		| 'credit_card'
		| 'ip_address'
		| 'name'
		| 'address'
		| 'date_of_birth';

	interface PiiWarning {
		column_name: string;
		pii_type: PiiType;
		confidence: number;
		sample_values: string[];
		match_count: number;
	}

	// State machine for objective flow
	type ObjectiveFlowState = 'idle' | 'selecting_objective' | 'viewing_requirements' | 'uploading_with_objective';
	let objectiveFlowState = $state<ObjectiveFlowState>('idle');

	// Modal states
	let showUploadModal = $state(false);
	let showSheetsModal = $state(false);

	// Objectives state
	let objectives = $state<ObjectiveRequirementsSummary[]>([]);
	let objectivesLoading = $state(false);
	let selectedObjectiveIndex = $state<number | null>(null);
	let selectedObjectiveName = $state<string>('');

	// Data requirements state
	let requirements = $state<DataRequirements | null>(null);
	let requirementsLoading = $state(false);
	let requirementsError = $state<string | null>(null);

	// Datasets state
	let datasets = $state<Dataset[]>([]);
	let datasetsLoading = $state(true);

	// Multi-select state
	let selectedDatasetIds = $state<Set<string>>(new Set());
	let isMultiSelectMode = $state(false);

	// Upload state
	let isUploading = $state(false);
	let deletingDatasetId = $state<string | null>(null);

	// PII confirmation state
	let showPiiModal = $state(false);
	let pendingDataset = $state<{ id: string; name: string; pii_warnings: PiiWarning[] } | null>(null);

	// Google Sheets state
	let sheetsConnected = $state(false);
	let sheetsConnectionLoading = $state(true);
	let isImportingSheets = $state(false);
	let sheetsConnectionMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);

	// ==========================================================================
	// Objectives / Data Requirements Functions
	// ==========================================================================

	async function loadObjectives() {
		objectivesLoading = true;
		try {
			const response = await apiClient.getAllObjectivesDataRequirements();
			objectives = response.objectives || [];
		} catch (err) {
			console.error('Failed to load objectives:', err);
		} finally {
			objectivesLoading = false;
		}
	}

	function handleObjectiveSelect(index: number) {
		selectedObjectiveIndex = index;
		const objective = objectives.find((o) => o.index === index);
		selectedObjectiveName = objective?.name || '';
	}

	async function showDataRequirements() {
		if (selectedObjectiveIndex === null) {
			toast.error('Please select an objective first');
			return;
		}

		objectiveFlowState = 'viewing_requirements';
		requirementsLoading = true;
		requirementsError = null;

		try {
			const response = await apiClient.getObjectiveDataRequirements(selectedObjectiveIndex);
			requirements = response.requirements;
		} catch (err) {
			console.error('Failed to load data requirements:', err);
			requirementsError = err instanceof Error ? err.message : 'Failed to load requirements';
		} finally {
			requirementsLoading = false;
		}
	}

	function handleUploadFromRequirements() {
		objectiveFlowState = 'uploading_with_objective';
		showUploadModal = true;
	}

	function handleBackFromRequirements() {
		objectiveFlowState = 'selecting_objective';
		requirements = null;
		requirementsError = null;
	}

	function startWhatDataFlow() {
		objectiveFlowState = 'selecting_objective';
		if (objectives.length === 0) {
			loadObjectives();
		}
	}

	function cancelWhatDataFlow() {
		objectiveFlowState = 'idle';
		selectedObjectiveIndex = null;
		selectedObjectiveName = '';
		requirements = null;
		requirementsError = null;
	}

	// ==========================================================================
	// Datasets Functions
	// ==========================================================================

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
			goto('/advisor/analyze', { replaceState: true });
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
			goto('/advisor/analyze', { replaceState: true });
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

	async function handleSheetsImport(url: string) {
		isImportingSheets = true;
		try {
			await apiClient.importSheetsDataset(url);
			await loadDatasets();
			showSheetsModal = false;
		} catch (err) {
			throw err;
		} finally {
			isImportingSheets = false;
		}
	}

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

		try {
			const name = file.name.replace(/\.csv$/i, '');
			const response = await apiClient.uploadDataset(file, name);

			// Check for PII warnings
			const piiWarnings = (response as any).pii_warnings as PiiWarning[] | null;
			if (piiWarnings && piiWarnings.length > 0) {
				pendingDataset = {
					id: response.id,
					name: response.name,
					pii_warnings: piiWarnings
				};
				showPiiModal = true;
				showUploadModal = false;
			} else {
				toast.success('Dataset uploaded successfully');
				showUploadModal = false;

				if (objectiveFlowState === 'uploading_with_objective' && selectedObjectiveIndex !== null) {
					goto(`/datasets/${response.id}?objective_index=${selectedObjectiveIndex}`);
				} else {
					await loadDatasets();
				}
			}
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Upload failed');
		} finally {
			isUploading = false;
			if (objectiveFlowState === 'uploading_with_objective') {
				objectiveFlowState = 'idle';
				selectedObjectiveIndex = null;
				selectedObjectiveName = '';
			}
		}
	}

	async function handlePiiConfirm() {
		if (!pendingDataset) return;

		try {
			await apiClient.acknowledgePii(pendingDataset.id);
			toast.success('Dataset uploaded successfully');

			if (objectiveFlowState === 'uploading_with_objective' && selectedObjectiveIndex !== null) {
				goto(`/datasets/${pendingDataset.id}?objective_index=${selectedObjectiveIndex}`);
			} else {
				await loadDatasets();
			}
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Failed to confirm upload');
		} finally {
			showPiiModal = false;
			pendingDataset = null;
			if (objectiveFlowState === 'uploading_with_objective') {
				objectiveFlowState = 'idle';
				selectedObjectiveIndex = null;
				selectedObjectiveName = '';
			}
		}
	}

	async function handlePiiCancel() {
		if (!pendingDataset) return;

		try {
			await apiClient.deleteDataset(pendingDataset.id);
			toast.info('Upload cancelled');
		} catch (err) {
			console.error('Failed to cleanup cancelled upload:', err);
		} finally {
			showPiiModal = false;
			pendingDataset = null;
		}
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
		if (!bytes) return '-';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	// Multi-select handlers
	function toggleSelectMode() {
		isMultiSelectMode = !isMultiSelectMode;
		if (!isMultiSelectMode) {
			selectedDatasetIds = new Set();
		}
	}

	function toggleDatasetSelection(datasetId: string, event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		const newSet = new Set(selectedDatasetIds);
		if (newSet.has(datasetId)) {
			newSet.delete(datasetId);
		} else if (newSet.size < 5) {
			newSet.add(datasetId);
		}
		selectedDatasetIds = newSet;
	}

	function startMultiAnalysis() {
		if (selectedDatasetIds.size >= 2) {
			const ids = Array.from(selectedDatasetIds).join(',');
			goto(`/datasets/multi-analysis?ids=${ids}`);
		}
	}

	// Dropdown handlers
	function handleUploadClick() {
		showUploadModal = true;
	}

	function handleSheetsClick() {
		showSheetsModal = true;
	}

	onMount(() => {
		loadDatasets();
		checkSheetsConnection();
		handleUrlParams();
	});
</script>

<svelte:head>
	<title>Analyze | Advisor | Board of One</title>
	<meta name="description" content="Upload and analyze your business data with AI-powered insights" />
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
	<!-- Page Header with Add Data dropdown -->
	<div class="flex items-center justify-between mb-6">
		<div>
			<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">Analyze</h1>
			<p class="mt-1 text-neutral-600 dark:text-neutral-400">
				Upload data and get AI-powered analysis and insights.
			</p>
		</div>
		<AddDataDropdown
			onUploadClick={handleUploadClick}
			onSheetsClick={handleSheetsClick}
			onWhatDataClick={startWhatDataFlow}
		/>
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

	<!-- Data Requirements Panel (when viewing requirements) -->
	{#if objectiveFlowState === 'viewing_requirements'}
		<div class="mb-6">
			<DataRequirementsPanel
				{requirements}
				loading={requirementsLoading}
				error={requirementsError}
				objectiveName={selectedObjectiveName}
				onUploadClick={handleUploadFromRequirements}
				onBackClick={handleBackFromRequirements}
			/>
		</div>
	{:else if objectiveFlowState === 'selecting_objective'}
		<!-- Objective Selection (when in "What Data Do I Need?" flow) -->
		<div class="mb-6 bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
			<div class="flex items-center justify-between mb-4">
				<h3 class="font-semibold text-neutral-900 dark:text-white">What data do I need?</h3>
				<button
					type="button"
					onclick={cancelWhatDataFlow}
					class="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
					aria-label="Close"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
				Select an objective to see what data would help you analyze it:
			</p>

			<ObjectiveSelector
				objectives={objectives.map((o) => ({
					index: o.index,
					name: o.name,
					requirements_summary: o.requirements_summary
				}))}
				selectedIndex={selectedObjectiveIndex}
				onSelect={handleObjectiveSelect}
				loading={objectivesLoading}
			/>

			{#if objectives.length === 0 && !objectivesLoading}
				<div class="mt-4 p-4 bg-neutral-50 dark:bg-neutral-900/50 rounded-lg">
					<p class="text-sm text-neutral-600 dark:text-neutral-400">
						No objectives found. <a href="/context/overview" class="text-brand-600 hover:text-brand-700 dark:text-brand-400">Set up your business context</a> to see data recommendations.
					</p>
				</div>
			{/if}

			<div class="mt-4 flex gap-3">
				<Button
					variant="brand"
					disabled={selectedObjectiveIndex === null}
					onclick={showDataRequirements}
				>
					What data do I need for this?
				</Button>
				<Button variant="outline" onclick={cancelWhatDataFlow}>
					Cancel
				</Button>
			</div>
		</div>
	{/if}

	<!-- Multi-Select Toolbar -->
	{#if datasets.length >= 2 && objectiveFlowState === 'idle'}
		<div class="mb-4 flex items-center justify-between">
			<div class="flex items-center gap-4">
				<Button variant={isMultiSelectMode ? 'brand' : 'outline'} size="sm" onclick={toggleSelectMode}>
					{isMultiSelectMode ? 'Cancel Selection' : 'Compare Datasets'}
				</Button>
				{#if isMultiSelectMode && selectedDatasetIds.size > 0}
					<span class="text-sm text-neutral-600 dark:text-neutral-400">
						{selectedDatasetIds.size} selected (min 2, max 5)
					</span>
				{/if}
			</div>
			{#if isMultiSelectMode && selectedDatasetIds.size >= 2}
				<Button variant="brand" onclick={startMultiAnalysis}>
					Analyze {selectedDatasetIds.size} Datasets
				</Button>
			{/if}
		</div>
	{/if}

	<!-- Datasets List (primary content) -->
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
			<Button variant="brand" onclick={handleUploadClick}>
				<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
				</svg>
				Upload CSV
			</Button>
		</div>
	{:else}
		<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
			{#each datasets as dataset (dataset.id)}
				{@const isSelected = selectedDatasetIds.has(dataset.id)}
				<a
					href={isMultiSelectMode ? '#' : `/datasets/${dataset.id}`}
					onclick={isMultiSelectMode ? (e) => toggleDatasetSelection(dataset.id, e) : undefined}
					class="block bg-white dark:bg-neutral-800 rounded-lg shadow-sm border p-6 hover:shadow-md transition-all duration-200 {isSelected
						? 'border-brand-500 ring-2 ring-brand-500/20'
						: 'border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-700'}"
				>
					<div class="flex items-start justify-between gap-2 mb-4">
						<div class="flex items-center gap-2">
							{#if isMultiSelectMode}
								<span
									class="w-6 h-6 rounded border-2 flex items-center justify-center flex-shrink-0 {isSelected
										? 'bg-brand-500 border-brand-500'
										: 'border-neutral-300 dark:border-neutral-600'}"
								>
									{#if isSelected}
										<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
										</svg>
									{/if}
								</span>
							{/if}
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
						<span>{dataset.row_count?.toLocaleString() || '-'} rows</span>
						<span>{dataset.column_count || '-'} cols</span>
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

<!-- Upload Modal -->
<UploadDataModal
	bind:open={showUploadModal}
	{isUploading}
	onFileSelect={handleFileUpload}
	onclose={() => (showUploadModal = false)}
/>

<!-- Sheets Import Modal -->
<SheetsImportModal
	bind:open={showSheetsModal}
	{sheetsConnected}
	{sheetsConnectionLoading}
	isImporting={isImportingSheets}
	onImport={handleSheetsImport}
	onConnect={connectGoogleSheets}
	onclose={() => (showSheetsModal = false)}
/>

<!-- PII Confirmation Modal -->
{#if pendingDataset}
	<PiiConfirmationModal
		bind:open={showPiiModal}
		datasetName={pendingDataset.name}
		piiWarnings={pendingDataset.pii_warnings}
		onConfirm={handlePiiConfirm}
		onCancel={handlePiiCancel}
	/>
{/if}
