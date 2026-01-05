<script lang="ts">
	/**
	 * AnalysisChat - Data analysis chat interface
	 *
	 * Provides unified interface for:
	 * - Dataset Q&A (when dataset selected)
	 * - General data guidance (when no dataset)
	 */
	import { apiClient, ApiClientError } from '$lib/api/client';
	import type { MentorMessage as MessageType, Dataset, DatasetDetailResponse, DatasetInsightsResponse } from '$lib/api/types';
	import { Button } from '$lib/components/ui';
	import MentorMessage from '$lib/components/mentor/MentorMessage.svelte';
	import InsightsPreview from './InsightsPreview.svelte';
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
	let selectedDatasetDetail = $state<DatasetDetailResponse | null>(null);
	let isLoadingDetail = $state(false);
	let contextSources = $state<string[]>([]);
	let datasetInsights = $state<DatasetInsightsResponse | null>(null);
	let insightsLoading = $state(false);
	let insightsError = $state<string | null>(null);
	let messagesContainer: HTMLDivElement;

	// Abort controller for current stream
	let currentAbort: (() => void) | null = null;

	// Computed
	const selectedDataset = $derived(
		datasets.find((d) => d.id === selectedDatasetId)
	);

	const placeholderText = $derived.by(() => {
		if (!selectedDataset) return 'Ask about data analysis...';
		const profiles = selectedDatasetDetail?.profiles;
		if (profiles && profiles.length > 0) {
			const columnNames = profiles.slice(0, 3).map((p) => p.column_name);
			return `Ask about ${columnNames.join(', ')}...`;
		}
		return `Ask about ${selectedDataset.name}...`;
	});

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

	function handleSuggestedQuestion(question: string) {
		// Set input and trigger submit
		inputValue = question;
		// Use requestAnimationFrame to ensure state is updated before submit
		requestAnimationFrame(() => {
			const form = document.querySelector('form');
			if (form) {
				form.dispatchEvent(new Event('submit', { cancelable: true }));
			}
		});
	}

	// Track pending insight fetch to cancel on rapid dataset switches
	let insightsFetchController: AbortController | null = null;

	async function handleDatasetChange(datasetId: string | null) {
		// Clear conversation when switching datasets to avoid context confusion
		if (datasetId !== selectedDatasetId && messages.length > 0) {
			clearConversation();
		}
		selectedDatasetId = datasetId;
		selectedDatasetDetail = null;
		datasetInsights = null;
		insightsError = null;

		// Cancel pending insights fetch
		if (insightsFetchController) {
			insightsFetchController.abort();
			insightsFetchController = null;
		}

		if (!datasetId) return;

		// Fetch full dataset details including column profiles
		isLoadingDetail = true;
		try {
			selectedDatasetDetail = await apiClient.getDataset(datasetId);
		} catch {
			// Silently fail - column hints are optional enhancement
		} finally {
			isLoadingDetail = false;
		}

		// Fetch insights (parallel with detail fetch would be ideal but sequential is simpler)
		insightsLoading = true;
		insightsFetchController = new AbortController();
		try {
			datasetInsights = await apiClient.getDatasetInsights(datasetId);
		} catch (err) {
			// Handle 422 (unprofiled dataset) gracefully
			if (err instanceof ApiClientError && err.status === 422) {
				insightsError = 'profiling';
			} else if (err instanceof Error && err.name !== 'AbortError') {
				// Silently fail for other errors - insights are optional
				insightsError = 'unavailable';
			}
		} finally {
			insightsLoading = false;
			insightsFetchController = null;
		}
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

		<!-- Column hints -->
		{#if isLoadingDetail}
			<div class="flex items-center gap-1 text-xs text-neutral-400">
				<Loader2 class="w-3 h-3 animate-spin" />
				<span>Loading columns...</span>
			</div>
		{:else if selectedDatasetDetail?.profiles && selectedDatasetDetail.profiles.length > 0}
			{@const profiles = selectedDatasetDetail.profiles}
			{@const displayLimit = 5}
			{@const visibleCols = profiles.slice(0, displayLimit)}
			{@const hiddenCount = profiles.length - displayLimit}
			<div class="flex flex-wrap items-center gap-1">
				<span class="text-xs text-neutral-400">Columns:</span>
				{#each visibleCols as profile (profile.id)}
					<span
						class="px-1.5 py-0.5 text-xs bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded"
						title="{profile.column_name} ({profile.data_type})"
					>
						{profile.column_name}
					</span>
				{/each}
				{#if hiddenCount > 0}
					<span class="text-xs text-neutral-400">+{hiddenCount} more</span>
				{/if}
			</div>
		{/if}

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
			<!-- Empty state: show insights or placeholder -->
			{#if insightsLoading}
				<!-- Loading insights skeleton -->
				<div class="space-y-3 animate-pulse">
					<div class="h-4 w-24 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
					<div class="grid grid-cols-2 gap-2">
						{#each [1, 2, 3, 4] as i (i)}
							<div class="h-16 bg-neutral-100 dark:bg-neutral-800 rounded-md"></div>
						{/each}
					</div>
					<div class="h-4 w-32 bg-neutral-200 dark:bg-neutral-700 rounded mt-4"></div>
					<div class="space-y-2">
						{#each [1, 2] as i (i)}
							<div class="h-12 bg-neutral-100 dark:bg-neutral-800 rounded-md"></div>
						{/each}
					</div>
				</div>
			{:else if datasetInsights}
				<!-- Show insights preview -->
				<InsightsPreview
					insights={datasetInsights}
					onQuestionClick={handleSuggestedQuestion}
				/>
			{:else if insightsError === 'profiling'}
				<!-- Dataset being profiled -->
				<div class="h-full flex items-center justify-center text-neutral-500 dark:text-neutral-400">
					<div class="text-center max-w-md">
						<Loader2 class="w-8 h-8 mx-auto mb-3 animate-spin text-brand-500" />
						<p class="text-sm font-medium mb-1">Analyzing your data...</p>
						<p class="text-xs text-neutral-400 dark:text-neutral-500">
							First-time analysis may take a moment. You can ask questions while we prepare insights.
						</p>
					</div>
				</div>
			{:else}
				<!-- Default empty state -->
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
			{/if}
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
				placeholder={placeholderText}
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
