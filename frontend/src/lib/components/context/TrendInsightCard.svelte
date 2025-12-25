<script lang="ts">
	/**
	 * TrendInsightCard - AI-powered market trend insight card
	 *
	 * Shows structured analysis of market trends including key takeaway,
	 * relevance to user's business, and recommended actions.
	 */
	import {
		TrendingUp,
		ExternalLink,
		Trash2,
		RefreshCw,
		Loader2,
		Clock,
		Zap,
		Target,
		AlertCircle
	} from 'lucide-svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import type { TrendInsight } from '$lib/api/types';

	interface Props {
		insight: TrendInsight;
		isGenerating?: boolean;
		onRefresh?: () => void;
		onDelete?: () => void;
	}

	let { insight, isGenerating = false, onRefresh, onDelete }: Props = $props();

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return 'Unknown';
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}

	function getTimeframeBadge(
		timeframe: string | null
	): { label: string; variant: 'neutral' | 'success' | 'warning' } {
		switch (timeframe) {
			case 'immediate':
				return { label: 'Act Now', variant: 'warning' };
			case 'short_term':
				return { label: 'Short Term', variant: 'success' };
			case 'long_term':
				return { label: 'Long Term', variant: 'neutral' };
			default:
				return { label: 'Timing Unknown', variant: 'neutral' };
		}
	}

	function getConfidenceBadge(
		confidence: string | null
	): { label: string; variant: 'neutral' | 'success' | 'warning' } {
		switch (confidence) {
			case 'high':
				return { label: 'High Confidence', variant: 'success' };
			case 'medium':
				return { label: 'Medium', variant: 'neutral' };
			case 'low':
				return { label: 'Low Confidence', variant: 'warning' };
			default:
				return { label: '', variant: 'neutral' };
		}
	}

	function truncateUrl(url: string, maxLen = 50): string {
		try {
			const urlObj = new URL(url);
			const display = urlObj.hostname + urlObj.pathname;
			return display.length > maxLen ? display.substring(0, maxLen) + '...' : display;
		} catch {
			return url.length > maxLen ? url.substring(0, maxLen) + '...' : url;
		}
	}

	const timeframeBadge = $derived(getTimeframeBadge(insight.timeframe));
	const confidenceBadge = $derived(getConfidenceBadge(insight.confidence));
</script>

<BoCard variant="bordered" padding="md">
	<div class="space-y-4">
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<div class="flex items-start gap-3 flex-1 min-w-0">
				<div
					class="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center flex-shrink-0"
				>
					<TrendingUp class="h-5 w-5 text-green-600 dark:text-green-400" />
				</div>
				<div class="min-w-0 flex-1">
					<h4 class="font-semibold text-neutral-900 dark:text-neutral-100 line-clamp-2">
						{insight.title || 'Market Trend'}
					</h4>
					<a
						href={insight.url}
						target="_blank"
						rel="noopener noreferrer"
						class="text-xs text-brand-600 dark:text-brand-400 hover:underline flex items-center gap-1 mt-0.5"
					>
						<span class="truncate">{truncateUrl(insight.url)}</span>
						<ExternalLink class="h-3 w-3 flex-shrink-0" />
					</a>
				</div>
			</div>

			<!-- Actions -->
			<div class="flex items-center gap-1 flex-shrink-0">
				{#if onRefresh}
					<BoButton
						variant="ghost"
						size="sm"
						onclick={onRefresh}
						disabled={isGenerating}
						title="Re-analyze trend"
					>
						{#if isGenerating}
							<Loader2 class="h-4 w-4 animate-spin" />
						{:else}
							<RefreshCw class="h-4 w-4" />
						{/if}
					</BoButton>
				{/if}
				{#if onDelete}
					<BoButton variant="ghost" size="sm" onclick={onDelete} title="Delete insight">
						<Trash2 class="h-4 w-4 text-red-500" />
					</BoButton>
				{/if}
			</div>
		</div>

		<!-- Badges -->
		{#if insight.timeframe || insight.confidence}
			<div class="flex flex-wrap gap-2">
				{#if insight.timeframe}
					<Badge variant={timeframeBadge.variant} size="sm">
						<Clock class="h-3 w-3 mr-1" />
						{timeframeBadge.label}
					</Badge>
				{/if}
				{#if insight.confidence && insight.confidence !== 'medium'}
					<Badge variant={confidenceBadge.variant} size="sm">
						{confidenceBadge.label}
					</Badge>
				{/if}
			</div>
		{/if}

		<!-- Key Takeaway -->
		{#if insight.key_takeaway}
			<div>
				<div class="flex items-center gap-1.5 mb-2">
					<Zap class="h-4 w-4 text-amber-500" />
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
						>Key Takeaway</span
					>
				</div>
				<p class="text-sm text-neutral-600 dark:text-neutral-400">
					{insight.key_takeaway}
				</p>
			</div>
		{/if}

		<!-- Relevance -->
		{#if insight.relevance}
			<div>
				<div class="flex items-center gap-1.5 mb-2">
					<Target class="h-4 w-4 text-brand-600 dark:text-brand-400" />
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
						>Why This Matters</span
					>
				</div>
				<p class="text-sm text-neutral-600 dark:text-neutral-400">
					{insight.relevance}
				</p>
			</div>
		{/if}

		<!-- Recommended Actions -->
		{#if insight.actions.length > 0}
			<div>
				<div class="flex items-center gap-1.5 mb-2">
					<AlertCircle class="h-4 w-4 text-blue-600 dark:text-blue-400" />
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
						>Recommended Actions</span
					>
				</div>
				<ul class="space-y-1.5">
					{#each insight.actions as action, i}
						<li class="text-sm text-neutral-600 dark:text-neutral-400 flex items-start gap-2">
							<span class="text-brand-500 font-medium mt-0.5">{i + 1}.</span>
							<span>{action}</span>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- Footer -->
		<div
			class="flex items-center justify-between pt-2 border-t border-neutral-200 dark:border-neutral-700"
		>
			<div class="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-500">
				<Clock class="h-3 w-3" />
				<span>Analyzed {formatDate(insight.analyzed_at)}</span>
			</div>
		</div>
	</div>
</BoCard>
