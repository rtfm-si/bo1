<script lang="ts">
	/**
	 * MentorChat - Main chat interface for mentor conversations
	 */
	import { onMount, tick } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { MentorMessage as MessageType, ResolvedMentions, HoneypotFields as HoneypotFieldsType, ConversationSearchResult } from '$lib/api/types';
	import { Button } from '$lib/components/ui';
	import HoneypotFields from '$lib/components/ui/HoneypotFields.svelte';
	import MentorMessage from './MentorMessage.svelte';
	import PersonaPicker from './PersonaPicker.svelte';
	import ContextSourcesBadge from './ContextSourcesBadge.svelte';
	import MentionAutocomplete from './MentionAutocomplete.svelte';
	import { Send, Square, Loader2, Search, X, MessageSquarePlus, ArrowRight } from 'lucide-svelte';
	import { goto } from '$app/navigation';

	// Props for pre-filling from URL query params
	interface Props {
		initialMessage?: string;
		initialPersona?: string;
		initialBlindspotId?: string;
		loadConversationId?: string | null;
		onConversationChange?: (id: string | null) => void;
	}
	let { initialMessage, initialPersona, initialBlindspotId, loadConversationId = null, onConversationChange }: Props = $props();

	// Track active blindspot for current conversation
	let activeBlindspotId = $state<string | null>(initialBlindspotId || null);

	// Chat state
	let messages = $state<MessageType[]>([]);
	let inputValue = $state('');
	let isStreaming = $state(false);
	let isThinking = $state(false);
	let isGenerating = $state(false);
	let error = $state<string | null>(null);
	let conversationId = $state<string | null>(null);
	let streamingContent = $state('');
	let selectedPersona = $state<string | null>(null); // null = auto-select
	let activePersona = $state<string | null>(null); // Actual persona being used
	let contextSources = $state<string[]>([]);
	let messagesContainer: HTMLDivElement;
	let textareaElement: HTMLTextAreaElement;

	// Mention autocomplete state
	let showMentionAutocomplete = $state(false);
	let mentionQuery = $state('');
	let mentionPosition = $state({ top: 0, left: 0 });
	let mentionAutocomplete: { onKeyDown: (e: KeyboardEvent) => void } | undefined;

	// Abort controller for current stream
	let currentAbort: (() => void) | null = null;

	// Honeypot state
	let honeypotValues = $state<HoneypotFieldsType>({});

	// Search state
	let showSearch = $state(false);
	let searchQuery = $state('');
	let searchResults = $state<ConversationSearchResult[]>([]);
	let isSearching = $state(false);
	let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

	// Meeting extraction state
	let pendingMeetingExtraction = $state(false);
	let meetingStatement = $state<string | null>(null);

	const MEETING_EXTRACT_PROMPT = 'Can you summarise the key decision or problem we\'ve been discussing? Write it as a clear, specific problem statement I could bring to my board.';

	function scrollToBottom() {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	}

	// Detect @ trigger and extract query after @
	function checkForMentionTrigger(text: string, cursorPos: number) {
		// Look backwards from cursor for @ symbol
		const beforeCursor = text.substring(0, cursorPos);
		const atIndex = beforeCursor.lastIndexOf('@');

		if (atIndex === -1) {
			showMentionAutocomplete = false;
			return;
		}

		// Check if @ is at start or preceded by whitespace
		if (atIndex > 0 && !/\s/.test(beforeCursor[atIndex - 1])) {
			showMentionAutocomplete = false;
			return;
		}

		// Extract query after @
		const afterAt = beforeCursor.substring(atIndex + 1);

		// If there's a colon with UUID already, don't show autocomplete
		if (/^(meeting|action|dataset):[0-9a-f-]+$/i.test(afterAt)) {
			showMentionAutocomplete = false;
			return;
		}

		// Show autocomplete with query
		mentionQuery = afterAt;
		showMentionAutocomplete = true;

		// Position dropdown above the input (simplified positioning)
		mentionPosition = { top: -280, left: 0 };
	}

	function handleMentionSelect(type: 'meeting' | 'action' | 'dataset' | 'chat', id: string, title: string) {
		if (!textareaElement) return;

		const cursorPos = textareaElement.selectionStart;
		const beforeCursor = inputValue.substring(0, cursorPos);
		const afterCursor = inputValue.substring(cursorPos);

		// Find the @ symbol position
		const atIndex = beforeCursor.lastIndexOf('@');
		if (atIndex === -1) return;

		// Replace @query with @type:id
		const beforeAt = inputValue.substring(0, atIndex);
		const mention = `@${type}:${id} `;
		inputValue = beforeAt + mention + afterCursor;

		// Close autocomplete
		showMentionAutocomplete = false;
		mentionQuery = '';

		// Focus and set cursor after the inserted mention
		textareaElement.focus();
		const newCursorPos = atIndex + mention.length;
		setTimeout(() => {
			textareaElement.setSelectionRange(newCursorPos, newCursorPos);
		}, 0);
	}

	function handleMentionClose() {
		showMentionAutocomplete = false;
		mentionQuery = '';
	}

	// Search functions
	async function doSearch(query: string) {
		if (query.length < 3) {
			searchResults = [];
			return;
		}
		isSearching = true;
		try {
			const response = await apiClient.searchAdvisorConversations(query, { limit: 5 });
			searchResults = response.matches;
		} catch (e) {
			console.error('Search failed:', e);
			searchResults = [];
		} finally {
			isSearching = false;
		}
	}

	function handleSearchInput(e: Event) {
		const target = e.target as HTMLInputElement;
		searchQuery = target.value;

		// Debounce search
		if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => doSearch(searchQuery), 300);
	}

	function handleSearchResultClick(result: ConversationSearchResult) {
		// Close search and load conversation
		showSearch = false;
		searchQuery = '';
		searchResults = [];
		loadConversation(result.conversation_id);
	}

	function toggleSearch() {
		showSearch = !showSearch;
		if (!showSearch) {
			searchQuery = '';
			searchResults = [];
		}
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		const question = inputValue.trim();
		if (!question || isStreaming) return;

		// Clear input and error
		inputValue = '';
		error = null;

		// Add user message
		const userMessage: MessageType = {
			role: 'user',
			content: question,
			timestamp: new Date().toISOString()
		};
		messages = [...messages, userMessage];

		// Start streaming
		isStreaming = true;
		isThinking = true;
		isGenerating = false;
		streamingContent = '';

		try {
			const stream = apiClient.chatWithMentor(question, conversationId, selectedPersona, honeypotValues, activeBlindspotId);
			currentAbort = stream.abort;

			for await (const { event, data } of stream.connect()) {
				switch (event) {
					case 'thinking':
						try {
							const thinkingData = JSON.parse(data);
							if (thinkingData.status === 'calling_llm') {
								isThinking = false;
								isGenerating = true;
								// Track actual persona being used (whether auto-selected or manual)
								if (thinkingData.persona) {
									activePersona = thinkingData.persona;
								}
							}
						} catch {
							// Ignore parse errors
						}
						break;

					case 'context':
						try {
							const contextData = JSON.parse(data);
							contextSources = contextData.sources || [];
						} catch {
							// Ignore parse errors
						}
						break;

					case 'response':
						try {
							const responseData = JSON.parse(data);
							streamingContent = responseData.content || '';

							// Update or add assistant message
							const existingAssistantIndex = messages.findIndex(
								(m, i) => i > messages.length - 2 && m.role === 'assistant'
							);

							if (existingAssistantIndex >= 0) {
								messages = messages.map((m, i) =>
									i === existingAssistantIndex
										? { ...m, content: streamingContent }
										: m
								);
							} else {
								const assistantMessage: MessageType = {
									role: 'assistant',
									content: streamingContent,
									timestamp: new Date().toISOString(),
									persona: activePersona
								};
								messages = [...messages, assistantMessage];
							}
						} catch {
							// Ignore parse errors
						}
						scrollToBottom();
						break;

					case 'done':
						try {
							const doneData = JSON.parse(data);
							const newId = doneData.conversation_id || conversationId;
							if (newId !== conversationId) {
								conversationId = newId;
								// Notify parent of new conversation
								onConversationChange?.(newId);
							}
							if (doneData.persona) {
								activePersona = doneData.persona;
							}
							// Clear blindspot after first message to avoid tagging all messages
							activeBlindspotId = null;
							isGenerating = false;
							if (pendingMeetingExtraction) {
								pendingMeetingExtraction = false;
								meetingStatement = streamingContent.trim();
							}
						} catch {
							// Ignore parse errors
						}
						break;

					case 'error':
						try {
							const errorData = JSON.parse(data);
							error = errorData.error || 'An error occurred';
						} catch {
							error = data || 'An error occurred';
						}
						break;
				}
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to send message';
			// Remove incomplete message
			messages = messages.filter((m) => m.content !== '');
		} finally {
			isStreaming = false;
			isThinking = false;
			isGenerating = false;
			streamingContent = '';
			currentAbort = null;
			scrollToBottom();
		}
	}

	function handleKeyDown(e: KeyboardEvent) {
		// Delegate to autocomplete when visible
		if (showMentionAutocomplete && mentionAutocomplete) {
			// Let autocomplete handle navigation keys
			if (['ArrowUp', 'ArrowDown', 'Enter', 'Escape', 'Tab'].includes(e.key)) {
				mentionAutocomplete.onKeyDown(e);
				return;
			}
		}

		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit(e);
		}
	}

	function handleInput(e: Event) {
		const target = e.target as HTMLTextAreaElement;
		checkForMentionTrigger(target.value, target.selectionStart);
	}

	function handleCancel() {
		if (currentAbort) {
			currentAbort();
			currentAbort = null;
		}
		isStreaming = false;
		isThinking = false;
		isGenerating = false;
		streamingContent = '';
	}

	function clearConversation() {
		messages = [];
		conversationId = null;
		error = null;
		contextSources = [];
		activePersona = null;
		activeBlindspotId = null;
		// Notify parent to update sidebar selection
		onConversationChange?.(null);
		// Flash input to signal ready for new chat
		tick().then(() => {
			textareaElement?.classList.add('ring-2', 'ring-brand-400');
			setTimeout(() => textareaElement?.classList.remove('ring-2', 'ring-brand-400'), 800);
		});
	}

	function startMeetingExtraction() {
		if (isStreaming || messages.length === 0) return;
		pendingMeetingExtraction = true;
		inputValue = MEETING_EXTRACT_PROMPT;
		handleSubmit({ preventDefault: () => {} } as Event);
	}

	function confirmStartMeeting() {
		if (!meetingStatement?.trim()) return;
		const text = meetingStatement.trim().slice(0, 5000);
		meetingStatement = null;
		goto(`/meeting/new?q=${encodeURIComponent(text)}`);
	}

	function cancelMeetingExtraction() {
		meetingStatement = null;
	}

	function handlePersonaChange(persona: string | null) {
		// If changing persona mid-conversation, warn and start new conversation
		if (messages.length > 0 && persona !== selectedPersona) {
			// Clear conversation when switching persona
			clearConversation();
		}
		selectedPersona = persona;
	}

	// Load existing conversation
	async function loadConversation(id: string) {
		try {
			const conv = await apiClient.getMentorConversation(id);
			conversationId = conv.id;
			messages = conv.messages.map(m => ({
				role: m.role,
				content: m.content,
				timestamp: m.timestamp,
				persona: m.persona
			}));
			selectedPersona = conv.persona;
			activePersona = conv.persona;
			contextSources = conv.context_sources;
			scrollToBottom();
		} catch (e) {
			console.error('Failed to load conversation:', e);
			error = 'Failed to load conversation';
		}
	}

	// React to loadConversationId prop changes
	$effect(() => {
		if (loadConversationId && loadConversationId !== conversationId) {
			loadConversation(loadConversationId);
		} else if (loadConversationId === null && conversationId !== null) {
			// Clear for new conversation
			clearConversation();
			tick().then(() => textareaElement?.focus());
		}
	});

	// Initialize with props on mount
	onMount(() => {
		if (loadConversationId) {
			loadConversation(loadConversationId);
		} else if (initialMessage) {
			inputValue = initialMessage;
		}
		if (initialPersona) {
			selectedPersona = initialPersona;
		}
	});
</script>

<div
	class="flex flex-col h-full bg-white dark:bg-neutral-900 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700"
>
	<!-- Header -->
	<div class="flex flex-col gap-3 px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
		<div class="flex items-center justify-between">
			<div>
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">
					Ask Your Advisor
				</h3>
				{#if activePersona && messages.length > 0}
					<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
						Currently using: <span class="font-medium capitalize">{activePersona.replace('_', ' ')}</span>
					</p>
				{/if}
			</div>
			<div class="flex items-center gap-2">
				<button
					onclick={toggleSearch}
					class="p-1.5 rounded-md text-neutral-500 hover:text-neutral-700 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:text-neutral-200 dark:hover:bg-neutral-800"
					title="Search past conversations"
				>
					{#if showSearch}
						<X class="w-4 h-4" />
					{:else}
						<Search class="w-4 h-4" />
					{/if}
				</button>
				{#if messages.length > 0 && conversationId && !meetingStatement}
					<button
						onclick={startMeetingExtraction}
						disabled={isStreaming || pendingMeetingExtraction}
						class="p-1.5 rounded-md text-neutral-500 hover:text-brand-600 hover:bg-neutral-100
							   dark:text-neutral-400 dark:hover:text-brand-400 dark:hover:bg-neutral-800
							   disabled:opacity-50"
						title="Start a meeting from this conversation"
					>
						{#if pendingMeetingExtraction}
							<Loader2 class="w-4 h-4 animate-spin" />
						{:else}
							<MessageSquarePlus class="w-4 h-4" />
						{/if}
					</button>
				{/if}
				{#if messages.length > 0}
					<button
						onclick={clearConversation}
						class="text-sm text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
					>
						Clear
					</button>
				{/if}
			</div>
		</div>
		<!-- Search Panel -->
		{#if showSearch}
			<div class="relative">
				<div class="flex items-center gap-2">
					<div class="relative flex-1">
						<Search class="absolute left-3 top-1/2 -tranneutral-y-1/2 w-4 h-4 text-neutral-400" />
						<input
							type="text"
							value={searchQuery}
							oninput={handleSearchInput}
							placeholder="Search past conversations..."
							class="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
						/>
						{#if isSearching}
							<Loader2 class="absolute right-3 top-1/2 -tranneutral-y-1/2 w-4 h-4 text-neutral-400 animate-spin" />
						{/if}
					</div>
				</div>
				<!-- Search Results Dropdown -->
				{#if searchResults.length > 0}
					<div class="absolute z-10 mt-1 w-full bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg max-h-64 overflow-y-auto">
						{#each searchResults as result (result.conversation_id)}
							<button
								onclick={() => handleSearchResultClick(result)}
								class="w-full px-3 py-2 text-left hover:bg-neutral-100 dark:hover:bg-neutral-700 border-b border-neutral-100 dark:border-neutral-700 last:border-b-0"
							>
								<p class="text-sm text-neutral-900 dark:text-white line-clamp-2">{result.preview}</p>
								<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
									{Math.round(result.similarity * 100)}% match
								</p>
							</button>
						{/each}
					</div>
				{:else if searchQuery.length >= 3 && !isSearching}
					<div class="absolute z-10 mt-1 w-full bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg p-3 text-center">
						<p class="text-sm text-neutral-500 dark:text-neutral-400">No matching conversations</p>
					</div>
				{/if}
			</div>
		{/if}
		<PersonaPicker selected={selectedPersona} onChange={handlePersonaChange} />
		{#if contextSources.length > 0}
			<ContextSourcesBadge sources={contextSources} />
		{/if}
	</div>

	<!-- Messages -->
	<div bind:this={messagesContainer} class="flex-1 overflow-y-auto p-4 space-y-4">
		{#if messages.length === 0}
			<div class="flex items-start justify-center pt-12 text-neutral-500 dark:text-neutral-400">
				<div class="text-center max-w-md">
					<svg
						class="w-12 h-12 mx-auto mb-3 text-neutral-300 dark:text-neutral-600"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="1.5"
							d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
						/>
					</svg>
					<p class="text-sm font-medium mb-1">Get guidance from your AI advisor</p>
					<p class="text-xs text-neutral-400 dark:text-neutral-500">
						Ask about strategy, priorities, actions, or data insights. Your business context is
						automatically included.
					</p>
				</div>
			</div>
		{:else}
			{#each messages as message, i (i)}
				<MentorMessage
					{message}
					isStreaming={isStreaming && i === messages.length - 1 && message.role === 'assistant'}
				/>
			{/each}
			{#if isThinking}
				<div class="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
					<Loader2 class="w-4 h-4 animate-spin" />
					<span class="text-sm">Thinking...</span>
				</div>
			{:else if isGenerating && !streamingContent}
				<div class="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
					<Loader2 class="w-4 h-4 animate-spin" />
					<span class="text-sm">Working...</span>
				</div>
			{/if}
		{/if}
	</div>

	<!-- Meeting extraction editor -->
	{#if meetingStatement !== null}
		<div class="mx-4 mb-2 p-3 rounded-lg border border-brand-200 dark:border-brand-800 bg-brand-50 dark:bg-brand-950/30">
			<label for="meeting-statement" class="block text-xs font-medium text-neutral-600 dark:text-neutral-400 mb-1">
				Problem statement for your meeting
			</label>
			<textarea
				id="meeting-statement"
				bind:value={meetingStatement}
				rows="4"
				maxlength="5000"
				class="w-full px-3 py-2 text-sm rounded-md border border-neutral-300 dark:border-neutral-600
					   bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white
					   focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y"
			></textarea>
			<div class="flex items-center justify-between mt-2">
				<span class="text-xs text-neutral-400">{meetingStatement.length}/5000</span>
				<div class="flex gap-2">
					<button
						onclick={cancelMeetingExtraction}
						class="px-3 py-1.5 text-sm rounded-md text-neutral-600 dark:text-neutral-400
							   hover:bg-neutral-100 dark:hover:bg-neutral-800"
					>Cancel</button>
					<button
						onclick={confirmStartMeeting}
						disabled={!meetingStatement?.trim() || meetingStatement.trim().length < 20}
						class="px-3 py-1.5 text-sm rounded-md bg-brand-600 text-white
							   hover:bg-brand-700 disabled:opacity-50 flex items-center gap-1.5"
					>
						Start Meeting <ArrowRight class="w-3.5 h-3.5" />
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Error -->
	{#if error}
		<div
			class="px-4 py-2 bg-error-50 dark:bg-error-900/20 border-t border-error-200 dark:border-error-800"
		>
			<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
		</div>
	{/if}

	<!-- Input -->
	<form onsubmit={handleSubmit} class="p-4 border-t border-neutral-200 dark:border-neutral-700">
		<!-- Honeypot fields for bot detection -->
		<HoneypotFields bind:values={honeypotValues} />

		<div class="relative flex gap-2">
			<!-- Mention Autocomplete -->
			<MentionAutocomplete
				bind:this={mentionAutocomplete}
				visible={showMentionAutocomplete}
				query={mentionQuery}
				onSelect={handleMentionSelect}
				onClose={handleMentionClose}
				position={mentionPosition}
			/>

			<textarea
				bind:this={textareaElement}
				bind:value={inputValue}
				onkeydown={handleKeyDown}
				oninput={handleInput}
				placeholder="Ask your advisor anything... (type @ to mention)"
				disabled={isStreaming}
				rows="1"
				class="flex-1 px-4 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent disabled:opacity-50 resize-none min-h-[40px] max-h-[120px]"
			></textarea>
			{#if isStreaming}
				<Button variant="danger" size="md" onclick={handleCancel}>
					<Square class="w-4 h-4" />
				</Button>
			{:else}
				<Button variant="brand" size="md" type="submit" disabled={!inputValue.trim()}>
					<Send class="w-4 h-4" />
				</Button>
			{/if}
		</div>
	</form>
</div>
