<script lang="ts">
	/**
	 * UploadDataModal - Modal with drag-drop CSV upload zone
	 * Extracted from analyze page for compact layout
	 */

	import { Modal, Button } from '$lib/components/ui';

	interface Props {
		open: boolean;
		isUploading?: boolean;
		onFileSelect: (file: File) => void;
		onclose: () => void;
	}

	let { open = $bindable(false), isUploading = false, onFileSelect, onclose }: Props = $props();

	let isDragging = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);

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
		if (file) onFileSelect(file);
	}

	function handleFileInputChange(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (file) onFileSelect(file);
		input.value = '';
	}
</script>

<Modal bind:open title="Upload CSV File" size="md" {onclose}>
	<div
		class="border-2 border-dashed rounded-lg p-8 text-center transition-colors {isDragging
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
			<input bind:this={fileInput} type="file" accept=".csv" class="hidden" onchange={handleFileInputChange} />
			<Button variant="outline" onclick={() => fileInput?.click()}>Browse Files</Button>
			<p class="text-sm text-neutral-500 dark:text-neutral-500 mt-2">CSV files only, max 10MB</p>
		{/if}
	</div>

	{#snippet footer()}
		<div class="flex justify-end">
			<Button variant="outline" onclick={onclose} disabled={isUploading}>Cancel</Button>
		</div>
	{/snippet}
</Modal>
