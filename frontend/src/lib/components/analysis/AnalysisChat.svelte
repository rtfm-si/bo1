<script lang="ts">
	/**
	 * AnalysisChat - Data analysis chat interface
	 *
	 * Provides unified interface for:
	 * - Dataset Q&A (when dataset selected)
	 * - General data guidance (when no dataset)
	 */
	import { apiClient } from '$lib/api/client';
	import type { MentorMessage as MessageType, Dataset } from '$lib/api/types';
	import { Button } from '$lib/components/ui';
	import MentorMessage from '$lib/components/mentor/MentorMessage.svelte';
	import { Send, Square, Loader2, Database, X } from 'lucide-svelte';

	// Props
	let {
		datasets = []
	}: {
		datasets?: Dataset[];
	} = $props();

	// Chat state
	let messages = $state<MessageType[]>([]);
	let inputValue = $state('');
	let isStreaming = $state(false);
	let isThinking = $state(false);
	let error = $state<string | null>(null);
	let conversationId = $state<string | null>(null);
	let streamingContent = $state('');
	let selectedDatasetId = $state<string | null>(null);
	let contextSources = $state<string[]>([]);
	let messagesContainer: HTMLDivElement;

	// Abort controller for current stream
	let currentAbort: (() => void) | null = null;

	// Computed
	const selectedDataset = $derived(
		datasets.find((d) => d.id === selectedDatasetId)
	);

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
			// Route based on whether dataset is selected
			const stream = selectedDatasetId
				? apiClient.askDataset(selectedDatasetId, question, conversationId)
				: apiClient.askAnalysis(question, conversationId);

			currentAbort = stream.abort;

			for await (const { event, data } of stream.connect()) {
				switch (event) {
					case 'thinking':
						try {
							const thinkingData = JSON.parse(data);
							if (thinkingData.status === 'calling_llm' || thinkingData.status === 'analyzing') {
								isThinking = false;
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
					case 'analysis':
						try {
							const responseData = JSON.parse(data);
							streamingContent = responseData.content || responseData.text || '';

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
									persona: 'data_analyst'
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
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit(e);
		}
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
	}

	function handleDatasetChange(datasetId: string | null) {
		// Clear conversation when switching datasets to avoid context confusion
		if (datasetId !== selectedDatasetId && messages.length > 0) {
			clearConversation();
		}
		selectedDatasetId = datasetId;
	}
</script>

<div
	class="flex flex-col h-[600px] bg-white dark:bg-neutral-900 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700"
>
	<!-- Header -->
	<div class="flex flex-col gap-3 px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
		<div class="flex items-center justify-between">
			<div>
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">
					Data Analysis
				</h3>
				{#if selectedDataset}
					<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
						Analyzing: <span class="font-medium">{selectedDataset.name}</span>
					</p>
				{:else}
					<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
						General data guidance
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

		<!-- Dataset Selector -->
		<div class="flex items-center gap-2">
			<Database class="w-4 h-4 text-neutral-400" />
			<select
				class="flex-1 px-3 py-1.5 text-sm rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
				value={selectedDatasetId || ''}
				onchange={(e) => handleDatasetChange(e.currentTarget.value || null)}
			>
				<option value="">No dataset (general guidance)</option>
				{#each datasets as dataset (dataset.id)}
					<option value={dataset.id}>{dataset.name}</option>
				{/each}
			</select>
			{#if selectedDatasetId}
				<button
					type="button"
					onclick={() => handleDatasetChange(null)}
					class="p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
					title="Clear dataset selection"
				>
					<X class="w-4 h-4" />
				</button>
			{/if}
		</div>

		{#if contextSources.length > 0}
			<div class="flex items-center gap-1 flex-wrap">
				<span class="text-xs text-neutral-400">Context:</span>
				{#each contextSources as source (source)}
					<span class="px-1.5 py-0.5 text-xs bg-neutral-100 dark:bg-neutral-800 rounded">
						{source}
					</span>
				{/each}
			</div>
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
							d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
						/>
					</svg>
					{#if selectedDataset}
						<p class="text-sm font-medium mb-1">Ask questions about {selectedDataset.name}</p>
						<p class="text-xs text-neutral-400 dark:text-neutral-500">
							Get insights, run queries, and explore your data with natural language.
						</p>
					{:else}
						<p class="text-sm font-medium mb-1">Get data analysis guidance</p>
						<p class="text-xs text-neutral-400 dark:text-neutral-500">
							Ask about data interpretation, metrics, or select a dataset above for specific analysis.
						</p>
					{/if}
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
					<span class="text-sm">
						{selectedDataset ? 'Analyzing data...' : 'Thinking...'}
					</span>
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
		<div class="flex gap-2">
			<textarea
				bind:value={inputValue}
				onkeydown={handleKeyDown}
				placeholder={selectedDataset
					? `Ask about ${selectedDataset.name}...`
					: 'Ask about data analysis...'}
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
