<script lang="ts">
	/**
	 * AddDataDropdown - Compact dropdown menu for adding data sources
	 * Options: Upload CSV, Import Google Sheet, What data do I need?
	 */

	import { clickOutside } from '$lib/utils/clickOutside';
	import { Button } from '$lib/components/ui';

	interface Props {
		onUploadClick: () => void;
		onSheetsClick: () => void;
		onWhatDataClick: () => void;
	}

	let { onUploadClick, onSheetsClick, onWhatDataClick }: Props = $props();

	let isOpen = $state(false);

	function toggle() {
		isOpen = !isOpen;
	}

	function handleAction(action: () => void) {
		action();
		isOpen = false;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			isOpen = false;
		}
	}
</script>

<div class="relative" use:clickOutside={() => (isOpen = false)}>
	<Button variant="brand" onclick={toggle}>
		<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
		</svg>
		Add Data
		<svg
			class="w-4 h-4 ml-2 transition-transform {isOpen ? 'rotate-180' : ''}"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</Button>

	{#if isOpen}
		<div
			class="absolute right-0 z-dropdown mt-2 w-56 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg py-1"
			role="menu"
			aria-orientation="vertical"
			tabindex="-1"
			onkeydown={handleKeydown}
		>
			<button
				type="button"
				class="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
				role="menuitem"
				onclick={() => handleAction(onUploadClick)}
			>
				<svg class="w-5 h-5 text-neutral-500 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
				</svg>
				<div>
					<div class="font-medium">Upload CSV</div>
					<div class="text-xs text-neutral-500 dark:text-neutral-400">From your computer</div>
				</div>
			</button>

			<button
				type="button"
				class="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
				role="menuitem"
				onclick={() => handleAction(onSheetsClick)}
			>
				<svg class="w-5 h-5 text-neutral-500 dark:text-neutral-400" viewBox="0 0 24 24" fill="currentColor">
					<path d="M19 11V9h-6V3h-2v6H5v2h6v10h2V11h6z"/>
				</svg>
				<div>
					<div class="font-medium">Import Google Sheet</div>
					<div class="text-xs text-neutral-500 dark:text-neutral-400">Connect to spreadsheet</div>
				</div>
			</button>

			<div class="my-1 border-t border-neutral-200 dark:border-neutral-700"></div>

			<button
				type="button"
				class="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
				role="menuitem"
				onclick={() => handleAction(onWhatDataClick)}
			>
				<svg class="w-5 h-5 text-neutral-500 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<div>
					<div class="font-medium">What data do I need?</div>
					<div class="text-xs text-neutral-500 dark:text-neutral-400">Get recommendations</div>
				</div>
			</button>
		</div>
	{/if}
</div>
