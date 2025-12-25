<script lang="ts">
	/**
	 * MentorChatHistory - Sidebar list of previous mentor conversations
	 * Supports inline editing of conversation labels.
	 */
	import { onMount, tick } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { MentorConversationResponse } from '$lib/api/types';
	import { MessageSquare, Trash2, Pencil, Check, X } from 'lucide-svelte';

	interface Props {
		selectedId?: string | null;
		onSelect: (id: string) => void;
		onNew: () => void;
	}
	let { selectedId = null, onSelect, onNew }: Props = $props();

	let conversations = $state<MentorConversationResponse[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	// Inline edit state
	let editingId = $state<string | null>(null);
	let editValue = $state('');
	let isSaving = $state(false);
	let editInputRef = $state<HTMLInputElement | null>(null);

	async function loadConversations() {
		try {
			isLoading = true;
			error = null;
			const response = await apiClient.getMentorConversations(20);
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
			await apiClient.deleteMentorConversation(id);
			conversations = conversations.filter(c => c.id !== id);
			if (selectedId === id) {
				onNew();
			}
		} catch (e) {
			console.error('Failed to delete conversation:', e);
		}
	}

	function startEditing(e: Event, conv: MentorConversationResponse) {
		e.stopPropagation();
		editingId = conv.id;
		editValue = getDisplayTitle(conv);
		// Focus the input after Svelte updates the DOM
		tick().then(() => {
			editInputRef?.focus();
			editInputRef?.select();
		});
	}

	function cancelEditing(e?: Event) {
		e?.stopPropagation();
		editingId = null;
		editValue = '';
	}

	async function saveLabel(e?: Event) {
		e?.stopPropagation();
		if (!editingId || isSaving) return;

		const trimmedLabel = editValue.trim();
		if (!trimmedLabel) {
			cancelEditing();
			return;
		}

		try {
			isSaving = true;
			const updated = await apiClient.updateMentorConversationLabel(editingId, trimmedLabel);
			// Update local state with new label
			conversations = conversations.map(c =>
				c.id === editingId ? { ...c, label: updated.label } : c
			);
			editingId = null;
			editValue = '';
		} catch (e) {
			console.error('Failed to update label:', e);
			// Keep editing mode open on error
		} finally {
			isSaving = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			saveLabel();
		} else if (e.key === 'Escape') {
			cancelEditing();
		}
	}

	function formatDate(isoString: string): string {
		const date = new Date(isoString);
		const now = new Date();
		const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

		if (diffDays === 0) {
			return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
		} else if (diffDays === 1) {
			return 'Yesterday';
		} else if (diffDays < 7) {
			return date.toLocaleDateString([], { weekday: 'short' });
		} else {
			return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
		}
	}

	function getDisplayTitle(conv: MentorConversationResponse): string {
		// Show label if present, otherwise show persona name
		if (conv.label) {
			return conv.label;
		}
		// Fallback to persona name
		const personaNames: Record<string, string> = {
			general: 'General Chat',
			action_coach: 'Action Coaching',
			data_analyst: 'Data Analysis'
		};
		return personaNames[conv.persona] || 'New Chat';
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
	<div class="flex items-center justify-between px-3 py-2 border-b border-neutral-200 dark:border-neutral-700">
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
							onclick={() => editingId !== conv.id && onSelect(conv.id)}
							class="w-full px-3 py-2 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800/50 group transition-colors cursor-pointer {selectedId === conv.id ? 'bg-brand-50 dark:bg-brand-900/20' : ''}"
							role="button"
							tabindex="0"
							onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && editingId !== conv.id && onSelect(conv.id)}
						>
							<div class="flex items-start gap-2">
								<MessageSquare class="w-4 h-4 mt-0.5 text-neutral-400 dark:text-neutral-500 flex-shrink-0" />
								<div class="flex-1 min-w-0">
									{#if editingId === conv.id}
										<!-- Inline edit mode -->
										<div class="flex items-center gap-1">
											<input
												bind:this={editInputRef}
												bind:value={editValue}
												onkeydown={handleKeydown}
												onblur={() => saveLabel()}
												disabled={isSaving}
												class="flex-1 px-1.5 py-0.5 text-sm font-medium bg-white dark:bg-neutral-800 border border-brand-400 dark:border-brand-500 rounded focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
												maxlength={100}
											/>
											<button
												onclick={(e) => saveLabel(e)}
												disabled={isSaving}
												class="p-0.5 text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 disabled:opacity-50"
												title="Save"
											>
												<Check class="w-3.5 h-3.5" />
											</button>
											<button
												onclick={(e) => cancelEditing(e)}
												disabled={isSaving}
												class="p-0.5 text-neutral-400 hover:text-neutral-600 dark:text-neutral-500 dark:hover:text-neutral-300 disabled:opacity-50"
												title="Cancel"
											>
												<X class="w-3.5 h-3.5" />
											</button>
										</div>
									{:else}
										<!-- Display mode -->
										<div class="flex items-center justify-between gap-1">
											<p class="text-sm font-medium text-neutral-900 dark:text-white truncate">
												{getDisplayTitle(conv)}
											</p>
											<div class="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
												<button
													onclick={(e) => startEditing(e, conv)}
													class="p-1 text-neutral-400 hover:text-brand-500 dark:text-neutral-500 dark:hover:text-brand-400"
													title="Rename conversation"
												>
													<Pencil class="w-3.5 h-3.5" />
												</button>
												<button
													onclick={(e) => handleDelete(e, conv.id)}
													class="p-1 text-neutral-400 hover:text-error-500 dark:text-neutral-500 dark:hover:text-error-400"
													title="Delete conversation"
												>
													<Trash2 class="w-3.5 h-3.5" />
												</button>
											</div>
										</div>
									{/if}
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
