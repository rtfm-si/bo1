<script lang="ts">
	/**
	 * MeetingContextSelector - Select past meetings, actions, and datasets as context
	 *
	 * Allows users to attach relevant context to a new meeting for better recommendations.
	 * Uses the same search API as MentionAutocomplete.
	 */
	import { apiClient } from '$lib/api/client';
	import type { MentionSuggestion, SessionContextIds } from '$lib/api/types';
	import { Calendar, CheckSquare, Database, Loader2, Search, X } from 'lucide-svelte';

	type ContextType = 'meeting' | 'action' | 'dataset';

	interface SelectedItem {
		id: string;
		type: ContextType;
		title: string;
	}

	interface Props {
		onContextChange: (context: SessionContextIds) => void;
	}

	let { onContextChange }: Props = $props();

	let activeTab = $state<ContextType>('meeting');
	let searchQuery = $state('');
	let suggestions = $state<MentionSuggestion[]>([]);
	let selectedItems = $state<SelectedItem[]>([]);
	let isLoading = $state(false);
	let isExpanded = $state(false);
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;

	// Limits per plan constraints
	const LIMITS: Record<ContextType, number> = {
		meeting: 5,
		action: 10,
		dataset: 3
	};

	// Tab configuration
	const tabConfig: { id: ContextType; label: string; icon: typeof Calendar }[] = [
		{ id: 'meeting', label: 'Meetings', icon: Calendar },
		{ id: 'action', label: 'Actions', icon: CheckSquare },
		{ id: 'dataset', label: 'Datasets', icon: Database }
	];

	// Debounced search when query or tab changes
	$effect(() => {
		if (!isExpanded) return;

		// Track activeTab as dependency by reading it in the synchronous part
		const currentTab = activeTab;

		// Clear previous timeout
		if (searchTimeout) {
			clearTimeout(searchTimeout);
		}

		// Debounce search (300ms)
		searchTimeout = setTimeout(() => {
			searchItems(currentTab, searchQuery);
		}, 300);

		return () => {
			if (searchTimeout) clearTimeout(searchTimeout);
		};
	});

	// Notify parent when selection changes
	$effect(() => {
		const context: SessionContextIds = {
			meetings: selectedItems.filter((i) => i.type === 'meeting').map((i) => i.id),
			actions: selectedItems.filter((i) => i.type === 'action').map((i) => i.id),
			datasets: selectedItems.filter((i) => i.type === 'dataset').map((i) => i.id)
		};
		onContextChange(context);
	});

	async function searchItems(type: ContextType, query: string) {
		isLoading = true;
		try {
			const result = await apiClient.searchMentions(type, query, 10);
			// Filter out already selected items
			const selectedIds = new Set(selectedItems.map((i) => i.id));
			suggestions = result.suggestions.filter((s) => !selectedIds.has(s.id));
		} catch (err) {
			console.error('Failed to search items:', err);
			suggestions = [];
		} finally {
			isLoading = false;
		}
	}

	function handleTabChange(tab: ContextType) {
		activeTab = tab;
		searchQuery = '';
	}

	function selectItem(suggestion: MentionSuggestion) {
		const type = suggestion.type as ContextType;

		// Check limit
		const currentCount = selectedItems.filter((i) => i.type === type).length;
		if (currentCount >= LIMITS[type]) {
			return; // At limit
		}

		// Add to selection
		selectedItems = [
			...selectedItems,
			{
				id: suggestion.id,
				type,
				title: suggestion.title
			}
		];

		// Remove from suggestions
		suggestions = suggestions.filter((s) => s.id !== suggestion.id);
	}

	function removeItem(item: SelectedItem) {
		selectedItems = selectedItems.filter((i) => i.id !== item.id);
	}

	function getItemCount(type: ContextType): number {
		return selectedItems.filter((i) => i.type === type).length;
	}

	function isAtLimit(type: ContextType): boolean {
		return getItemCount(type) >= LIMITS[type];
	}
</script>

<div class="mt-6">
	<!-- Collapsed view - show toggle button and selected items count -->
	<button
		type="button"
		onclick={() => (isExpanded = !isExpanded)}
		class="w-full flex items-center justify-between px-4 py-3 bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800/50 transition-colors"
	>
		<div class="flex items-center gap-3">
			<div class="p-1.5 bg-info-100 dark:bg-info-900/30 rounded">
				<Search class="w-4 h-4 text-info-600 dark:text-info-400" />
			</div>
			<div class="text-left">
				<p class="text-sm font-medium text-neutral-900 dark:text-white">
					Add Context (Optional)
				</p>
				<p class="text-xs text-neutral-500 dark:text-neutral-400">
					{#if selectedItems.length === 0}
						Attach past meetings, actions, or datasets for better recommendations
					{:else}
						{selectedItems.length} item{selectedItems.length !== 1 ? 's' : ''} selected
					{/if}
				</p>
			</div>
		</div>
		<svg
			class="w-5 h-5 text-neutral-400 transition-transform {isExpanded ? 'rotate-180' : ''}"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</button>

	<!-- Selected items as chips (always visible if items selected) -->
	{#if selectedItems.length > 0}
		<div class="flex flex-wrap gap-2 mt-3">
			{#each selectedItems as item (item.id)}
				<span
					class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-info-100 dark:bg-info-900/30 text-info-800 dark:text-info-200 text-sm rounded-full"
				>
					{#if item.type === 'meeting'}
						<Calendar class="w-3 h-3" />
					{:else if item.type === 'action'}
						<CheckSquare class="w-3 h-3" />
					{:else}
						<Database class="w-3 h-3" />
					{/if}
					<span class="max-w-[150px] truncate">{item.title}</span>
					<button
						type="button"
						onclick={() => removeItem(item)}
						class="p-0.5 hover:bg-info-200 dark:hover:bg-info-800 rounded-full transition-colors"
						aria-label="Remove {item.title}"
					>
						<X class="w-3 h-3" />
					</button>
				</span>
			{/each}
		</div>
	{/if}

	<!-- Expanded search panel -->
	{#if isExpanded}
		<div
			class="mt-3 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden"
		>
			<!-- Tabs -->
			<div class="flex border-b border-neutral-200 dark:border-neutral-700">
				{#each tabConfig as tab}
					{@const count = getItemCount(tab.id)}
					{@const limit = LIMITS[tab.id]}
					{@const Icon = tab.icon}
					<button
						type="button"
						onclick={() => handleTabChange(tab.id)}
						class="flex-1 px-4 py-2.5 text-sm font-medium flex items-center justify-center gap-2 transition-colors
							{activeTab === tab.id
							? 'text-info-600 dark:text-info-400 border-b-2 border-info-500 -mb-px bg-info-50 dark:bg-info-900/20'
							: 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700/50'}"
					>
						<Icon class="w-4 h-4" />
						{tab.label}
						{#if count > 0}
							<span
								class="px-1.5 py-0.5 text-xs rounded-full {count >= limit
									? 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300'
									: 'bg-info-100 dark:bg-info-900/30 text-info-700 dark:text-info-300'}"
							>
								{count}/{limit}
							</span>
						{/if}
					</button>
				{/each}
			</div>

			<!-- Search input -->
			<div class="p-3 border-b border-neutral-200 dark:border-neutral-700">
				<div class="relative">
					<Search
						class="absolute left-3 top-1/2 -tranneutral-y-1/2 w-4 h-4 text-neutral-400"
					/>
					<input
						type="text"
						bind:value={searchQuery}
						placeholder="Search {activeTab}s..."
						class="w-full pl-9 pr-4 py-2 bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-600 rounded-lg text-sm text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-info-500 focus:border-transparent"
					/>
				</div>
			</div>

			<!-- Results list -->
			<div class="max-h-60 overflow-y-auto">
				{#if isLoading}
					<div class="flex items-center justify-center py-8 text-neutral-500 dark:text-neutral-400">
						<Loader2 class="w-5 h-5 animate-spin mr-2" />
						<span class="text-sm">Searching...</span>
					</div>
				{:else if suggestions.length === 0}
					<div class="py-8 text-center text-sm text-neutral-500 dark:text-neutral-400">
						{searchQuery
							? `No ${activeTab}s found for "${searchQuery}"`
							: `No recent ${activeTab}s available`}
					</div>
				{:else if isAtLimit(activeTab)}
					<div class="py-8 text-center">
						<p class="text-sm text-warning-600 dark:text-warning-400">
							Maximum {LIMITS[activeTab]} {activeTab}s reached
						</p>
						<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
							Remove an item to add more
						</p>
					</div>
				{:else}
					{#each suggestions as suggestion}
						<button
							type="button"
							onclick={() => selectItem(suggestion)}
							disabled={isAtLimit(activeTab)}
							class="w-full px-4 py-3 text-left hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
						>
							<div class="text-sm font-medium text-neutral-900 dark:text-white truncate">
								{suggestion.title}
							</div>
							{#if suggestion.preview}
								<div class="text-xs text-neutral-500 dark:text-neutral-400 truncate mt-0.5">
									{suggestion.preview}
								</div>
							{/if}
						</button>
					{/each}
				{/if}
			</div>

			<!-- Footer hint -->
			<div
				class="px-4 py-2 text-xs text-neutral-400 dark:text-neutral-500 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/50"
			>
				Selected context will be provided to experts during deliberation
			</div>
		</div>
	{/if}
</div>
