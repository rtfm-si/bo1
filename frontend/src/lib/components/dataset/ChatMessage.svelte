<script lang="ts">
	/**
	 * ChatMessage - Renders a single chat message (user or assistant)
	 */
	import type { ConversationMessage, ChartSpec, ChartResultResponse } from '$lib/api/types';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import ChartRenderer from './ChartRenderer.svelte';
	import ChartModal from './ChartModal.svelte';
	import FavouriteButton from './FavouriteButton.svelte';
	import { apiClient } from '$lib/api/client';

	interface Props {
		message: ConversationMessage;
		datasetId?: string;
		isStreaming?: boolean;
		onNextStepClick?: (question: string) => void;
		// Favourite support
		isFavourited?: boolean;
		favouriteLoading?: boolean;
		onToggleFavourite?: () => void;
	}

	let {
		message,
		datasetId,
		isStreaming = false,
		onNextStepClick,
		isFavourited = false,
		favouriteLoading = false,
		onToggleFavourite
	}: Props = $props();

	// Chart preview state
	let chartLoading = $state(false);
	let chartError = $state<string | null>(null);
	let chartData = $state<ChartResultResponse | null>(null);
	let chartExpanded = $state(false);
	let modalOpen = $state(false);

	async function loadChartPreview() {
		if (!datasetId || !message.chart_spec || chartData) return;

		chartLoading = true;
		chartError = null;
		try {
			const spec = message.chart_spec as ChartSpec;
			const result = await apiClient.previewChart(datasetId, spec);
			chartData = result;
			chartExpanded = true;
		} catch (err) {
			chartError = err instanceof Error ? err.message : 'Failed to load chart';
		} finally {
			chartLoading = false;
		}
	}

	function handleExpand() {
		modalOpen = true;
	}

	const isUser = $derived(message.role === 'user');

	// Strip markdown formatting from text
	function stripMarkdown(text: string): string {
		return text
			.replace(/\*\*(.+?)\*\*/g, '$1')  // **bold**
			.replace(/\*(.+?)\*/g, '$1')       // *italic*
			.replace(/__(.+?)__/g, '$1')       // __bold__
			.replace(/_(.+?)_/g, '$1')         // _italic_
			.replace(/`(.+?)`/g, '$1')         // `code`
			.replace(/^#+\s*/gm, '')           // # headers
			.trim();
	}

	// Parse next steps from message content
	const parsedContent = $derived(() => {
		if (isUser || !message.content) return { content: message.content, nextSteps: [] };

		// Look for next steps section (various formats)
		const nextStepsPatterns = [
			/(?:##?\s*)?(?:Next Steps|What's Next|Try These|Suggested Questions|You might want to)[:\s]*\n((?:[-•*]\s*.+\n?)+)/gi,
			/(?:##?\s*)?(?:Next Steps|What's Next|Try These|Suggested Questions)[:\s]*\n((?:\d+\.\s*.+\n?)+)/gi
		];

		let content = message.content;
		let nextSteps: string[] = [];

		for (const pattern of nextStepsPatterns) {
			const match = content.match(pattern);
			if (match) {
				// Extract the list items
				const listText = match[1] || match[0];
				const items = listText
					.split(/\n/)
					.map((line: string) => stripMarkdown(line.replace(/^[-•*\d.]\s*/, '')))
					.filter((line: string) => line.length > 0 && line.length < 200);

				if (items.length > 0) {
					nextSteps = items.slice(0, 4); // Max 4 suggestions
					// Remove the next steps section from displayed content
					content = content.replace(match[0], '').trim();
					break;
				}
			}
		}

		return { content, nextSteps };
	});

	function formatTime(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleTimeString('en-US', {
			hour: 'numeric',
			minute: '2-digit'
		});
	}
</script>

<div class="flex {isUser ? 'justify-end' : 'justify-start'} mb-4">
	<div
		class="max-w-[85%] rounded-lg px-4 py-3 {isUser
			? 'bg-brand-500 text-white'
			: 'bg-neutral-100 dark:bg-neutral-700 text-neutral-900 dark:text-white'}"
	>
		<!-- Message content -->
		<div class="text-sm">
			{#if isUser}
				<div class="whitespace-pre-wrap">{message.content}</div>
			{:else}
				<MarkdownContent content={parsedContent().content} class="prose-sm" />
				{#if isStreaming}
					<span class="inline-block w-2 h-4 bg-current animate-pulse ml-0.5"></span>
				{/if}
			{/if}
		</div>

		<!-- Chart preview if present -->
		{#if message.chart_spec}
			<div class="mt-3 p-3 bg-white dark:bg-neutral-800 rounded border border-neutral-200 dark:border-neutral-600">
				{#if chartData && chartExpanded}
					<!-- Rendered chart -->
					<ChartRenderer
						figureJson={chartData.figure_json}
						title={(message.chart_spec as ChartSpec).title || ''}
						viewMode="simple"
						onExpand={handleExpand}
						{isFavourited}
						{favouriteLoading}
						onToggleFavourite={onToggleFavourite}
					/>
				{:else if chartLoading}
					<!-- Loading state -->
					<div class="flex items-center justify-center py-4">
						<div class="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
							<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							<span class="text-xs">Loading chart...</span>
						</div>
					</div>
				{:else if chartError}
					<!-- Error state -->
					<div class="text-xs text-error-600 dark:text-error-400 py-2">{chartError}</div>
				{:else}
					<!-- Chart metadata with preview button -->
					<div class="flex items-center justify-between">
						<div>
							<div class="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400 mb-1">
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
								</svg>
								<span>Chart: {(message.chart_spec as ChartSpec).chart_type} - {(message.chart_spec as ChartSpec).title || 'Untitled'}</span>
							</div>
							<div class="text-xs text-neutral-500 dark:text-neutral-400">
								X: {(message.chart_spec as ChartSpec).x_field} | Y: {(message.chart_spec as ChartSpec).y_field}
								{#if (message.chart_spec as ChartSpec).group_field}
									| Group: {(message.chart_spec as ChartSpec).group_field}
								{/if}
							</div>
						</div>
						<div class="flex items-center gap-2">
							{#if onToggleFavourite}
								<FavouriteButton
									{isFavourited}
									loading={favouriteLoading}
									size="sm"
									onclick={onToggleFavourite}
								/>
							{/if}
							{#if datasetId}
								<button
									type="button"
									onclick={loadChartPreview}
									class="px-3 py-1.5 text-xs rounded bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300 hover:bg-brand-200 dark:hover:bg-brand-800/40 transition-colors"
								>
									Preview
								</button>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Query result summary if present -->
		{#if message.query_result && !message.chart_spec}
			<div class="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
				Query returned {message.query_result.row_count || 0} rows
			</div>
		{/if}

		<!-- Next Steps buttons -->
		{#if !isUser && parsedContent().nextSteps.length > 0 && onNextStepClick}
			<div class="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-600">
				<div class="text-xs text-neutral-500 dark:text-neutral-400 mb-2">Try asking:</div>
				<div class="flex flex-wrap gap-2">
					{#each parsedContent().nextSteps as step}
						<button
							onclick={() => onNextStepClick(step)}
							class="text-xs px-3 py-1.5 rounded-full bg-white dark:bg-neutral-600 border border-neutral-300 dark:border-neutral-500 text-neutral-700 dark:text-neutral-200 hover:bg-brand-50 hover:border-brand-300 dark:hover:bg-brand-900/30 dark:hover:border-brand-700 transition-colors text-left"
						>
							{step}
						</button>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Timestamp -->
		<div class="mt-2 text-xs {isUser ? 'text-brand-200' : 'text-neutral-400 dark:text-neutral-500'}">
			{formatTime(message.timestamp)}
		</div>
	</div>
</div>

<!-- Chart Modal -->
{#if chartData}
	<ChartModal
		bind:open={modalOpen}
		figureJson={chartData.figure_json}
		title={(message.chart_spec as ChartSpec)?.title || 'Chart'}
	/>
{/if}
