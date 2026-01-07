<script lang="ts">
	/**
	 * Research Headlines Widget - Shows recent research from meetings
	 *
	 * Features:
	 * - Shows actual research performed during board meetings
	 * - Displays research question, summary, and sources
	 * - Links to source URLs when available
	 * - Color-coded by category
	 * - Empty state for users without research
	 */
	import { apiClient } from '$lib/api/client';
	import type { RecentResearchItem } from '$lib/api/types';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { onMount } from 'svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import { formatCompactRelativeTime } from '$lib/utils/time-formatting';

	// Fetch recent research from API
	const researchData = useDataFetch(() => apiClient.getRecentResearch(8));

	// Expose fetch method for parent component to trigger refresh
	export function refresh() {
		researchData.fetch();
	}

	// Derived state
	const research = $derived<RecentResearchItem[]>(researchData.data?.research ?? []);
	const isLoading = $derived(researchData.isLoading);
	const hasData = $derived(research.length > 0);
	const totalCount = $derived(researchData.data?.total_count ?? 0);

	// Category display config
	type CategoryKey = 'saas_metrics' | 'market_analysis' | 'competitor_analysis' | 'industry_trends' | 'pricing' | 'growth' | 'funding' | 'general';
	const categoryConfig: Record<CategoryKey | 'default', { label: string; color: string }> = {
		saas_metrics: { label: 'Metrics', color: 'text-green-600 dark:text-green-400' },
		market_analysis: { label: 'Market', color: 'text-cyan-600 dark:text-cyan-400' },
		competitor_analysis: { label: 'Competition', color: 'text-red-600 dark:text-red-400' },
		industry_trends: { label: 'Trends', color: 'text-purple-600 dark:text-purple-400' },
		pricing: { label: 'Pricing', color: 'text-amber-600 dark:text-amber-400' },
		growth: { label: 'Growth', color: 'text-emerald-600 dark:text-emerald-400' },
		funding: { label: 'Funding', color: 'text-blue-600 dark:text-blue-400' },
		general: { label: 'Research', color: 'text-slate-600 dark:text-slate-400' },
		default: { label: 'Research', color: 'text-slate-500 dark:text-slate-400' }
	};

	function getCategoryInfo(category: string | null | undefined) {
		if (!category) return categoryConfig.default;
		return categoryConfig[category as CategoryKey] ?? categoryConfig.default;
	}

	// Truncate text to a max length
	function truncate(text: string | null | undefined, maxLength: number): string {
		if (!text) return '';
		if (text.length <= maxLength) return text;
		return text.substring(0, maxLength).trim() + '...';
	}

	// Get first valid source URL from research item
	function getFirstSourceUrl(item: RecentResearchItem): string | null {
		if (!item.sources || item.sources.length === 0) return null;
		for (const src of item.sources) {
			if (src.url) return src.url;
		}
		return null;
	}

	// Count valid sources
	function getSourceCount(item: RecentResearchItem): number {
		if (!item.sources) return 0;
		return item.sources.filter(s => s.url).length;
	}

	onMount(() => {
		researchData.fetch();
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
					d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
				/>
			</svg>
			<h2 class="text-base font-semibold text-neutral-900 dark:text-white">Research</h2>
			{#if totalCount > 0}
				<span class="inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400">
					{totalCount} total
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
					<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-full mb-1"></div>
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
						d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
					/>
				</svg>
			</div>
			<h3 class="text-sm font-medium text-neutral-900 dark:text-white mb-1">No research yet</h3>
			<p class="text-xs text-neutral-500 dark:text-neutral-400 max-w-xs mx-auto">
				Research from your board meetings will appear here. Start a meeting to gather market intelligence.
			</p>
		</div>
	{:else}
		<!-- Research items -->
		<div class="divide-y divide-neutral-100 dark:divide-neutral-700/50">
			{#each research as item (item.id)}
				{@const catInfo = getCategoryInfo(item.category)}
				{@const sourceUrl = getFirstSourceUrl(item)}
				{@const sourceCount = getSourceCount(item)}
				<div class="px-4 py-3 hover:bg-neutral-50 dark:hover:bg-neutral-700/30 transition-colors">
					<!-- Category badge + time -->
					<div class="flex items-center gap-2 mb-1">
						<span class="text-[10px] font-bold uppercase tracking-wider {catInfo.color}">
							{catInfo.label}
						</span>
						{#if item.created_at}
							<span class="text-[10px] text-neutral-400 dark:text-neutral-500">
								{formatCompactRelativeTime(item.created_at)}
							</span>
						{/if}
					</div>
					<!-- Research question -->
					<h3 class="text-sm font-semibold text-neutral-900 dark:text-white leading-tight mb-1">
						{truncate(item.question, 80)}
					</h3>
					<!-- Summary -->
					{#if item.summary}
						<p class="text-xs text-neutral-600 dark:text-neutral-300 leading-snug mb-2">
							{truncate(item.summary, 150)}
						</p>
					{/if}
					<!-- Sources -->
					{#if sourceCount > 0}
						<div class="flex items-center gap-2 flex-wrap">
							{#if sourceUrl}
								<a
									href={sourceUrl}
									target="_blank"
									rel="noopener noreferrer"
									class="inline-flex items-center gap-1 text-xs text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 transition-colors"
								>
									<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
									</svg>
									View source
								</a>
							{/if}
							{#if sourceCount > 1}
								<span class="text-[10px] text-neutral-400 dark:text-neutral-500">
									+{sourceCount - 1} more
								</span>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</BoCard>
