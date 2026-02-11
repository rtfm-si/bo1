<script lang="ts">
	/**
	 * DatasetChatHistory - Sidebar list of previous dataset Q&A conversations
	 * Based on MentorChatHistory pattern
	 */
	import { onMount, tick } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { ConversationResponse } from '$lib/api/types';
	import { MessageSquare, Trash2 } from 'lucide-svelte';

	import { formatDate } from '$lib/utils/time-formatting';
	interface Props {
		datasetId: string;
		selectedId?: string | null;
		onSelect: (id: string) => void;
		onNew: () => void;
	}
	let { datasetId, selectedId = null, onSelect, onNew }: Props = $props();

	let conversations = $state<ConversationResponse[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	async function loadConversations() {
		try {
			isLoading = true;
			error = null;
			const response = await apiClient.getConversations(datasetId);
			conversations = response.conversations;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load conversations';
		} finally {
			isLoading = false;
		}
	}

	async function handleDelete(e: Event, id: string) {
		e.stopPropagation();
		try {
			await apiClient.deleteConversation(datasetId, id);
			conversations = conversations.filter((c) => c.id !== id);
			if (selectedId === id) {
				onNew();
			}
		} catch (e) {
			console.error('Failed to delete conversation:', e);
		}
	}


	function getDisplayTitle(conv: ConversationResponse): string {
		// Generate title from conversation date
		const date = new Date(conv.created_at);
		return `${date.toLocaleDateString([], { month: 'short', day: 'numeric' })} Q&A`;
	}

	onMount(() => {
		loadConversations();
	});

	// Expose refresh method for parent
	export function refresh() {
		loadConversations();
	}
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div
		class="flex items-center justify-between px-3 py-2 border-b border-neutral-200 dark:border-neutral-700"
	>
		<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300">History</h3>
		<button
			onclick={onNew}
			class="px-2 py-1 text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300"
		>
			+ New
		</button>
	</div>

	<!-- List -->
	<div class="flex-1 overflow-y-auto">
		{#if isLoading}
			<div class="px-3 py-4 text-sm text-neutral-500 dark:text-neutral-400">Loading...</div>
		{:else if error}
			<div class="px-3 py-4 text-sm text-error-600 dark:text-error-400">{error}</div>
		{:else if conversations.length === 0}
			<div class="px-3 py-4 text-sm text-neutral-500 dark:text-neutral-400">
				No conversations yet
			</div>
		{:else}
			<ul class="divide-y divide-neutral-100 dark:divide-neutral-800">
				{#each conversations as conv}
					<li>
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<div
							onclick={() => onSelect(conv.id)}
							class="w-full px-3 py-2 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800/50 group transition-colors cursor-pointer {selectedId ===
							conv.id
								? 'bg-brand-50 dark:bg-brand-900/20'
								: ''}"
							role="button"
							tabindex="0"
							onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(conv.id)}
						>
							<div class="flex items-start gap-2">
								<MessageSquare
									class="w-4 h-4 mt-0.5 text-neutral-400 dark:text-neutral-500 flex-shrink-0"
								/>
								<div class="flex-1 min-w-0">
									<div class="flex items-center justify-between gap-1">
										<p class="text-sm font-medium text-neutral-900 dark:text-white truncate">
											{getDisplayTitle(conv)}
										</p>
										<div
											class="flex items-center opacity-0 group-hover:opacity-100 transition-opacity"
										>
											<button
												onclick={(e) => handleDelete(e, conv.id)}
												class="p-1 text-neutral-400 hover:text-error-500 dark:text-neutral-500 dark:hover:text-error-400"
												title="Delete conversation"
											>
												<Trash2 class="w-3.5 h-3.5" />
											</button>
										</div>
									</div>
									<div class="flex items-center gap-2 mt-0.5">
										<span class="text-xs text-neutral-500 dark:text-neutral-400">
											{formatDate(conv.updated_at)}
										</span>
										<span class="text-xs text-neutral-400 dark:text-neutral-500">
											{conv.message_count} msg{conv.message_count !== 1 ? 's' : ''}
										</span>
									</div>
								</div>
							</div>
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>
