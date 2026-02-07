<script lang="ts">
	/**
	 * SheetsImportModal - Modal for importing data from Google Drive
	 * Supports: Google Sheets, Excel (XLSX/XLS), CSV, TSV, TXT
	 * Uses Google Picker for visual file selection (drive.file scope)
	 */

	import { Modal, Button } from '$lib/components/ui';
	import { openPicker, type PickedFile } from '$lib/services/googlePicker';

	interface Props {
		open: boolean;
		isImporting?: boolean;
		onImport: (url: string) => Promise<void>;
		onclose: () => void;
	}

	let {
		open = $bindable(false),
		isImporting = false,
		onImport,
		onclose
	}: Props = $props();

	let selectedFile = $state<PickedFile | null>(null);
	let error = $state<string | null>(null);
	let isLoadingPicker = $state(false);

	function getFileTypeLabel(mimeType: string): string {
		const labels: Record<string, string> = {
			'application/vnd.google-apps.spreadsheet': 'Google Sheets',
			'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel (XLSX)',
			'application/vnd.ms-excel': 'Excel (XLS)',
			'text/csv': 'CSV',
			'text/plain': 'Text file',
			'text/tab-separated-values': 'TSV'
		};
		return labels[mimeType] || 'Data file';
	}

	async function handleSelectSheet() {
		error = null;
		isLoadingPicker = true;

		try {
			const file = await openPicker();
			if (file) {
				selectedFile = file;
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to open Google Drive picker';
		} finally {
			isLoadingPicker = false;
		}
	}

	async function handleImport() {
		if (!selectedFile) {
			error = 'Please select a Google Sheet first';
			return;
		}

		error = null;
		try {
			await onImport(selectedFile.url);
			selectedFile = null;
			open = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Import failed';
		}
	}

	function handleClearSelection() {
		selectedFile = null;
		error = null;
	}

	// Reset state when modal closes
	$effect(() => {
		if (!open) {
			selectedFile = null;
			error = null;
			isLoadingPicker = false;
		}
	});
</script>

<Modal bind:open title="Import from Google Drive" size="md" {onclose}>
	<div class="space-y-4">
		{#if !selectedFile}
			<!-- No file selected - show picker button -->
			<div class="flex flex-col items-center justify-center p-8 border-2 border-dashed border-neutral-300 dark:border-neutral-600 rounded-lg">
				<svg class="w-12 h-12 text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
				</svg>
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4 text-center">
					Select a spreadsheet or data file from Google Drive
				</p>
				<Button
					variant="brand"
					onclick={handleSelectSheet}
					disabled={isLoadingPicker}
				>
					{#if isLoadingPicker}
						<svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Loading...
					{:else}
						Select from Google Drive
					{/if}
				</Button>
			</div>
		{:else}
			<!-- File selected - show selection -->
			<div class="flex items-center justify-between p-4 bg-neutral-50 dark:bg-neutral-900/50 rounded-lg">
				<div class="flex items-center gap-3 min-w-0">
					<div class="flex-shrink-0 w-10 h-10 bg-success-100 dark:bg-success-900/30 rounded-lg flex items-center justify-center">
						<svg class="w-6 h-6 text-success-600 dark:text-success-400" viewBox="0 0 24 24" fill="currentColor">
							<path d="M19.5 3h-15A1.5 1.5 0 003 4.5v15A1.5 1.5 0 004.5 21h15a1.5 1.5 0 001.5-1.5v-15A1.5 1.5 0 0019.5 3zm-9 15H6v-3h4.5v3zm0-4.5H6v-3h4.5v3zm0-4.5H6V6h4.5v3zm4.5 9h-3v-3h3v3zm0-4.5h-3v-3h3v3zm0-4.5h-3V6h3v3zm4.5 9h-3v-3h3v3zm0-4.5h-3v-3h3v3zm0-4.5h-3V6h3v3z"/>
						</svg>
					</div>
					<div class="min-w-0">
						<p class="text-sm font-medium text-neutral-900 dark:text-white truncate">
							{selectedFile.name}
						</p>
						<p class="text-xs text-neutral-500 dark:text-neutral-400">
							{getFileTypeLabel(selectedFile.mimeType)}
						</p>
					</div>
				</div>
				<Button variant="ghost" size="sm" onclick={handleClearSelection}>
					Change
				</Button>
			</div>
		{/if}

		{#if error}
			<div class="p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
				<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
			</div>
		{/if}

		<p class="text-sm text-neutral-500 dark:text-neutral-400">
			You'll be prompted to sign in with Google if not already connected.
		</p>
	</div>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="outline" onclick={onclose} disabled={isImporting}>Cancel</Button>
			<Button
				variant="brand"
				onclick={handleImport}
				disabled={isImporting || !selectedFile}
			>
				{isImporting ? 'Importing...' : 'Import'}
			</Button>
		</div>
	{/snippet}
</Modal>
