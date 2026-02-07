<script lang="ts">
	/**
	 * Renders a multi-step analytics response: SQL → chart → summary per step.
	 */
	import SqlPreview from './SqlPreview.svelte';
	import AnalyticsChart from './AnalyticsChart.svelte';

	interface StepData {
		step: number;
		description?: string;
		sql?: string;
		columns?: string[];
		row_count?: number;
		chart_config?: { data?: unknown[]; layout?: Record<string, unknown> } | null;
		summary?: string;
		error?: string;
	}

	interface Props {
		role: 'user' | 'assistant';
		content: string;
		steps?: StepData[];
		suggestions?: string[];
		isStreaming?: boolean;
		onSuggestionClick?: (suggestion: string) => void;
	}

	let {
		role,
		content,
		steps = [],
		suggestions = [],
		isStreaming = false,
		onSuggestionClick
	}: Props = $props();
</script>

<div class="flex gap-3 {role === 'user' ? 'justify-end' : 'justify-start'}">
	<div
		class="max-w-[90%] {role === 'user'
			? 'bg-accent-50 dark:bg-accent-900/20 border-accent-200 dark:border-accent-800'
			: 'bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700'} border rounded-xl px-4 py-3"
	>
		{#if role === 'user'}
			<p class="text-sm text-neutral-900 dark:text-neutral-100">{content}</p>
		{:else}
			<!-- Assistant message with steps -->
			{#if steps.length > 0}
				<div class="space-y-4">
					{#each steps as step (step.step)}
						<div class="border-l-2 border-accent-300 dark:border-accent-700 pl-3">
							<p class="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
								Step {step.step + 1}{step.description ? `: ${step.description}` : ''}
							</p>

							{#if step.sql}
								<SqlPreview sql={step.sql} />
							{/if}

							{#if step.row_count !== undefined}
								<p class="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
									{step.row_count} row{step.row_count !== 1 ? 's' : ''}
									{step.columns ? ` \u00b7 ${step.columns.length} columns` : ''}
								</p>
							{/if}

							{#if step.chart_config}
								<div class="mt-2">
									<AnalyticsChart figureJson={step.chart_config} />
								</div>
							{/if}

							{#if step.summary}
								<p class="text-sm text-neutral-700 dark:text-neutral-300 mt-2">{step.summary}</p>
							{/if}

							{#if step.error}
								<p class="text-sm text-red-600 dark:text-red-400 mt-1">{step.error}</p>
							{/if}
						</div>
					{/each}
				</div>
			{:else if content}
				<p class="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">{content}</p>
			{/if}

			<!-- Streaming indicator -->
			{#if isStreaming}
				<div class="flex items-center gap-1.5 mt-2">
					<div class="flex gap-0.5">
						<span class="w-1.5 h-1.5 bg-accent-400 rounded-full animate-pulse"></span>
						<span class="w-1.5 h-1.5 bg-accent-400 rounded-full animate-pulse" style="animation-delay: 0.15s"></span>
						<span class="w-1.5 h-1.5 bg-accent-400 rounded-full animate-pulse" style="animation-delay: 0.3s"></span>
					</div>
					<span class="text-xs text-neutral-400">Analyzing...</span>
				</div>
			{/if}

			<!-- Follow-up suggestions -->
			{#if suggestions.length > 0 && !isStreaming}
				<div class="mt-3 pt-3 border-t border-neutral-100 dark:border-neutral-700">
					<p class="text-xs text-neutral-500 dark:text-neutral-400 mb-2">Also consider:</p>
					<div class="flex flex-wrap gap-1.5">
						{#each suggestions as suggestion}
							<button
								class="text-xs px-2.5 py-1 rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 hover:bg-accent-100 dark:hover:bg-accent-900/30 hover:text-accent-700 dark:hover:text-accent-300 transition-colors"
								onclick={() => onSuggestionClick?.(suggestion)}
							>
								{suggestion}
							</button>
						{/each}
					</div>
				</div>
			{/if}
		{/if}
	</div>
</div>
