<script lang="ts">
	/**
	 * MentionAutocomplete - Dropdown for @mention suggestions in mentor chat
	 *
	 * Shows when user types @ in the input field.
	 * Categories: Meetings | Actions | Datasets
	 */
	import { apiClient } from '$lib/api/client';
	import type { MentionSuggestion } from '$lib/api/types';
	import { Calendar, CheckSquare, Database, Loader2 } from 'lucide-svelte';

	type MentionType = 'meeting' | 'action' | 'dataset';

	interface Props {
		visible: boolean;
		query: string;
		onSelect: (type: MentionType, id: string, title: string) => void;
		onClose: () => void;
		position?: { top: number; left: number };
	}

	let {
		visible,
		query,
		onSelect,
		onClose,
		position = { top: 0, left: 0 }
	}: Props = $props();

	let activeTab = $state<MentionType>('meeting');
	let suggestions = $state<MentionSuggestion[]>([]);
	let isLoading = $state(false);
	let selectedIndex = $state(0);
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;

	// Debounced search when query or tab changes
	$effect(() => {
		if (!visible) return;

		// Clear previous timeout
		if (searchTimeout) {
			clearTimeout(searchTimeout);
		}

		// Debounce search (300ms)
		searchTimeout = setTimeout(() => {
			searchMentions(activeTab, query);
		}, 300);

		return () => {
			if (searchTimeout) clearTimeout(searchTimeout);
		};
	});

	// Reset selected index when suggestions change
	$effect(() => {
		if (suggestions.length > 0) {
			selectedIndex = 0;
		}
	});

	async function searchMentions(type: MentionType, q: string) {
		isLoading = true;
		try {
			const result = await apiClient.searchMentions(type, q, 10);
			suggestions = result.suggestions;
		} catch (err) {
			console.error('Failed to search mentions:', err);
			suggestions = [];
		} finally {
			isLoading = false;
		}
	}

	function handleTabChange(tab: MentionType) {
		activeTab = tab;
		selectedIndex = 0;
	}

	function handleSelect(suggestion: MentionSuggestion) {
		onSelect(suggestion.type as MentionType, suggestion.id, suggestion.title);
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (!visible) return;

		switch (e.key) {
			case 'ArrowDown':
				e.preventDefault();
				selectedIndex = Math.min(selectedIndex + 1, suggestions.length - 1);
				break;
			case 'ArrowUp':
				e.preventDefault();
				selectedIndex = Math.max(selectedIndex - 1, 0);
				break;
			case 'Enter':
				e.preventDefault();
				if (suggestions[selectedIndex]) {
					handleSelect(suggestions[selectedIndex]);
				}
				break;
			case 'Escape':
				e.preventDefault();
				onClose();
				break;
			case 'Tab':
				// Switch tabs with Tab key
				e.preventDefault();
				const tabs: MentionType[] = ['meeting', 'action', 'dataset'];
				const currentIndex = tabs.indexOf(activeTab);
				const nextIndex = e.shiftKey
					? (currentIndex - 1 + tabs.length) % tabs.length
					: (currentIndex + 1) % tabs.length;
				handleTabChange(tabs[nextIndex]);
				break;
		}
	}

	// Expose keyboard handler for parent component
	export function onKeyDown(e: KeyboardEvent) {
		handleKeyDown(e);
	}

	const tabConfig: { id: MentionType; label: string; icon: typeof Calendar }[] = [
		{ id: 'meeting', label: 'Meetings', icon: Calendar },
		{ id: 'action', label: 'Actions', icon: CheckSquare },
		{ id: 'dataset', label: 'Datasets', icon: Database }
	];
</script>

{#if visible}
	<div
		class="absolute z-50 w-80 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden"
		style="top: {position.top}px; left: {position.left}px;"
		role="listbox"
		aria-label="Mention suggestions"
	>
		<!-- Tabs -->
		<div class="flex border-b border-neutral-200 dark:border-neutral-700">
			{#each tabConfig as tab}
				<button
					type="button"
					onclick={() => handleTabChange(tab.id)}
					class="flex-1 px-3 py-2 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors
						{activeTab === tab.id
						? 'text-brand-600 dark:text-brand-400 border-b-2 border-brand-500 -mb-px bg-brand-50 dark:bg-brand-900/20'
						: 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700/50'}"
				>
					<svelte:component this={tab.icon} class="w-3.5 h-3.5" />
					{tab.label}
				</button>
			{/each}
		</div>

		<!-- Suggestions List -->
		<div class="max-h-60 overflow-y-auto">
			{#if isLoading}
				<div class="flex items-center justify-center py-6 text-neutral-500 dark:text-neutral-400">
					<Loader2 class="w-4 h-4 animate-spin mr-2" />
					<span class="text-sm">Searching...</span>
				</div>
			{:else if suggestions.length === 0}
				<div class="py-6 text-center text-sm text-neutral-500 dark:text-neutral-400">
					{query ? `No ${activeTab}s found for "${query}"` : `No recent ${activeTab}s`}
				</div>
			{:else}
				{#each suggestions as suggestion, i}
					<button
						type="button"
						onclick={() => handleSelect(suggestion)}
						onmouseenter={() => (selectedIndex = i)}
						class="w-full px-3 py-2 text-left hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors
							{selectedIndex === i ? 'bg-brand-50 dark:bg-brand-900/20' : ''}"
						role="option"
						aria-selected={selectedIndex === i}
					>
						<div class="text-sm font-medium text-neutral-900 dark:text-white truncate">
							{suggestion.title}
						</div>
						{#if suggestion.preview}
							<div class="text-xs text-neutral-500 dark:text-neutral-400 truncate">
								{suggestion.preview}
							</div>
						{/if}
					</button>
				{/each}
			{/if}
		</div>

		<!-- Footer hint -->
		<div
			class="px-3 py-1.5 text-xs text-neutral-400 dark:text-neutral-500 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800"
		>
			<kbd class="px-1 py-0.5 bg-neutral-200 dark:bg-neutral-700 rounded">Tab</kbd> switch category
			<span class="mx-1">|</span>
			<kbd class="px-1 py-0.5 bg-neutral-200 dark:bg-neutral-700 rounded">Enter</kbd> select
			<span class="mx-1">|</span>
			<kbd class="px-1 py-0.5 bg-neutral-200 dark:bg-neutral-700 rounded">Esc</kbd> close
		</div>
	</div>
{/if}
