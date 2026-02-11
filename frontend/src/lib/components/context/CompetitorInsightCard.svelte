<script lang="ts">
	/**
	 * CompetitorInsightCard - AI-powered competitor analysis card
	 *
	 * Shows structured competitive intelligence including strengths,
	 * weaknesses, and market gaps. Supports generation, refresh, and delete.
	 */
	import {
		Building2,
		Users,
		DollarSign,
		ThumbsUp,
		ThumbsDown,
		Target,
		Trash2,
		RefreshCw,
		Loader2,
		Clock
	} from 'lucide-svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import type { CompetitorInsight } from '$lib/api/types';

	import { formatDate } from '$lib/utils/time-formatting';
	interface Props {
		insight: CompetitorInsight;
		isGenerating?: boolean;
		onRefresh?: () => void;
		onDelete?: () => void;
	}

	let { insight, isGenerating = false, onRefresh, onDelete }: Props = $props();

</script>

<BoCard variant="bordered" padding="md">
	<div class="space-y-4">
		<!-- Header -->
		<div class="flex items-start justify-between">
			<div class="flex items-center gap-3">
				<div
					class="w-10 h-10 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center"
				>
					<Building2 class="h-5 w-5 text-brand-600 dark:text-brand-400" />
				</div>
				<div>
					<h4 class="font-semibold text-neutral-900 dark:text-neutral-100">
						{insight.name}
					</h4>
					{#if insight.tagline}
						<p class="text-sm text-neutral-500 dark:text-neutral-400 italic">
							"{insight.tagline}"
						</p>
					{/if}
				</div>
			</div>

			<!-- Actions -->
			<div class="flex items-center gap-1">
				{#if onRefresh}
					<BoButton
						variant="ghost"
						size="sm"
						onclick={onRefresh}
						disabled={isGenerating}
						title="Refresh insight"
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
						<Trash2 class="h-4 w-4 text-error-500" />
					</BoButton>
				{/if}
			</div>
		</div>

		<!-- Quick Stats -->
		{#if insight.size_estimate || insight.revenue_estimate}
			<div class="flex flex-wrap gap-4 text-sm">
				{#if insight.size_estimate}
					<div class="flex items-center gap-1.5 text-neutral-600 dark:text-neutral-400">
						<Users class="h-4 w-4" />
						<span>{insight.size_estimate}</span>
					</div>
				{/if}
				{#if insight.revenue_estimate}
					<div class="flex items-center gap-1.5 text-neutral-600 dark:text-neutral-400">
						<DollarSign class="h-4 w-4" />
						<span>{insight.revenue_estimate}</span>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Strengths -->
		{#if insight.strengths.length > 0}
			<div>
				<div class="flex items-center gap-1.5 mb-2">
					<ThumbsUp class="h-4 w-4 text-success-600 dark:text-success-400" />
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">Strengths</span>
				</div>
				<ul class="space-y-1">
					{#each insight.strengths as strength}
						<li class="text-sm text-neutral-600 dark:text-neutral-400 flex items-start gap-2">
							<span class="text-success-500 mt-1">+</span>
							<span>{strength}</span>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- Weaknesses -->
		{#if insight.weaknesses.length > 0}
			<div>
				<div class="flex items-center gap-1.5 mb-2">
					<ThumbsDown class="h-4 w-4 text-error-600 dark:text-error-400" />
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">Weaknesses</span
					>
				</div>
				<ul class="space-y-1">
					{#each insight.weaknesses as weakness}
						<li class="text-sm text-neutral-600 dark:text-neutral-400 flex items-start gap-2">
							<span class="text-error-500 mt-1">-</span>
							<span>{weakness}</span>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- Market Gaps -->
		{#if insight.market_gaps.length > 0}
			<div>
				<div class="flex items-center gap-1.5 mb-2">
					<Target class="h-4 w-4 text-brand-600 dark:text-brand-400" />
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
						>Opportunities</span
					>
				</div>
				<ul class="space-y-1">
					{#each insight.market_gaps as gap}
						<li class="text-sm text-neutral-600 dark:text-neutral-400 flex items-start gap-2">
							<span class="text-brand-500 mt-1">*</span>
							<span>{gap}</span>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- Footer -->
		<div class="flex items-center justify-between pt-2 border-t border-neutral-200 dark:border-neutral-700">
			<div class="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-500">
				<Clock class="h-3 w-3" />
				<span>Updated {formatDate(insight.last_updated)}</span>
			</div>
		</div>
	</div>
</BoCard>
