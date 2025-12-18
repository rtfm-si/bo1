<script lang="ts">
	/**
	 * MentorChat - Main chat interface for mentor conversations
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { MentorMessage as MessageType, MentorPersonaId, ResolvedMentions, HoneypotFields as HoneypotFieldsType } from '$lib/api/types';
	import { Button } from '$lib/components/ui';
	import HoneypotFields from '$lib/components/ui/HoneypotFields.svelte';
	import MentorMessage from './MentorMessage.svelte';
	import PersonaPicker from './PersonaPicker.svelte';
	import ContextSourcesBadge from './ContextSourcesBadge.svelte';
	import MentionAutocomplete from './MentionAutocomplete.svelte';
	import { Send, Square, Loader2 } from 'lucide-svelte';

	// Props for pre-filling from URL query params
	interface Props {
		initialMessage?: string;
		initialPersona?: MentorPersonaId;
	}
	let { initialMessage, initialPersona }: Props = $props();

	// Chat state
	let messages = $state<MessageType[]>([]);
	let inputValue = $state('');
	let isStreaming = $state(false);
	let isThinking = $state(false);
	let error = $state<string | null>(null);
	let conversationId = $state<string | null>(null);
	let streamingContent = $state('');
	let selectedPersona = $state<MentorPersonaId | null>(null); // null = auto-select
	let activePersona = $state<MentorPersonaId | null>(null); // Actual persona being used
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

	function handleMentionSelect(type: 'meeting' | 'action' | 'dataset', id: string, title: string) {
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
		streamingContent = '';

		try {
			const stream = apiClient.chatWithMentor(question, conversationId, selectedPersona, honeypotValues);
			currentAbort = stream.abort;

			for await (const { event, data } of stream.connect()) {
				switch (event) {
					case 'thinking':
						try {
							const thinkingData = JSON.parse(data);
							if (thinkingData.status === 'calling_llm') {
								isThinking = false;
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
							conversationId = doneData.conversation_id || conversationId;
							if (doneData.persona) {
								activePersona = doneData.persona;
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
		streamingContent = '';
	}

	function clearConversation() {
		messages = [];
		conversationId = null;
		error = null;
		contextSources = [];
		activePersona = null;
	}

	function handlePersonaChange(persona: MentorPersonaId | null) {
		// If changing persona mid-conversation, warn and start new conversation
		if (messages.length > 0 && persona !== selectedPersona) {
			// Clear conversation when switching persona
			clearConversation();
		}
		selectedPersona = persona;
	}

	// Initialize with props on mount
	onMount(() => {
		if (initialMessage) {
			inputValue = initialMessage;
		}
		if (initialPersona) {
			selectedPersona = initialPersona;
		}
	});
</script>

<div
	class="flex flex-col h-[600px] bg-white dark:bg-neutral-900 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700"
>
	<!-- Header -->
	<div class="flex flex-col gap-3 px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
		<div class="flex items-center justify-between">
			<div>
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">
					Ask Your Mentor
				</h3>
				{#if activePersona && messages.length > 0}
					<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
						Currently using: <span class="font-medium capitalize">{activePersona.replace('_', ' ')}</span>
					</p>
				{/if}
			</div>
			{#if messages.length > 0}
				<button
					onclick={clearConversation}
					class="text-sm text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
				>
					Clear
				</button>
			{/if}
		</div>
		<PersonaPicker selected={selectedPersona} onChange={handlePersonaChange} />
		{#if contextSources.length > 0}
			<ContextSourcesBadge sources={contextSources} />
		{/if}
	</div>

	<!-- Messages -->
	<div bind:this={messagesContainer} class="flex-1 overflow-y-auto p-4 space-y-4">
		{#if messages.length === 0}
			<div class="h-full flex items-center justify-center text-neutral-500 dark:text-neutral-400">
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
					<p class="text-sm font-medium mb-1">Get guidance from your AI mentor</p>
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
			{/if}
		{/if}
	</div>

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
				placeholder="Ask your mentor anything... (type @ to mention)"
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
