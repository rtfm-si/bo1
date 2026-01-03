<script lang="ts">
	/**
	 * ColumnReferenceSidebar - Collapsible sidebar showing available columns
	 * Click-to-copy column names for easy reference during chat
	 */
	import type { ColumnSemantic } from '$lib/api/types';

	interface Props {
		columns: ColumnSemantic[];
		isOpen?: boolean;
		onToggle?: () => void;
	}

	let { columns, isOpen = true, onToggle }: Props = $props();

	// Show more/less state for many columns
	let showAll = $state(false);
	const MAX_INITIAL = 10;

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

	async function copyColumnName(name: string) {
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

	function getSemanticBadgeColor(type: string): string {
		switch (type.toLowerCase()) {
			case 'metric':
			case 'numeric':
			case 'currency':
				return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
			case 'dimension':
			case 'category':
			case 'categorical':
				return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
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
</script>

{#if isOpen}
	<div class="flex flex-col h-full bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
		<!-- Header -->
		<div class="flex items-center justify-between px-3 py-2 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-700/50">
			<span class="text-sm font-medium text-neutral-700 dark:text-neutral-200 flex items-center gap-1.5">
				<svg class="w-4 h-4 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
				</svg>
				Columns ({columns.length})
			</span>
			{#if onToggle}
				<button
					onclick={onToggle}
					class="p-1 rounded hover:bg-neutral-200 dark:hover:bg-neutral-600 text-neutral-500 dark:text-neutral-400"
					title="Close sidebar"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			{/if}
		</div>

		<!-- Column List -->
		<div class="flex-1 overflow-y-auto p-2 space-y-1">
			{#if columns.length === 0}
				<p class="text-sm text-neutral-500 dark:text-neutral-400 text-center py-4">
					No column data available
				</p>
			{:else}
				{#each displayColumns as col (col.column_name)}
					<button
						onclick={() => copyColumnName(col.column_name)}
						class="w-full text-left p-2 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors group"
						title={col.column_name.length > 20 ? `${col.column_name} - Click to copy` : 'Click to copy'}
					>
						<div class="flex items-center justify-between gap-2">
							<span class="text-sm font-medium text-neutral-800 dark:text-neutral-100 truncate">
								{truncateName(col.column_name)}
							</span>
							{#if copiedColumn === col.column_name}
								<svg class="w-3.5 h-3.5 text-success-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
								</svg>
							{:else}
								<svg class="w-3.5 h-3.5 text-neutral-400 opacity-0 group-hover:opacity-100 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
								</svg>
							{/if}
						</div>
						<div class="flex items-center gap-1.5 mt-1">
							<span class="px-1.5 py-0.5 text-[10px] font-medium rounded {getSemanticBadgeColor(col.semantic_type)}">
								{col.semantic_type}
							</span>
						</div>
						{#if col.business_meaning}
							<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-2">
								{col.business_meaning}
							</p>
						{/if}
					</button>
				{/each}

				{#if hasMore}
					<button
						onclick={() => showAll = !showAll}
						class="w-full py-2 text-xs text-brand-600 dark:text-brand-400 hover:underline"
					>
						{showAll ? 'Show less' : `Show ${columns.length - MAX_INITIAL} more`}
					</button>
				{/if}
			{/if}
		</div>

		<!-- Footer tip -->
		<div class="px-3 py-2 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-700/30">
			<p class="text-[10px] text-neutral-500 dark:text-neutral-400">
				Click column to copy name
			</p>
		</div>
	</div>
{:else}
	<!-- Collapsed toggle button -->
	<button
		onclick={onToggle}
		class="flex items-center gap-1 px-2 py-1 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded transition-colors"
		title="Show column reference"
	>
		<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
		</svg>
		<span>Columns</span>
	</button>
{/if}
