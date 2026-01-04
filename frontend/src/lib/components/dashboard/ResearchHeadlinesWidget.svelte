<script lang="ts">
	/**
	 * Research Headlines Widget - Newspaper-style insights from meetings
	 *
	 * Features:
	 * - Newspaper-style layout with headlines and taglines
	 * - Shows insights from board meetings (clarification questions)
	 * - Color-coded by category
	 * - Clickable links to source meetings
	 * - Empty state for users without insights
	 */
	import { apiClient } from '$lib/api/client';
	import type { ClarificationInsight, InsightCategory } from '$lib/api/types';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { onMount } from 'svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import { formatCompactRelativeTime } from '$lib/utils/time-formatting';

	// Fetch insights from context API
	const insightsData = useDataFetch(() => apiClient.getInsights());

	// Expose fetch method for parent component to trigger refresh
	export function refresh() {
		insightsData.fetch();
	}

	// Derived state
	const insights = $derived<ClarificationInsight[]>(
		(insightsData.data?.clarifications ?? [])
			.sort((a, b) => new Date(b.answered_at ?? 0).getTime() - new Date(a.answered_at ?? 0).getTime())
			.slice(0, 8)
	);
	const isLoading = $derived(insightsData.isLoading);
	const hasData = $derived(insights.length > 0);

	// Category display config (matching insights page)
	const categoryConfig: Record<InsightCategory, { label: string; color: string; icon: string }> = {
		revenue: { label: 'Revenue', color: 'text-green-600 dark:text-green-400', icon: '$' },
		growth: { label: 'Growth', color: 'text-emerald-600 dark:text-emerald-400', icon: '~' },
		customers: { label: 'Customers', color: 'text-blue-600 dark:text-blue-400', icon: '#' },
		team: { label: 'Team', color: 'text-purple-600 dark:text-purple-400', icon: '@' },
		product: { label: 'Product', color: 'text-indigo-600 dark:text-indigo-400', icon: '*' },
		operations: { label: 'Operations', color: 'text-orange-600 dark:text-orange-400', icon: '>' },
		market: { label: 'Market', color: 'text-cyan-600 dark:text-cyan-400', icon: '%' },
		competition: { label: 'Competition', color: 'text-red-600 dark:text-red-400', icon: '!' },
		funding: { label: 'Funding', color: 'text-amber-600 dark:text-amber-400', icon: '+' },
		costs: { label: 'Costs', color: 'text-rose-600 dark:text-rose-400', icon: '-' },
		uncategorized: { label: 'Other', color: 'text-slate-500 dark:text-slate-400', icon: '.' }
	};

	function getCategoryInfo(category: InsightCategory | null | undefined) {
		return categoryConfig[category ?? 'uncategorized'] ?? categoryConfig.uncategorized;
	}

	// Truncate text to a max length
	function truncate(text: string, maxLength: number): string {
		if (text.length <= maxLength) return text;
		return text.substring(0, maxLength).trim() + '...';
	}

	onMount(() => {
		insightsData.fetch();
	});
</script>

<BoCard class="overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
		<div class="flex items-center gap-2">
			<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"
				/>
			</svg>
			<h2 class="text-base font-semibold text-neutral-900 dark:text-white">Research Insights</h2>
			{#if insights.length > 0}
				<span class="inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400">
					{insights.length} recent
				</span>
			{/if}
		</div>
		<a
			href="/context/insights"
			class="text-xs text-neutral-500 dark:text-neutral-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors flex items-center gap-1"
		>
			View all
			<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
			</svg>
		</a>
	</div>

	{#if isLoading}
		<!-- Loading skeleton -->
		<div class="p-4 space-y-3">
			{#each [1, 2, 3, 4] as idx (idx)}
				<div class="animate-pulse">
					<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4 mb-1.5"></div>
					<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2"></div>
				</div>
			{/each}
		</div>
	{:else if !hasData}
		<!-- Empty state -->
		<div class="p-6 text-center">
			<div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-neutral-100 dark:bg-neutral-700 mb-3">
				<svg class="w-6 h-6 text-neutral-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"
					/>
				</svg>
			</div>
			<h3 class="text-sm font-medium text-neutral-900 dark:text-white mb-1">No insights yet</h3>
			<p class="text-xs text-neutral-500 dark:text-neutral-400 max-w-xs mx-auto">
				Run a board meeting to discover insights about your business. Each clarifying question becomes research.
			</p>
		</div>
	{:else}
		<!-- Newspaper-style headlines -->
		<div class="divide-y divide-neutral-100 dark:divide-neutral-700/50">
			{#each insights as insight (insight.question)}
				{@const catInfo = getCategoryInfo(insight.category)}
				<a
					href={insight.session_id ? `/meeting/${insight.session_id}` : '/context/insights'}
					class="block px-4 py-3 hover:bg-neutral-50 dark:hover:bg-neutral-700/30 transition-colors group"
				>
					<!-- Category badge + time -->
					<div class="flex items-center gap-2 mb-1">
						<span class="text-[10px] font-bold uppercase tracking-wider {catInfo.color}">
							{catInfo.label}
						</span>
						{#if insight.answered_at}
							<span class="text-[10px] text-neutral-400 dark:text-neutral-500">
								{formatCompactRelativeTime(insight.answered_at)}
							</span>
						{/if}
					</div>
					<!-- Headline (question) -->
					<h3 class="text-sm font-semibold text-neutral-900 dark:text-white leading-tight group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
						{truncate(insight.question, 80)}
					</h3>
					<!-- Tagline (answer) -->
					<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 leading-snug">
						{truncate(insight.answer, 100)}
					</p>
				</a>
			{/each}
		</div>
	{/if}
</BoCard>
