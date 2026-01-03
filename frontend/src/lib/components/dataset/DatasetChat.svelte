<script lang="ts">
	/**
	 * DatasetChat - Chat interface for dataset Q&A with SSE streaming
	 * Supports loading existing conversations by ID
	 * Enhanced with column reference and query templates
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { ConversationMessage, ChartSpec, ColumnSemantic } from '$lib/api/types';
	import { Button } from '$lib/components/ui';
	import ChatMessage from './ChatMessage.svelte';

	interface Props {
		datasetId: string;
		selectedConversationId?: string | null;
		onConversationChange?: (conversationId: string | null) => void;
		columnSemantics?: ColumnSemantic[];
		onShowColumns?: () => void;
		onAnalysisCreated?: () => void;
	}

	let { datasetId, selectedConversationId = null, onConversationChange, columnSemantics = [], onShowColumns, onAnalysisCreated }: Props = $props();

	/**
	 * Public method to ask a question programmatically
	 * Used by parent components to trigger questions from suggested prompts
	 */
	export function askQuestion(question: string) {
		inputValue = question;
		// Focus the input to show the user what's happening
		const inputEl = document.querySelector<HTMLInputElement>('#dataset-chat-input');
		if (inputEl) {
			inputEl.focus();
		}
	}

	// Chat state
	let messages = $state<ConversationMessage[]>([]);
	let inputValue = $state('');
	let isStreaming = $state(false);
	let isLoadingConversation = $state(false);
	let error = $state<string | null>(null);
	let conversationId = $state<string | null>(null);
	let streamingContent = $state('');
	let messagesContainer: HTMLDivElement;

	// Abort controller for current stream
	let currentAbort: (() => void) | null = null;

	// Load conversation when selectedConversationId changes
	$effect(() => {
		if (selectedConversationId) {
			loadConversation(selectedConversationId);
		} else if (selectedConversationId === null && conversationId !== null) {
			// Reset to new conversation
			clearConversation();
		}
	});

	async function loadConversation(convId: string) {
		try {
			isLoadingConversation = true;
			error = null;
			const response = await apiClient.getConversation(datasetId, convId);
			conversationId = convId;
			messages = response.messages || [];
			scrollToBottom();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load conversation';
			console.error('Failed to load conversation:', e);
		} finally {
			isLoadingConversation = false;
		}
	}

	function scrollToBottom() {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
		const userMessage: ConversationMessage = {
			role: 'user',
			content: question,
			timestamp: new Date().toISOString()
		};
		messages = [...messages, userMessage];

		// Start streaming
		isStreaming = true;
		streamingContent = '';

		// Initialize streaming message
		const streamingMessage: ConversationMessage = {
			role: 'assistant',
			content: '',
			timestamp: new Date().toISOString()
		};

		try {
			const stream = apiClient.askDataset(datasetId, question, conversationId);
			currentAbort = stream.abort;

			let chartSpec: ChartSpec | null = null;
			let queryResult: Record<string, unknown> | null = null;

			for await (const { event, data } of stream.connect()) {
				switch (event) {
					case 'analysis':
						try {
							const analysisData = JSON.parse(data);
							streamingContent = analysisData.content || '';
							// Update the streaming message in the messages array
							messages = [
								...messages.slice(0, -1).filter((m) => m.role !== 'assistant' || m.content !== ''),
								{ ...streamingMessage, content: streamingContent }
							];
						} catch {
							// Fallback if not JSON
							streamingContent = data;
						}
						scrollToBottom();
						break;

					case 'query':
						try {
							const queryData = JSON.parse(data);
							// Store query spec for later use
							queryResult = queryData.spec || queryData;
						} catch {
							// Ignore parse errors
						}
						break;

					case 'query_result':
						try {
							const resultData = JSON.parse(data);
							queryResult = resultData;
						} catch {
							// Ignore parse errors
						}
						break;

					case 'chart':
						try {
							const chartData = JSON.parse(data);
							chartSpec = chartData.spec || chartData;
						} catch {
							// Ignore parse errors
						}
						break;

					case 'done':
						// Extract conversation_id and analysis_id from done event
						try {
							const doneData = JSON.parse(data);
							const newConvId = doneData.conversation_id;
							if (newConvId && newConvId !== conversationId) {
								conversationId = newConvId;
								// Notify parent of new conversation
								onConversationChange?.(newConvId);
							}
							// If chart was saved to analysis gallery, notify parent to refresh
							if (doneData.analysis_id) {
								onAnalysisCreated?.();
							}
						} catch {
							// Ignore parse errors
						}
						// Finalize message
						const finalMessage: ConversationMessage = {
							role: 'assistant',
							content: streamingContent,
							timestamp: new Date().toISOString(),
							chart_spec: chartSpec,
							query_result: queryResult
						};
						messages = [...messages.filter((m) => m.role === 'user'), finalMessage];
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

			// Finalize the message after stream ends
			if (streamingContent) {
				const finalMessage: ConversationMessage = {
					role: 'assistant',
					content: streamingContent,
					timestamp: new Date().toISOString(),
					chart_spec: chartSpec,
					query_result: queryResult
				};
				// Replace any incomplete streaming message with final
				messages = [...messages.filter((m) => m.content !== streamingContent || m.role === 'user'), finalMessage];
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to send message';
			// Remove incomplete streaming message
			messages = messages.filter((m) => m.role === 'user' || m.content !== '');
		} finally {
			isStreaming = false;
			streamingContent = '';
			currentAbort = null;
			scrollToBottom();
		}
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit(e);
		}
	}

	function handleNextStepClick(question: string) {
		// Set the input value and submit
		inputValue = question;
		// Trigger submit after a brief delay to allow state update
		setTimeout(() => {
			const form = document.querySelector('#dataset-chat-form') as HTMLFormElement;
			if (form) {
				form.requestSubmit();
			}
		}, 50);
	}

	function handleCancel() {
		if (currentAbort) {
			currentAbort();
			currentAbort = null;
		}
		isStreaming = false;
		streamingContent = '';
	}

	function clearConversation() {
		messages = [];
		conversationId = null;
		error = null;
	}

	// --- Column-based helpers for empty state ---

	// Get top columns by type for display
	const numericColumns = $derived(
		columnSemantics.filter(c =>
			['metric', 'numeric', 'currency', 'percentage'].includes(c.semantic_type.toLowerCase())
		).slice(0, 3)
	);

	const dimensionColumns = $derived(
		columnSemantics.filter(c =>
			['dimension', 'category', 'categorical'].includes(c.semantic_type.toLowerCase())
		).slice(0, 3)
	);

	const dateColumns = $derived(
		columnSemantics.filter(c =>
			['date', 'datetime', 'timestamp'].includes(c.semantic_type.toLowerCase())
		)
	);

	// Generate contextual example based on available columns
	const contextualExample = $derived.by(() => {
		const numCol = numericColumns[0]?.column_name;
		const dimCol = dimensionColumns[0]?.column_name;
		const dateCol = dateColumns[0]?.column_name;

		if (numCol && dimCol) {
			return `Top ${dimCol} by ${numCol}`;
		} else if (numCol && dateCol) {
			return `${numCol} trend over ${dateCol}`;
		} else if (numCol) {
			return `What's the average ${numCol}?`;
		} else if (dimCol) {
			return `Distribution of ${dimCol}`;
		}
		return 'What are the key trends in this data?';
	});

	// Parse error types for better guidance
	function parseErrorType(errorMsg: string): { type: string; guidance: string } {
		const msg = errorMsg.toLowerCase();

		if (msg.includes('no results') || msg.includes('empty') || msg.includes('no data')) {
			return {
				type: 'no_results',
				guidance: 'Try broadening your query - remove filters or use a wider date range.'
			};
		}
		if (msg.includes('column') && (msg.includes('not found') || msg.includes('invalid') || msg.includes('unknown'))) {
			return {
				type: 'invalid_column',
				guidance: 'Column not recognized. Check available columns for the correct name.'
			};
		}
		if (msg.includes('timeout') || msg.includes('too long')) {
			return {
				type: 'timeout',
				guidance: 'Query took too long. Try filtering to a smaller subset of data.'
			};
		}
		if (msg.includes('syntax') || msg.includes('parse')) {
			return {
				type: 'syntax',
				guidance: 'Query format issue. Try rephrasing your question more simply.'
			};
		}
		return {
			type: 'unknown',
			guidance: 'Something went wrong. Try rephrasing your question.'
		};
	}

	const errorInfo = $derived(error ? parseErrorType(error) : null);
</script>

<div class="flex flex-col h-[500px] bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700">
	<!-- Header -->
	<div class="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
		<h3 class="text-lg font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
			<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
			</svg>
			Ask a Question
		</h3>
		{#if messages.length > 0}
			<button
				onclick={clearConversation}
				class="text-sm text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
			>
				Clear
			</button>
		{/if}
	</div>

	<!-- Messages -->
	<div bind:this={messagesContainer} class="flex-1 overflow-y-auto p-4">
		{#if isLoadingConversation}
			<div class="h-full flex items-center justify-center text-neutral-500 dark:text-neutral-400">
				<div class="text-center">
					<svg class="w-8 h-8 mx-auto mb-2 animate-spin text-brand-500" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					<p class="text-sm">Loading conversation...</p>
				</div>
			</div>
		{:else if messages.length === 0}
			<div class="h-full flex items-center justify-center text-neutral-500 dark:text-neutral-400">
				<div class="text-center max-w-sm px-4">
					<svg class="w-12 h-12 mx-auto mb-3 text-neutral-300 dark:text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
					</svg>
					<p class="text-sm font-medium mb-2">Ask questions about your data</p>

					{#if columnSemantics.length > 0}
						<!-- Show available columns hint -->
						<div class="text-xs text-neutral-400 dark:text-neutral-500 mb-3">
							<span class="text-neutral-500 dark:text-neutral-400">Available:</span>
							{#each columnSemantics.slice(0, 5) as col, i}
								<span class="font-mono text-brand-600 dark:text-brand-400">{col.column_name}</span>{#if i < Math.min(columnSemantics.length, 5) - 1}, {/if}
							{/each}
							{#if columnSemantics.length > 5}
								<button
									onclick={onShowColumns}
									class="text-brand-500 hover:underline ml-1"
								>
									+{columnSemantics.length - 5} more
								</button>
							{/if}
						</div>

						<!-- Contextual example -->
						<p class="text-xs text-neutral-400 dark:text-neutral-500">
							Try: "<button
								onclick={() => { inputValue = contextualExample; }}
								class="text-brand-500 hover:underline"
							>{contextualExample}</button>"
						</p>
					{:else}
						<p class="text-xs mt-1 text-neutral-400 dark:text-neutral-500">
							e.g., "What are the top 5 products by revenue?"
						</p>
					{/if}
				</div>
			</div>
		{:else}
			{#each messages as message, i (i)}
				<ChatMessage
					{message}
					{datasetId}
					isStreaming={isStreaming && i === messages.length - 1 && message.role === 'assistant'}
					onNextStepClick={handleNextStepClick}
				/>
			{/each}
		{/if}
	</div>

	<!-- Error with enhanced guidance -->
	{#if error && errorInfo}
		<div class="px-4 py-2 bg-error-50 dark:bg-error-900/20 border-t border-error-200 dark:border-error-800">
			<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
			<div class="flex items-center justify-between mt-1">
				<p class="text-xs text-error-600 dark:text-error-400">{errorInfo.guidance}</p>
				{#if errorInfo.type === 'invalid_column' && onShowColumns}
					<button
						onclick={onShowColumns}
						class="text-xs text-brand-600 dark:text-brand-400 hover:underline flex items-center gap-1"
					>
						<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
						Show columns
					</button>
				{/if}
			</div>
		</div>
	{:else if error}
		<div class="px-4 py-2 bg-error-50 dark:bg-error-900/20 border-t border-error-200 dark:border-error-800">
			<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
		</div>
	{/if}

	<!-- Input -->
	<form id="dataset-chat-form" onsubmit={handleSubmit} class="p-4 border-t border-neutral-200 dark:border-neutral-700">
		<div class="flex gap-2">
			<input
				id="dataset-chat-input"
				type="text"
				bind:value={inputValue}
				onkeydown={handleKeyDown}
				placeholder="Ask a question about your data..."
				disabled={isStreaming}
				class="flex-1 px-4 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent disabled:opacity-50"
			/>
			{#if isStreaming}
				<Button variant="danger" size="md" onclick={handleCancel}>
					Cancel
				</Button>
			{:else}
				<Button variant="brand" size="md" type="submit" disabled={!inputValue.trim()}>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
					</svg>
				</Button>
			{/if}
		</div>
	</form>
</div>
