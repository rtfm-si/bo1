<script lang="ts">
	/**
	 * ColumnReferenceSidebar - Collapsible sidebar showing available columns
	 * Click-to-copy column names for easy reference during chat
	 * Supports inline-editable user descriptions
	 */
	import { onMount } from 'svelte';
	import type { ColumnSemantic } from '$lib/api/types';
	import { apiClient } from '$lib/api/client';

	interface Props {
		columns: ColumnSemantic[];
		datasetId: string;
		isOpen?: boolean;
		onToggle?: () => void;
	}

	let { columns, datasetId, isOpen = true, onToggle }: Props = $props();

	// Show more/less state for many columns
	let showAll = $state(false);
	const MAX_INITIAL = 10;

	// User-defined descriptions (loaded from API)
	let userDescriptions = $state<Record<string, string>>({});
	let editingColumn = $state<string | null>(null);
	let editValue = $state('');
	let saving = $state(false);

	// Sorted by confidence, highest first
	const sortedColumns = $derived(
		[...columns].sort((a, b) => b.confidence - a.confidence)
	);

	const displayColumns = $derived(
		showAll ? sortedColumns : sortedColumns.slice(0, MAX_INITIAL)
	);

	const hasMore = $derived(columns.length > MAX_INITIAL);

	// Clipboard state
	let copiedColumn = $state<string | null>(null);

	// Load user descriptions on mount
	onMount(async () => {
		try {
			userDescriptions = await apiClient.getColumnDescriptions(datasetId);
		} catch {
			// Silently fail - descriptions are optional
		}
	});

	async function copyColumnName(name: string, e: MouseEvent) {
		e.stopPropagation();
		try {
			await navigator.clipboard.writeText(name);
			copiedColumn = name;
			setTimeout(() => {
				copiedColumn = null;
			}, 1500);
		} catch {
			// Fallback for older browsers
			const textarea = document.createElement('textarea');
			textarea.value = name;
			document.body.appendChild(textarea);
			textarea.select();
			document.execCommand('copy');
			document.body.removeChild(textarea);
			copiedColumn = name;
			setTimeout(() => {
				copiedColumn = null;
			}, 1500);
		}
	}

	function startEdit(columnName: string, currentDescription: string) {
		editingColumn = columnName;
		editValue = currentDescription;
	}

	async function saveDescription() {
		if (!editingColumn || saving) return;

		const columnName = editingColumn;
		const description = editValue.trim();

		saving = true;
		try {
			await apiClient.updateColumnDescription(datasetId, columnName, description);
			userDescriptions = { ...userDescriptions, [columnName]: description };
		} catch {
			// Show error briefly? For now just fail silently
		} finally {
			saving = false;
			editingColumn = null;
			editValue = '';
		}
	}

	function cancelEdit() {
		editingColumn = null;
		editValue = '';
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			saveDescription();
		} else if (e.key === 'Escape') {
			cancelEdit();
		}
	}

	function getSemanticBadgeColor(type: string): string {
		switch (type.toLowerCase()) {
			case 'metric':
			case 'numeric':
			case 'currency':
				return 'bg-info-100 text-info-700 dark:bg-info-900/30 dark:text-info-300';
			case 'dimension':
			case 'category':
			case 'categorical':
				return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300';
			case 'date':
			case 'datetime':
			case 'timestamp':
				return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300';
			case 'identifier':
			case 'id':
				return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300';
			default:
				return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300';
		}
	}

	function truncateName(name: string, maxLen = 20): string {
		return name.length > maxLen ? name.slice(0, maxLen - 1) + '...' : name;
	}

	// Generate a placeholder description from column name
	function generatePlaceholder(col: ColumnSemantic): string {
		// Convert snake_case or camelCase to readable text
		const readable = col.column_name
			.replace(/_/g, ' ')
			.replace(/([a-z])([A-Z])/g, '$1 $2')
			.toLowerCase();

		return `Describe what "${readable}" represents...`;
	}

	// Get the display description for a column
	function getDescription(col: ColumnSemantic): string {
		// Priority: user description > AI business_meaning > empty
		return userDescriptions[col.column_name] || col.business_meaning || '';
	}
</script>

<!-- Toggle button - always visible -->
<button
	onclick={onToggle}
	class="absolute right-0 top-0 z-10 flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm hover:shadow transition-all"
	title={isOpen ? 'Hide columns' : 'Show columns'}
>
	<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
		<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
	</svg>
	<span class="hidden sm:inline">{isOpen ? 'Hide' : 'Columns'}</span>
	<span class="text-xs text-neutral-400">({columns.length})</span>
</button>

<!-- Slide-out drawer panel -->
{#if isOpen}
	<!-- Backdrop for mobile -->
	<button
		onclick={onToggle}
		class="fixed inset-0 bg-black/20 dark:bg-black/40 z-40 lg:hidden"
		aria-label="Close sidebar"
	></button>

	<!-- Drawer panel -->
	<div class="fixed right-0 top-0 h-full w-72 sm:w-80 z-50 lg:absolute lg:top-12 lg:h-auto lg:max-h-[600px] lg:w-64 lg:z-20 flex flex-col bg-white dark:bg-neutral-800 rounded-l-lg lg:rounded-lg border border-neutral-200 dark:border-neutral-700 shadow-xl overflow-hidden animate-slide-in-right">
		<!-- Header -->
		<div class="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-700/50">
			<span class="text-sm font-semibold text-neutral-700 dark:text-neutral-200 flex items-center gap-2">
				<svg class="w-4 h-4 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
				</svg>
				Column Reference
			</span>
			<button
				onclick={onToggle}
				class="p-1.5 rounded-md hover:bg-neutral-200 dark:hover:bg-neutral-600 text-neutral-500 dark:text-neutral-400 transition-colors"
				title="Close"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>

		<!-- Column List -->
		<div class="flex-1 overflow-y-auto p-3 space-y-1">
			{#if columns.length === 0}
				<p class="text-sm text-neutral-500 dark:text-neutral-400 text-center py-4">
					No column data available
				</p>
			{:else}
				{#each displayColumns as col (col.column_name)}
					<div class="w-full text-left p-2.5 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors group">
						<!-- Column name row with copy button -->
						<div class="flex items-center justify-between gap-2">
							<button
								onclick={(e) => copyColumnName(col.column_name, e)}
								class="text-sm font-medium text-neutral-800 dark:text-neutral-100 truncate hover:text-brand-600 dark:hover:text-brand-400"
								title={col.column_name.length > 20 ? `${col.column_name} - Click to copy` : 'Click to copy'}
							>
								{truncateName(col.column_name, 24)}
							</button>
							{#if copiedColumn === col.column_name}
								<svg class="w-4 h-4 text-success-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
								</svg>
							{:else}
								<svg class="w-4 h-4 text-neutral-400 opacity-0 group-hover:opacity-100 flex-shrink-0 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
								</svg>
							{/if}
						</div>

						<!-- Type badge - show semantic type, with technical as tooltip -->
						<div class="flex items-center gap-1.5 mt-1.5">
							{#if col.semantic_type && col.semantic_type.toLowerCase() !== 'unknown'}
								<span
									class="px-2 py-0.5 text-[10px] font-medium rounded-full {getSemanticBadgeColor(col.semantic_type)}"
									title={col.technical_type}
								>
									{col.semantic_type}
								</span>
							{:else}
								<!-- Unknown semantic type - show technical type as primary -->
								<span class="px-2 py-0.5 text-[10px] font-medium rounded-full bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400">
									{col.technical_type || 'unknown'}
								</span>
							{/if}
						</div>

						<!-- Description (editable) -->
						{#if editingColumn === col.column_name}
							<!-- Edit mode -->
							<div class="mt-2">
								<!-- svelte-ignore a11y_autofocus -->
								<input
									type="text"
									bind:value={editValue}
									onblur={saveDescription}
									onkeydown={handleKeydown}
									placeholder={generatePlaceholder(col)}
									disabled={saving}
									class="w-full text-xs px-2.5 py-1.5 rounded-md border border-brand-300 dark:border-brand-600 bg-white dark:bg-neutral-700 text-neutral-700 dark:text-neutral-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
									autofocus
								/>
								<p class="text-[10px] text-neutral-400 mt-1">Enter to save, Esc to cancel</p>
							</div>
						{:else}
							<!-- View mode - clickable to edit -->
							<button
								onclick={() => startEdit(col.column_name, getDescription(col))}
								class="mt-2 w-full text-left"
								title="Click to edit description"
							>
								{#if getDescription(col)}
									<p class="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2 hover:text-neutral-700 dark:hover:text-neutral-300">
										{getDescription(col)}
									</p>
								{:else}
									<p class="text-xs text-neutral-400 dark:text-neutral-500 italic hover:text-brand-500 dark:hover:text-brand-400">
										+ Add description
									</p>
								{/if}
							</button>
						{/if}
					</div>
				{/each}

				{#if hasMore}
					<button
						onclick={() => showAll = !showAll}
						class="w-full py-2 text-xs font-medium text-brand-600 dark:text-brand-400 hover:underline"
					>
						{showAll ? 'Show less' : `Show ${columns.length - MAX_INITIAL} more`}
					</button>
				{/if}
			{/if}
		</div>

		<!-- Footer tip -->
		<div class="px-4 py-2.5 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-700/30">
			<p class="text-xs text-neutral-500 dark:text-neutral-400 flex items-center gap-1.5">
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				Click column name to copy
			</p>
		</div>
	</div>
{/if}

<style>
	@keyframes slide-in-right {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	.animate-slide-in-right {
		animation: slide-in-right 0.2s ease-out;
	}
</style>
