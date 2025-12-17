<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import type { Dataset } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { toast } from '$lib/stores/toast';

	// Use data fetch utility for datasets
	const datasetsData = useDataFetch(() => apiClient.getDatasets());

	// Derived state
	const datasets = $derived<Dataset[]>(datasetsData.data?.datasets || []);
	const isLoading = $derived(datasetsData.isLoading);
	const error = $derived(datasetsData.error);

	// Show toast when error changes
	$effect(() => {
		if (error) {
			toast.error(error);
		}
	});

	// Upload state
	let isUploading = $state(false);
	let uploadError = $state<string | null>(null);
	let uploadProgress = $state(0);
	let isDragging = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);

	// Delete operation state
	let deletingDatasetId = $state<string | null>(null);

	// Google Sheets connection state
	let sheetsConnected = $state(false);
	let sheetsConnectionLoading = $state(true);
	let sheetsConnectionMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);

	onMount(() => {
		datasetsData.fetch();
		checkSheetsConnection();
		handleUrlParams();
	});

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
		// Check URL params for OAuth callback messages
		const params = $page.url.searchParams;
		const sheetsError = params.get('sheets_error');
		const sheetsSuccess = params.get('sheets_connected');

		if (sheetsSuccess === 'true') {
			sheetsConnectionMessage = { type: 'success', text: 'Google Sheets connected successfully!' };
			sheetsConnected = true;
			// Clear params from URL
			goto('/datasets', { replaceState: true });
		} else if (sheetsError) {
			// Map sanitized safe error codes to user-friendly messages
			const errorMessages: Record<string, string> = {
				auth_failed: 'Authentication failed. Please try again.',
				access_denied: 'Access denied. Please contact support if you believe this is an error.',
				config_error: 'Service configuration error. Please try again later.',
				session_expired: 'Your session has expired. Please try again.',
				rate_limited: 'Too many attempts. Please try again later.',
			};
			sheetsConnectionMessage = {
				type: 'error',
				text: errorMessages[sheetsError] || 'Connection failed. Please try again.',
			};
			// Clear params from URL
			goto('/datasets', { replaceState: true });
		}

		// Auto-dismiss message after 5 seconds
		if (sheetsConnectionMessage) {
			setTimeout(() => {
				sheetsConnectionMessage = null;
			}, 5000);
		}
	}

	function connectGoogleSheets() {
		window.location.href = apiClient.getSheetsConnectUrl();
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

	async function handleFileUpload(file: File) {
		if (!file.name.toLowerCase().endsWith('.csv')) {
			uploadError = 'Only CSV files are supported';
			return;
		}

		if (file.size > 10 * 1024 * 1024) {
			uploadError = 'File size must be under 10MB';
			return;
		}

		isUploading = true;
		uploadError = null;
		uploadProgress = 0;

		try {
			// Extract name from filename (remove .csv extension)
			const name = file.name.replace(/\.csv$/i, '');
			await apiClient.uploadDataset(file, name);
			uploadProgress = 100;
			await datasetsData.fetch();
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
		if (file) {
			handleFileUpload(file);
		}
	}

	function handleFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (file) {
			handleFileUpload(file);
		}
		input.value = '';
	}

	// Google Sheets import state
	let sheetsUrl = $state('');
	let isImportingSheets = $state(false);
	let sheetsError = $state<string | null>(null);

	// Validate Google Sheets URL pattern
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
			await datasetsData.fetch();
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Import failed');
		} finally {
			isImportingSheets = false;
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
			await datasetsData.fetch();
		} catch (err) {
			console.error('Failed to delete dataset:', err);
			toast.error(err instanceof Error ? err.message : 'Failed to delete dataset');
		} finally {
			deletingDatasetId = null;
		}
	}
</script>

<svelte:head>
	<title>Datasets - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Header -->
		<div class="mb-8">
			<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">Datasets</h1>
			<p class="mt-1 text-neutral-600 dark:text-neutral-400">
				Upload and analyze your data with AI-powered insights
			</p>
		</div>

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
				<p class="text-neutral-600 dark:text-neutral-400 mb-2">
					Drag and drop a CSV file here, or
				</p>
				<input
					bind:this={fileInput}
					type="file"
					accept=".csv"
					class="hidden"
					onchange={handleFileSelect}
				/>
				<Button variant="outline" onclick={() => fileInput?.click()}>
					{#snippet children()}
						Browse Files
					{/snippet}
				</Button>
				<p class="text-sm text-neutral-500 dark:text-neutral-500 mt-2">
					CSV files only, max 10MB
				</p>
			{/if}
		</div>

		<!-- Connection Status Message -->
		{#if sheetsConnectionMessage}
			<div
				class="mb-4 p-4 rounded-lg {sheetsConnectionMessage.type === 'success'
					? 'bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800'
					: 'bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800'}"
			>
				<div class="flex items-center gap-2">
					{#if sheetsConnectionMessage.type === 'success'}
						<svg class="w-5 h-5 text-success-600 dark:text-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
						</svg>
					{:else}
						<svg class="w-5 h-5 text-error-600 dark:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
					{/if}
					<span class="{sheetsConnectionMessage.type === 'success' ? 'text-success-700 dark:text-success-300' : 'text-error-700 dark:text-error-300'}">
						{sheetsConnectionMessage.text}
					</span>
				</div>
			</div>
		{/if}

		<!-- Google Sheets Import Section -->
		<div class="mb-8 bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-2">
					<svg class="w-5 h-5 text-green-600 dark:text-green-400" viewBox="0 0 24 24" fill="currentColor">
						<path d="M14.721 4.314A6.75 6.75 0 0112 3a6.75 6.75 0 00-6.75 6.75c0 2.41 1.66 4.716 3.543 6.562a26.366 26.366 0 003.207 2.688 26.366 26.366 0 003.207-2.688c1.883-1.846 3.543-4.152 3.543-6.562A6.75 6.75 0 0012 3c-.944 0-1.846.194-2.66.54l5.381 5.381v-.001l.026-.026a2.25 2.25 0 00-3.182-3.182l-.026.026-5.381-5.381a6.713 6.713 0 012.842-.626c.944 0 1.846.194 2.66.54z" />
					</svg>
					<h3 class="font-semibold text-neutral-900 dark:text-white">Import from Google Sheets</h3>
				</div>
				<!-- Connection Status Badge -->
				{#if !sheetsConnectionLoading}
					{#if sheetsConnected}
						<span class="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300">
							<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
							</svg>
							Connected
						</span>
					{:else}
						<Button variant="outline" size="sm" onclick={connectGoogleSheets}>
							{#snippet children()}
								<svg class="w-4 h-4 mr-1" viewBox="0 0 24 24" fill="currentColor">
									<path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/>
								</svg>
								Connect Google
							{/snippet}
						</Button>
					{/if}
				{/if}
			</div>
			<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
				{#if sheetsConnected}
					Import data from any Google Sheet you have access to, including private sheets.
				{:else}
					Import data from public Google Sheets. <button onclick={connectGoogleSheets} class="text-brand-600 dark:text-brand-400 hover:underline">Connect Google</button> to import private sheets.
				{/if}
			</p>
			<div class="flex gap-3">
				<input
					type="url"
					bind:value={sheetsUrl}
					placeholder="https://docs.google.com/spreadsheets/d/..."
					class="flex-1 px-4 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:ring-2 focus:ring-brand-500 focus:border-transparent"
					disabled={isImportingSheets}
				/>
				<Button
					variant="brand"
					onclick={handleSheetsImport}
					disabled={isImportingSheets || !sheetsUrl.trim()}
				>
					{#snippet children()}
						{#if isImportingSheets}
							<svg class="w-4 h-4 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							Importing...
						{:else}
							Import
						{/if}
					{/snippet}
				</Button>
			</div>
			{#if sheetsError}
				<p class="mt-2 text-sm text-error-600 dark:text-error-400">{sheetsError}</p>
			{/if}
		</div>

		{#if uploadError}
			<div class="mb-6 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4">
				<p class="text-sm text-error-700 dark:text-error-300">{uploadError}</p>
			</div>
		{/if}

		{#if isLoading}
			<!-- Loading State -->
			<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
				{#each Array(6) as _, i (i)}
					<ShimmerSkeleton type="card" />
				{/each}
			</div>
		{:else if datasets.length === 0}
			<!-- Empty State -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-12 text-center">
				<svg class="w-16 h-16 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
				</svg>
				<h2 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-2">
					No datasets yet
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-md mx-auto">
					Upload your first CSV file to start exploring your data with AI-powered analysis.
				</p>
			</div>
		{:else}
			<!-- Datasets Grid -->
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
									<h3 class="font-semibold text-neutral-900 dark:text-white truncate">
										{dataset.name}
									</h3>
									<span class="text-xs text-neutral-500 dark:text-neutral-500 uppercase">
										{dataset.source_type}
									</span>
								</div>
							</div>
						</div>

						{#if dataset.description}
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4 line-clamp-2">
								{dataset.description}
							</p>
						{/if}

						<!-- Stats -->
						<div class="flex items-center gap-4 text-sm text-neutral-600 dark:text-neutral-400 mb-4">
							<span class="flex items-center gap-1">
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
								</svg>
								{dataset.row_count?.toLocaleString() || '—'} rows
							</span>
							<span class="flex items-center gap-1">
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
								</svg>
								{dataset.column_count || '—'} cols
							</span>
							<span class="flex items-center gap-1">
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
								</svg>
								{formatBytes(dataset.file_size_bytes)}
							</span>
						</div>

						<!-- Footer -->
						<div class="pt-4 border-t border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
							<span class="text-xs text-neutral-500 dark:text-neutral-500">
								Updated {formatDate(dataset.updated_at)}
							</span>
							<button
								onclick={(e) => handleDelete(dataset.id, e)}
								class="p-1 hover:bg-error-50 dark:hover:bg-error-900/20 rounded transition-colors group disabled:opacity-50 disabled:cursor-not-allowed"
								title="Delete dataset"
								aria-label="Delete dataset"
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
	</main>
</div>
