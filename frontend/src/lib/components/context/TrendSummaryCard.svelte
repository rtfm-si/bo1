<script lang="ts">
	/**
	 * TrendSummaryCard - AI-generated market trend summary display
	 *
	 * Shows an executive summary of current market trends for user's industry
	 * with key trends, opportunities, and threats.
	 * Supports tier-gated timeframe views (3m/12m/24m).
	 */
	import {
		TrendingUp,
		RefreshCw,
		Loader2,
		Clock,
		Lightbulb,
		AlertTriangle,
		Sparkles,
		ChevronDown,
		ChevronUp,
		Lock
	} from 'lucide-svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';

	import { formatDate } from '$lib/utils/time-formatting';
	interface TrendSummary {
		summary: string;
		key_trends: string[];
		opportunities: string[];
		threats: string[];
		generated_at: string;
		industry: string;
		timeframe?: string;
		available_timeframes?: string[];
	}

	type Timeframe = 'now' | '3m' | '12m' | '24m';

	interface Props {
		summary: TrendSummary | null;
		isStale?: boolean;
		needsIndustry?: boolean;
		isLoading?: boolean;
		isRefreshing?: boolean;
		error?: string | null;
		selectedTimeframe?: Timeframe;
		availableTimeframes?: string[];
		upgradePrompt?: string | null;
		canRefresh?: boolean;
		refreshBlockedReason?: string | null;
		onRefresh?: () => void;
		onTimeframeChange?: (timeframe: Timeframe) => void;
	}

	const TIMEFRAME_LABELS: Record<Timeframe, string> = {
		'now': 'Now',
		'3m': '3 Month',
		'12m': '12 Month',
		'24m': '24 Month'
	};

	const ALL_TIMEFRAMES: Timeframe[] = ['now', '3m', '12m', '24m'];

	let {
		summary,
		isStale = false,
		needsIndustry = false,
		isLoading = false,
		isRefreshing = false,
		error = null,
		selectedTimeframe = 'now',
		availableTimeframes = ['now', '3m'],
		upgradePrompt = null,
		canRefresh = true,
		refreshBlockedReason = null,
		onRefresh,
		onTimeframeChange
	}: Props = $props();

	// Refresh is only blocked for "Now" view (forecasts have their own tier gating)
	const isRefreshBlocked = $derived(selectedTimeframe === 'now' && !canRefresh);

	let isExpanded = $state(true);

	function isTimeframeLocked(tf: Timeframe): boolean {
		// 'now' is never locked - available to all tiers
		if (tf === 'now') return false;
		return !availableTimeframes.includes(tf);
	}

	function handleTimeframeClick(tf: Timeframe) {
		if (!isTimeframeLocked(tf) && onTimeframeChange) {
			onTimeframeChange(tf);
		}
	}


	function daysAgo(dateStr: string | null): number {
		if (!dateStr) return 0;
		const date = new Date(dateStr);
		const now = new Date();
		return Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
	}
</script>

<BoCard variant="default" padding="lg">
	<div class="space-y-4">
		<!-- Header -->
		<div class="flex items-start justify-between gap-3">
			<div class="flex items-center gap-3">
				<div
					class="w-10 h-10 rounded-lg bg-gradient-to-br from-brand-500 to-brand-600 dark:from-brand-600 dark:to-brand-700 flex items-center justify-center flex-shrink-0 shadow-sm"
				>
					<TrendingUp class="h-5 w-5 text-white" />
				</div>
				<div>
					<h3 class="font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
						{selectedTimeframe === 'now' ? 'Current Market Trends' : 'Market Trends Forecast'}
						{#if summary}
							<Badge variant="neutral" size="sm">{summary.industry}</Badge>
						{/if}
					</h3>
					{#if summary}
						<p class="text-xs text-neutral-500 dark:text-neutral-400 flex items-center gap-1 mt-0.5">
							<Clock class="h-3 w-3" />
							<span>Updated {formatDate(summary.generated_at)}</span>
							{#if isStale}
								<span class="text-warning-600 dark:text-warning-400">(outdated)</span>
							{/if}
						</p>
					{/if}
				</div>
			</div>

			<!-- Actions -->
			<div class="flex items-center gap-1 flex-shrink-0">
				{#if onRefresh && !needsIndustry}
					<BoButton
						variant="outline"
						size="sm"
						onclick={onRefresh}
						disabled={isRefreshing || isLoading || isRefreshBlocked}
						title={isRefreshBlocked && refreshBlockedReason ? refreshBlockedReason : isStale ? 'Refresh forecast (outdated)' : 'Refresh forecast'}
					>
						{#if isRefreshing}
							<Loader2 class="h-4 w-4 animate-spin mr-1" />
							<span>Refreshing...</span>
						{:else if isRefreshBlocked}
							<Lock class="h-4 w-4 mr-1" />
							<span>Refresh</span>
						{:else}
							<RefreshCw class="h-4 w-4 mr-1" />
							<span>Refresh</span>
						{/if}
					</BoButton>
				{/if}
				{#if summary}
					<BoButton
						variant="ghost"
						size="sm"
						onclick={() => (isExpanded = !isExpanded)}
						title={isExpanded ? 'Collapse' : 'Expand'}
					>
						{#if isExpanded}
							<ChevronUp class="h-4 w-4" />
						{:else}
							<ChevronDown class="h-4 w-4" />
						{/if}
					</BoButton>
				{/if}
			</div>
		</div>

		<!-- Timeframe Selector -->
		{#if !needsIndustry}
			<div class="flex items-center gap-2">
				<span class="text-xs text-neutral-500 dark:text-neutral-400">Timeframe:</span>
				<div class="flex rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					{#each ALL_TIMEFRAMES as tf}
						<button
							class="px-3 py-1.5 text-xs font-medium transition-colors flex items-center gap-1
								{selectedTimeframe === tf
									? 'bg-brand-500 text-white'
									: isTimeframeLocked(tf)
										? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 dark:text-neutral-500 cursor-not-allowed'
										: 'bg-white dark:bg-neutral-900 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800'}"
							onclick={() => handleTimeframeClick(tf)}
							disabled={isTimeframeLocked(tf)}
							title={isTimeframeLocked(tf) ? `Upgrade to unlock ${TIMEFRAME_LABELS[tf]} forecasts` : TIMEFRAME_LABELS[tf]}
						>
							{#if isTimeframeLocked(tf)}
								<Lock class="h-3 w-3" />
							{/if}
							{TIMEFRAME_LABELS[tf]}
						</button>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Upgrade Prompt -->
		{#if upgradePrompt}
			<Alert variant="warning" title="Upgrade required">
				{upgradePrompt}
			</Alert>
		{/if}

		<!-- Refresh Blocked Message (for "Now" view only) -->
		{#if isRefreshBlocked && refreshBlockedReason && selectedTimeframe === 'now'}
			<Alert variant="info" title="Refresh cooldown">
				{refreshBlockedReason}
			</Alert>
		{/if}

		<!-- Error State -->
		{#if error}
			<Alert variant="error" title="Error loading trends">
				{error}
			</Alert>
		{/if}

		<!-- Needs Industry State -->
		{#if needsIndustry && !isLoading}
			<Alert variant="warning" title="Industry not set">
				Set your industry in Business Context to see market trends for your sector.
			</Alert>
		{/if}

		<!-- Loading State -->
		{#if isLoading}
			<div class="flex items-center justify-center py-8">
				<Loader2 class="h-6 w-6 animate-spin text-brand-500" />
				<span class="ml-2 text-neutral-600 dark:text-neutral-400">Loading trends...</span>
			</div>
		{/if}

		<!-- Empty State -->
		{#if !summary && !isLoading && !needsIndustry && !error}
			<div class="text-center py-6">
				<Sparkles class="h-8 w-8 text-brand-400 mx-auto mb-2" />
				<p class="text-neutral-600 dark:text-neutral-400 text-sm">
					No trend summary yet. Click Refresh to generate one.
				</p>
			</div>
		{/if}

		<!-- Content -->
		{#if summary && isExpanded && !isLoading}
			<div class="space-y-5">
				<!-- Executive Summary -->
				<div class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg p-4">
					<p class="text-neutral-700 dark:text-neutral-300 text-sm leading-relaxed">
						{summary.summary}
					</p>
				</div>

				<!-- Key Trends -->
				{#if summary.key_trends.length > 0}
					<div>
						<div class="flex items-center gap-2 mb-3">
							<TrendingUp class="h-4 w-4 text-brand-600 dark:text-brand-400" />
							<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
								>Key Trends</span
							>
						</div>
						<ul class="space-y-2">
							{#each summary.key_trends as trend, i}
								<li
									class="flex items-start gap-2 text-sm text-neutral-600 dark:text-neutral-400 pl-1"
								>
									<span
										class="w-5 h-5 rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 flex items-center justify-center flex-shrink-0 text-xs font-medium"
									>
										{i + 1}
									</span>
									<span>{trend}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Opportunities & Threats Grid -->
				<div class="grid md:grid-cols-2 gap-4">
					<!-- Opportunities -->
					{#if summary.opportunities.length > 0}
						<div
							class="bg-success-50 dark:bg-success-900/20 rounded-lg p-4 border border-success-200 dark:border-success-800"
						>
							<div class="flex items-center gap-2 mb-3">
								<Lightbulb class="h-4 w-4 text-success-600 dark:text-success-400" />
								<span class="text-sm font-medium text-success-700 dark:text-success-300"
									>Opportunities</span
								>
							</div>
							<ul class="space-y-2">
								{#each summary.opportunities as opportunity}
									<li
										class="flex items-start gap-2 text-sm text-success-700 dark:text-success-300"
									>
										<span class="text-success-500 mt-1">•</span>
										<span>{opportunity}</span>
									</li>
								{/each}
							</ul>
						</div>
					{/if}

					<!-- Threats -->
					{#if summary.threats.length > 0}
						<div
							class="bg-warning-50 dark:bg-warning-900/20 rounded-lg p-4 border border-warning-200 dark:border-warning-800"
						>
							<div class="flex items-center gap-2 mb-3">
								<AlertTriangle class="h-4 w-4 text-warning-600 dark:text-warning-400" />
								<span class="text-sm font-medium text-warning-700 dark:text-warning-300"
									>Challenges</span
								>
							</div>
							<ul class="space-y-2">
								{#each summary.threats as threat}
									<li class="flex items-start gap-2 text-sm text-warning-700 dark:text-warning-300">
										<span class="text-warning-500 mt-1">•</span>
										<span>{threat}</span>
									</li>
								{/each}
							</ul>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Collapsed State Preview -->
		{#if summary && !isExpanded && !isLoading}
			<p class="text-neutral-600 dark:text-neutral-400 text-sm line-clamp-2">
				{summary.summary}
			</p>
		{/if}
	</div>
</BoCard>
