<script lang="ts">
	/**
	 * SheetsImportModal - Modal for importing Google Sheets data
	 * Extracted from analyze page for compact layout
	 */

	import { Modal, Button } from '$lib/components/ui';

	interface Props {
		open: boolean;
		sheetsConnected: boolean;
		sheetsConnectionLoading: boolean;
		isImporting?: boolean;
		onImport: (url: string) => Promise<void>;
		onConnect: () => void;
		onclose: () => void;
	}

	let {
		open = $bindable(false),
		sheetsConnected,
		sheetsConnectionLoading,
		isImporting = false,
		onImport,
		onConnect,
		onclose
	}: Props = $props();

	let sheetsUrl = $state('');
	let error = $state<string | null>(null);

	function isValidSheetsUrl(url: string): boolean {
		return /docs\.google\.com\/spreadsheets\/d\/[a-zA-Z0-9_-]+/.test(url);
	}

	async function handleImport() {
		if (!sheetsUrl.trim()) {
			error = 'Please enter a Google Sheets URL';
			return;
		}
		if (!isValidSheetsUrl(sheetsUrl)) {
			error = 'Please enter a valid Google Sheets URL';
			return;
		}

		error = null;
		try {
			await onImport(sheetsUrl.trim());
			sheetsUrl = '';
			open = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Import failed';
		}
	}

	// Reset state when modal closes
	$effect(() => {
		if (!open) {
			error = null;
		}
	});
</script>

<Modal bind:open title="Import from Google Sheets" size="md" {onclose}>
	<div class="space-y-4">
		{#if !sheetsConnectionLoading}
			<div class="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-900/50 rounded-lg">
				<span class="text-sm text-neutral-600 dark:text-neutral-400">
					{sheetsConnected
						? 'Google account connected - you can import private sheets'
						: 'Connect Google to import private sheets'}
				</span>
				{#if sheetsConnected}
					<span class="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300">
						Connected
					</span>
				{:else}
					<Button variant="outline" size="sm" onclick={onConnect}>Connect Google</Button>
				{/if}
			</div>
		{/if}

		<div>
			<label for="sheets-url" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
				Google Sheets URL
			</label>
			<input
				id="sheets-url"
				type="url"
				bind:value={sheetsUrl}
				placeholder="https://docs.google.com/spreadsheets/d/..."
				class="w-full px-4 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:ring-2 focus:ring-brand-500 focus:border-transparent"
				disabled={isImporting}
			/>
			{#if error}
				<p class="mt-2 text-sm text-error-600 dark:text-error-400">{error}</p>
			{/if}
		</div>

		<p class="text-sm text-neutral-500 dark:text-neutral-400">
			Paste the URL of any Google Sheet you have access to. Public sheets work without connecting Google.
		</p>
	</div>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="outline" onclick={onclose} disabled={isImporting}>Cancel</Button>
			<Button variant="brand" onclick={handleImport} disabled={isImporting || !sheetsUrl.trim()}>
				{isImporting ? 'Importing...' : 'Import'}
			</Button>
		</div>
	{/snippet}
</Modal>
