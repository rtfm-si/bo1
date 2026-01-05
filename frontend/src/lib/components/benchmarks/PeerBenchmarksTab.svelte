<script lang="ts">
	/**
	 * Peer Benchmarks Tab - Compare your metrics against industry peers
	 * Extracted from /context/peer-benchmarks for use in tabbed interface
	 *
	 * Features:
	 * - Consent toggle for data sharing
	 * - Percentile cards showing p25/p50/p75 with user position
	 * - Tier-gated metrics (locked indicators for upgrade)
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { PeerBenchmarkConsentStatus, PeerBenchmarksResponse, PeerBenchmarkPreviewResponse, ApiError } from '$lib/api/types';
	import Alert from '$lib/components/ui/Alert.svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	// Error codes from backend for specific handling
	type ContextErrorCode = 'API_CONTEXT_MISSING' | 'API_INDUSTRY_NOT_SET' | 'API_NOT_FOUND' | null;

	// State
	let consent = $state<PeerBenchmarkConsentStatus | null>(null);
	let benchmarks = $state<PeerBenchmarksResponse | null>(null);
	let preview = $state<PeerBenchmarkPreviewResponse | null>(null);
	let isLoading = $state(true);
	let isToggling = $state(false);
	let error = $state<string | null>(null);
	let errorCode = $state<ContextErrorCode>(null);

	onMount(async () => {
		await loadData();
	});

	/** Extract error code from API error if present */
	function extractErrorCode(e: unknown): ContextErrorCode {
		if (e && typeof e === 'object' && 'error_code' in e) {
			const code = (e as ApiError).error_code;
			if (code === 'API_CONTEXT_MISSING' || code === 'API_INDUSTRY_NOT_SET' || code === 'API_NOT_FOUND') {
				return code;
			}
		}
		return null;
	}

	async function loadData() {
		isLoading = true;
		error = null;
		errorCode = null;

		try {
			// Load consent status first
			consent = await apiClient.getPeerBenchmarkConsent();

			// If not consented, fetch preview metric to show teaser
			if (!consent.consented) {
				try {
					preview = await apiClient.getPeerBenchmarkPreview();
				} catch (e) {
					// Preview not available - check if it's a context/industry issue
					const code = extractErrorCode(e);
					if (code) {
						errorCode = code;
					}
					preview = null;
				}
			}

			// Try to load benchmarks (may fail if no context/industry set)
			try {
				benchmarks = await apiClient.getPeerBenchmarks();
			} catch (e) {
				const code = extractErrorCode(e);
				if (code) {
					// Context or industry not set - show appropriate guidance
					errorCode = code;
					benchmarks = null;
				} else {
					throw e;
				}
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load peer benchmarks';
			errorCode = extractErrorCode(e);
			console.error('Failed to load peer benchmarks:', e);
		} finally {
			isLoading = false;
		}
	}

	async function toggleConsent() {
		if (!consent) return;

		isToggling = true;
		try {
			if (consent.consented) {
				consent = await apiClient.optOutPeerBenchmarks();
			} else {
				consent = await apiClient.optInPeerBenchmarks();
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update consent';
		} finally {
			isToggling = false;
		}
	}

	function formatValue(value: number | null): string {
		if (value === null) return '-';
		if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
		if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
		if (value < 1 && value > 0) return value.toFixed(2);
		return value.toLocaleString();
	}

	function getPercentileColor(percentile: number | null): string {
		if (percentile === null) return 'bg-neutral-100 dark:bg-neutral-800';
		if (percentile >= 75) return 'bg-green-100 dark:bg-green-900/30';
		if (percentile >= 50) return 'bg-blue-100 dark:bg-blue-900/30';
		if (percentile >= 25) return 'bg-amber-100 dark:bg-amber-900/30';
		return 'bg-red-100 dark:bg-red-900/30';
	}

	function getPercentileLabel(percentile: number | null): string {
		if (percentile === null) return 'N/A';
		if (percentile >= 90) return 'Top 10%';
		if (percentile >= 75) return 'Top 25%';
		if (percentile >= 50) return 'Above median';
		if (percentile >= 25) return 'Below median';
		return 'Bottom 25%';
	}

	function getSourceBadge(source: string | undefined): { label: string; color: string; description: string } {
		switch (source) {
			case 'industry_research':
				return {
					label: 'Industry Research',
					color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
					description: 'Benchmark data sourced from industry research and reports'
				};
			case 'similar_industry':
				return {
					label: 'Similar Industry',
					color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
					description: 'Benchmarks from a similar industry (no exact match found)'
				};
			default:
				return {
					label: 'Peer Data',
					color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
					description: 'Anonymized data from opted-in peers in your industry'
				};
		}
	}

	function formatConfidence(confidence: number | null | undefined): string {
		if (confidence === null || confidence === undefined) return '';
		if (confidence >= 0.8) return 'High confidence';
		if (confidence >= 0.5) return 'Medium confidence';
		return 'Low confidence';
	}
</script>

<div class="space-y-6">
	{#if isLoading}
		<div class="flex items-center justify-center py-12">
			<Spinner size="lg" />
		</div>
	{:else if error}
		<Alert variant="error">
			<p>{error}</p>
			<button
				class="mt-2 text-sm font-medium text-red-700 hover:text-red-600 dark:text-red-300 dark:hover:text-red-200"
				onclick={loadData}
			>
				Try again
			</button>
		</Alert>
	{:else}
		<!-- Teaser Card for Non-Opted Users with Preview -->
		{#if !consent?.consented && preview}
			<BoCard class="border-brand-200 dark:border-brand-800 bg-gradient-to-br from-brand-50 to-white dark:from-brand-950/20 dark:to-neutral-900">
				<div class="p-4 sm:p-6">
					<div class="flex flex-col md:flex-row gap-6">
						<!-- Preview Metric -->
						<div class="flex-1">
							<div class="flex items-center gap-2 mb-3">
								<div class="w-2 h-2 rounded-full bg-brand-500 animate-pulse"></div>
								<span class="text-xs font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">
									Industry Preview
								</span>
							</div>
							<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-1">
								{preview.display_name}
							</h3>
							<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
								{preview.industry} industry median from {preview.sample_count} peers
							</p>
							<div class="inline-flex items-baseline gap-1 px-4 py-2 bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700">
								<span class="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
									{formatValue(preview.p50)}
								</span>
								<span class="text-sm text-neutral-500">median</span>
							</div>
						</div>

						<!-- CTA -->
						<div class="flex-shrink-0 flex flex-col justify-center items-start md:items-end gap-3">
							<p class="text-sm text-neutral-600 dark:text-neutral-400 max-w-xs">
								<strong>See how you compare.</strong> Opt in to view your percentile rank across all metrics.
							</p>
							<BoButton
								variant="brand"
								loading={isToggling}
								onclick={toggleConsent}
							>
								Opt In to Compare
							</BoButton>
						</div>
					</div>

					<!-- Blurred/locked preview of other metrics -->
					<div class="mt-6 pt-4 border-t border-neutral-200 dark:border-neutral-800">
						<div class="flex items-center gap-2 mb-3">
							<svg class="w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
							</svg>
							<span class="text-xs text-neutral-500">More metrics available after opt-in</span>
						</div>
						<div class="flex gap-2 flex-wrap">
							{#each ['Revenue', 'Customers', 'Growth Rate', 'Team Size', 'Churn'] as metric}
								<span class="px-3 py-1 text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-400 rounded-full blur-[1px]">
									{metric}
								</span>
							{/each}
							<span class="px-3 py-1 text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-400 rounded-full">
								+10 more
							</span>
						</div>
					</div>
				</div>
			</BoCard>
		{/if}

		<!-- Consent Card -->
		<BoCard>
			<div class="p-4 sm:p-6">
				<div class="flex items-start justify-between gap-4">
					<div class="flex-1">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
							{consent?.consented ? 'You\'re Contributing' : 'Join Peer Benchmarking'}
						</h2>
						<p class="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
							{#if consent?.consented}
								Your anonymized metrics are helping build better industry benchmarks. You can now see your percentile rank across all metrics.
							{:else if benchmarks}
								Join {benchmarks.metrics[0]?.sample_count || 'other'} peers in {benchmarks.industry} to see how your metrics stack up. Compare revenue, growth, churn, and more.
							{:else}
								Opt in to share your anonymized metrics and see how you compare to peers. No personal or company-identifying information is shared.
							{/if}
						</p>
						<div class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-400 dark:text-neutral-500">
							<span class="flex items-center gap-1">
								<svg class="w-3.5 h-3.5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
								</svg>
								K-anonymity protected (min 5 peers)
							</span>
							<span class="flex items-center gap-1">
								<svg class="w-3.5 h-3.5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
								</svg>
								No PII or company names
							</span>
							<span class="flex items-center gap-1">
								<svg class="w-3.5 h-3.5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
								</svg>
								Industry-level aggregates only
							</span>
						</div>
					</div>
					<div class="flex-shrink-0">
						<BoButton
							variant={consent?.consented ? 'secondary' : 'brand'}
							loading={isToggling}
							onclick={toggleConsent}
						>
							{consent?.consented ? 'Opt Out' : 'Opt In'}
						</BoButton>
					</div>
				</div>
			</div>
		</BoCard>

		<!-- Context/Industry Setup Guidance -->
		{#if errorCode === 'API_CONTEXT_MISSING'}
			<Alert variant="info">
				<p>
					<strong>Set up your business context first.</strong> To see peer benchmarks, you need to
					<a href="/context/overview" class="font-medium underline">set up your business context</a>
					with your company information.
				</p>
			</Alert>
		{:else if errorCode === 'API_INDUSTRY_NOT_SET'}
			<Alert variant="warning">
				<p>
					<strong>Select an industry.</strong> Please update your
					<a href="/context/overview" class="font-medium underline">business context</a>
					to select an industry and see peer comparisons.
				</p>
			</Alert>
		{:else if errorCode === 'API_NOT_FOUND' || !benchmarks}
			<Alert variant="info">
				<p>
					<strong>No peer data available yet.</strong> Peer benchmarks require multiple users in your industry to opt in.
					As more users join and share their anonymized metrics, you'll be able to see how you compare.
					{#if consent?.consented}
						Thank you for opting in — you're helping build valuable benchmarks for your industry!
					{:else}
						<button type="button" class="font-medium underline text-brand-600 dark:text-brand-400" onclick={toggleConsent}>Opt in now</button> to be among the first in your industry.
					{/if}
				</p>
			</Alert>
		{:else}
			<!-- Industry Header -->
			{@const sourceBadge = getSourceBadge(benchmarks.source)}
			<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
				<div>
					<div class="flex items-center gap-2 mb-1">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
							{benchmarks.industry} Benchmarks
						</h2>
						<span class={`text-xs px-2 py-0.5 rounded-full ${sourceBadge.color}`}>
							{sourceBadge.label}
						</span>
					</div>
					<p class="text-xs text-neutral-400 dark:text-neutral-500">
						{sourceBadge.description}
						{#if benchmarks.updated_at}
							• Updated {new Date(benchmarks.updated_at).toLocaleDateString()}
						{/if}
					</p>
					{#if benchmarks.similar_industry}
						<p class="text-xs text-amber-600 dark:text-amber-400 mt-1">
							Based on: {benchmarks.similar_industry}
						</p>
					{/if}
				</div>
				<div class="flex items-center gap-3 text-sm text-neutral-500 dark:text-neutral-400">
					{#if benchmarks.confidence !== null && benchmarks.confidence !== undefined}
						<span class="flex items-center gap-1">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							{formatConfidence(benchmarks.confidence)}
						</span>
					{/if}
					{#if benchmarks.source === 'peer_data'}
						<span>Min {benchmarks.k_anonymity_threshold} peers for data</span>
					{/if}
				</div>
			</div>

			<!-- Research Sources (if applicable) -->
			{#if benchmarks.sources && benchmarks.sources.length > 0 && benchmarks.source !== 'peer_data'}
				<details class="text-xs">
					<summary class="text-neutral-500 dark:text-neutral-400 cursor-pointer hover:text-neutral-700 dark:hover:text-neutral-300">
						View {benchmarks.sources.length} research sources
					</summary>
					<ul class="mt-2 space-y-1 pl-4 text-neutral-400 dark:text-neutral-500">
						{#each benchmarks.sources.slice(0, 5) as source}
							<li class="truncate">
								<a href={source} target="_blank" rel="noopener noreferrer" class="hover:text-brand-600 dark:hover:text-brand-400 underline">
									{source}
								</a>
							</li>
						{/each}
						{#if benchmarks.sources.length > 5}
							<li class="text-neutral-400">+{benchmarks.sources.length - 5} more</li>
						{/if}
					</ul>
				</details>
			{/if}

			<!-- Metrics Grid -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{#each benchmarks.metrics as metric (metric.metric)}
					<BoCard class={metric.locked ? 'opacity-60' : ''}>
						<div class="p-4">
							<!-- Metric Header -->
							<div class="flex items-center justify-between mb-3">
								<h3 class="font-medium text-neutral-900 dark:text-neutral-100">
									{metric.display_name}
								</h3>
								{#if metric.locked}
									<span class="text-xs px-2 py-0.5 bg-neutral-100 dark:bg-neutral-800 text-neutral-500 rounded-full">
										Upgrade to unlock
									</span>
								{:else if benchmarks.source === 'peer_data' && metric.sample_count < 5}
									<span class="text-xs px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full">
										Insufficient data
									</span>
								{/if}
							</div>

							{#if metric.locked}
								<!-- Locked State -->
								<div class="h-24 flex items-center justify-center">
									<div class="text-center text-neutral-400">
										<svg class="w-8 h-8 mx-auto mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
										</svg>
										<span class="text-xs">Pro feature</span>
									</div>
								</div>
							{:else if benchmarks.source === 'peer_data' && metric.sample_count < 5}
								<!-- Insufficient Data State (peer data only) -->
								<div class="h-24 flex items-center justify-center text-center">
									<p class="text-sm text-neutral-400 dark:text-neutral-500">
										Need {5 - metric.sample_count} more peers
									</p>
								</div>
							{:else}
								<!-- Percentile Bar -->
								<div class="space-y-3">
									<!-- User Value & Percentile -->
									{#if metric.user_value !== null}
										<div class={`p-2 rounded-lg ${getPercentileColor(metric.user_percentile)}`}>
											<div class="flex items-center justify-between">
												<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">
													Your value: {formatValue(metric.user_value)}
												</span>
												<span class="text-xs font-medium text-neutral-600 dark:text-neutral-400">
													{getPercentileLabel(metric.user_percentile)}
												</span>
											</div>
										</div>
									{:else}
										<div class="p-2 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
											<span class="text-sm text-neutral-400 dark:text-neutral-500">
												No data - add to context
											</span>
										</div>
									{/if}

									<!-- Percentile Range -->
									<div class="relative pt-2">
										<!-- Bar -->
										<div class="h-2 bg-neutral-100 dark:bg-neutral-800 rounded-full overflow-hidden">
											<div
												class="h-full bg-gradient-to-r from-red-400 via-yellow-400 via-50% to-green-400"
												style="width: 100%"
											></div>
										</div>

										<!-- Markers -->
										<div class="flex justify-between mt-1 text-xs text-neutral-400">
											<span>p10: {formatValue(metric.p10)}</span>
											<span>p50: {formatValue(metric.p50)}</span>
											<span>p90: {formatValue(metric.p90)}</span>
										</div>

										<!-- User position marker -->
										{#if metric.user_percentile !== null}
											<div
												class="absolute top-2 w-0.5 h-2 bg-brand-600 dark:bg-brand-400"
												style="left: {metric.user_percentile}%"
											>
												<div class="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-brand-600 dark:bg-brand-400"></div>
											</div>
										{/if}
									</div>

									<!-- Sample Size (only for peer data) -->
									{#if benchmarks.source === 'peer_data' && metric.sample_count > 0}
										<p class="text-xs text-neutral-400 dark:text-neutral-500 text-right">
											{metric.sample_count} peers
										</p>
									{:else if benchmarks.source !== 'peer_data'}
										<p class="text-xs text-neutral-400 dark:text-neutral-500 text-right">
											Industry research
										</p>
									{/if}
								</div>
							{/if}
						</div>
					</BoCard>
				{/each}
			</div>

			<!-- Upgrade CTA if metrics are locked -->
			{#if benchmarks.metrics.some(m => m.locked)}
				<BoCard>
					<div class="p-6 text-center">
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
							Unlock All Benchmarks
						</h3>
						<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
							Upgrade to Pro to see all peer comparison metrics and get unlimited insights.
						</p>
						<a
							href="/settings/billing"
							class="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
						>
							View Plans
						</a>
					</div>
				</BoCard>
			{/if}
		{/if}
	{/if}
</div>
