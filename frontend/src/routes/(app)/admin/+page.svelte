<script lang="ts">
	import { Users, List, TrendingUp, DollarSign, Clock, Activity, BarChart3, History, PieChart, Bell, Tag, MessageSquare, Wrench, Globe, Database, Mail, Zap, ExternalLink, LineChart, Server, FileText } from 'lucide-svelte';
	import ExtendedKPIsPanel from '$lib/components/admin/ExtendedKPIsPanel.svelte';
	import ResearchCostsPanel from '$lib/components/admin/ResearchCostsPanel.svelte';
	import ResearchCacheMetrics from '$lib/components/admin/ResearchCacheMetrics.svelte';
	import UptimeStatusBadge from '$lib/components/admin/UptimeStatusBadge.svelte';
	import EmergencyToggles from '$lib/components/admin/EmergencyToggles.svelte';
	import { adminApi, type EmailStatsResponse, type ResearchCacheStats, type ObservabilityLinksResponse } from '$lib/api/admin';
	import { onMount } from 'svelte';

	interface AdminStats {
		totalUsers: number;
		totalMeetings: number;
		totalCost: number;
		whitelistCount: number;
		waitlistPending: number;
	}

	const defaultStats: AdminStats = {
		totalUsers: 0,
		totalMeetings: 0,
		totalCost: 0,
		whitelistCount: 0,
		waitlistPending: 0
	};

	let { data } = $props<{ data: { stats?: AdminStats } }>();

	let stats = $state<AdminStats>(defaultStats);
	let emailStats = $state<EmailStatsResponse | null>(null);
	let emailStatsLoading = $state(true);
	let cacheStats = $state<ResearchCacheStats | null>(null);
	let cacheStatsLoading = $state(true);
	let observabilityLinks = $state<ObservabilityLinksResponse | null>(null);

	// Sync stats when data prop changes
	$effect(() => {
		stats = data?.stats ?? defaultStats;
	});

	// Fetch email, cache stats, and observability links in parallel
	onMount(async () => {
		const fetchEmailStats = async () => {
			try {
				emailStats = await adminApi.getEmailStats(30);
			} catch (e) {
				console.error('Failed to load email stats:', e);
			} finally {
				emailStatsLoading = false;
			}
		};

		const fetchCacheStats = async () => {
			try {
				cacheStats = await adminApi.getResearchCacheStats();
			} catch (e) {
				console.error('Failed to load research cache stats:', e);
			} finally {
				cacheStatsLoading = false;
			}
		};

		const fetchObservabilityLinks = async () => {
			try {
				observabilityLinks = await adminApi.getObservabilityLinks();
			} catch (e) {
				console.error('Failed to load observability links:', e);
			}
		};

		await Promise.all([fetchEmailStats(), fetchCacheStats(), fetchObservabilityLinks()]);
	});
</script>

<svelte:head>
	<title>Admin Dashboard - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/dashboard"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
						aria-label="Back to dashboard"
					>
						<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</a>
					<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
						Admin Dashboard
					</h1>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Stats Cards -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
				<!-- Total Users -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Total Users</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{stats.totalUsers}</p>
						</div>
						<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
							<Users class="w-6 h-6 text-brand-600 dark:text-brand-400" />
						</div>
					</div>
				</div>

				<!-- Total Meetings -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Total Meetings</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{stats.totalMeetings}</p>
						</div>
						<div class="p-3 bg-accent-100 dark:bg-accent-900/30 rounded-lg">
							<TrendingUp class="w-6 h-6 text-accent-600 dark:text-accent-400" />
						</div>
					</div>
				</div>

				<!-- Total Cost -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Total Cost</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">${stats.totalCost.toFixed(2)}</p>
						</div>
						<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
							<DollarSign class="w-6 h-6 text-success-600 dark:text-success-400" />
						</div>
					</div>
				</div>

				<!-- Waitlist Pending -->
				<a
					href="/admin/waitlist"
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-amber-300 dark:hover:border-amber-700 transition-all duration-200"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Waitlist</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{stats.waitlistPending}</p>
						</div>
						<div class="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
							<Clock class="w-6 h-6 text-amber-600 dark:text-amber-400" />
						</div>
					</div>
				</a>

				<!-- Whitelist Count -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Whitelist</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{stats.whitelistCount}</p>
						</div>
						<div class="p-3 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
							<List class="w-6 h-6 text-warning-600 dark:text-warning-400" />
						</div>
					</div>
				</div>
			</div>

		<!-- Email Stats Card -->
		<div class="mb-8">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Email Activity</h2>
			<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
				{#if emailStatsLoading}
					<div class="flex items-center justify-center h-32">
						<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
					</div>
				{:else if emailStats}
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
						<!-- Total Sent -->
						<div class="flex items-center gap-4">
							<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
								<Mail class="w-6 h-6 text-brand-600 dark:text-brand-400" />
							</div>
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400">Total (30d)</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{emailStats.total}</p>
							</div>
						</div>

						<!-- Today -->
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Today</p>
							<p class="text-xl font-semibold text-neutral-900 dark:text-white">{emailStats.by_period.today}</p>
						</div>

						<!-- This Week -->
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">This Week</p>
							<p class="text-xl font-semibold text-neutral-900 dark:text-white">{emailStats.by_period.week}</p>
						</div>

						<!-- This Month -->
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">This Month</p>
							<p class="text-xl font-semibold text-neutral-900 dark:text-white">{emailStats.by_period.month}</p>
						</div>
					</div>

					<!-- By Type Breakdown -->
					{#if Object.keys(emailStats.by_type).length > 0}
						<div class="mt-6 pt-6 border-t border-neutral-200 dark:border-neutral-700">
							<p class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">By Type</p>
							<div class="flex flex-wrap gap-3">
								{#each Object.entries(emailStats.by_type).sort((a, b) => b[1] - a[1]) as [type, count]}
									<div class="px-3 py-1.5 bg-neutral-100 dark:bg-neutral-700 rounded-full text-sm">
										<span class="text-neutral-600 dark:text-neutral-400">{type.replace(/_/g, ' ')}:</span>
										<span class="font-medium text-neutral-900 dark:text-white ml-1">{count}</span>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				{:else}
					<p class="text-neutral-500 dark:text-neutral-400 text-center py-8">No email data available</p>
				{/if}
			</div>
		</div>

		<!-- Research Cache Stats Card -->
		<div class="mb-8">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Research Cache</h2>
			<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
				{#if cacheStatsLoading}
					<div class="flex items-center justify-center h-32">
						<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
					</div>
				{:else if cacheStats}
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
						<!-- Hit Rate -->
						<div class="flex items-center gap-4">
							<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
								<Zap class="w-6 h-6 text-success-600 dark:text-success-400" />
							</div>
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400">Hit Rate (30d)</p>
								<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{cacheStats.cache_hit_rate_30d.toFixed(1)}%</p>
							</div>
						</div>

						<!-- Cost Savings -->
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Savings (30d)</p>
							<p class="text-xl font-semibold text-success-600 dark:text-success-400">${cacheStats.cost_savings_30d.toFixed(2)}</p>
						</div>

						<!-- Total Cached -->
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Cached Results</p>
							<p class="text-xl font-semibold text-neutral-900 dark:text-white">{cacheStats.total_cached_results.toLocaleString()}</p>
						</div>

						<!-- Top Questions Count -->
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Top Questions</p>
							<p class="text-xl font-semibold text-neutral-900 dark:text-white">{cacheStats.top_cached_questions.length}</p>
						</div>
					</div>

					<!-- Top Cached Questions -->
					{#if cacheStats.top_cached_questions.length > 0}
						<details class="mt-6 pt-6 border-t border-neutral-200 dark:border-neutral-700">
							<summary class="text-sm font-medium text-neutral-700 dark:text-neutral-300 cursor-pointer hover:text-brand-600 dark:hover:text-brand-400">
								View top cached questions
							</summary>
							<div class="mt-3 space-y-2">
								{#each cacheStats.top_cached_questions.slice(0, 5) as q}
									<div class="p-3 bg-neutral-50 dark:bg-neutral-700/50 rounded-lg">
										<p class="text-sm text-neutral-900 dark:text-white truncate" title={q.question}>{q.question}</p>
										<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
											{q.hit_count} hits
										</p>
									</div>
								{/each}
							</div>
						</details>
					{/if}
				{:else}
					<p class="text-neutral-500 dark:text-neutral-400 text-center py-8">No cache data available</p>
				{/if}
			</div>
		</div>

		<!-- Research Cache Metrics (Detailed) -->
		<ResearchCacheMetrics />

		<!-- Research Costs Panel -->
		<ResearchCostsPanel />

		<!-- Extended KPIs Panel -->
		<ExtendedKPIsPanel />

		<!-- External Monitoring Status -->
		<div class="mb-8">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">System Status</h2>
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<UptimeStatusBadge statusPageUrl={observabilityLinks?.uptimerobot_url} />
				<EmergencyToggles />
			</div>

			<!-- Monitoring Quick Links -->
			{#if observabilityLinks && (observabilityLinks.grafana_url || observabilityLinks.prometheus_url || observabilityLinks.analytics_url || observabilityLinks.status_url)}
				<div class="mt-4 flex flex-wrap gap-3">
					{#if observabilityLinks.grafana_url}
						<a
							href={observabilityLinks.grafana_url}
							target="_blank"
							rel="noopener noreferrer"
							class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors"
						>
							<LineChart class="w-4 h-4 text-brand-500" />
							Grafana
							<ExternalLink class="w-3.5 h-3.5 text-neutral-400" />
						</a>
					{/if}
					{#if observabilityLinks.prometheus_url}
						<a
							href={observabilityLinks.prometheus_url}
							target="_blank"
							rel="noopener noreferrer"
							class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-700 hover:border-warning-300 dark:hover:border-warning-600 transition-colors"
						>
							<Server class="w-4 h-4 text-warning-500" />
							Prometheus
							<ExternalLink class="w-3.5 h-3.5 text-neutral-400" />
						</a>
					{/if}
					{#if observabilityLinks.analytics_url}
						<a
							href={observabilityLinks.analytics_url}
							target="_blank"
							rel="noopener noreferrer"
							class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-700 hover:border-info-300 dark:hover:border-info-600 transition-colors"
						>
							<BarChart3 class="w-4 h-4 text-info-500" />
							Analytics
							<ExternalLink class="w-3.5 h-3.5 text-neutral-400" />
						</a>
					{/if}
					{#if observabilityLinks.status_url}
						<a
							href={observabilityLinks.status_url}
							target="_blank"
							rel="noopener noreferrer"
							class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-700 hover:border-success-300 dark:hover:border-success-600 transition-colors"
						>
							<Activity class="w-4 h-4 text-success-500" />
							Status Page
							<ExternalLink class="w-3.5 h-3.5 text-neutral-400" />
						</a>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Quick Links - Monitoring -->
		<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Monitoring</h2>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 mb-8">
			<!-- Active Sessions Card -->
			<a
				href="/admin/sessions"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
						<Activity class="w-6 h-6 text-brand-600 dark:text-brand-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Active Sessions</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Monitor and control live meetings</p>
					</div>
				</div>
				<span class="text-sm text-brand-600 dark:text-brand-400">View sessions →</span>
			</a>

			<!-- Cost Analytics Card -->
			<a
				href="/admin/costs"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-success-300 dark:hover:border-success-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
						<BarChart3 class="w-6 h-6 text-success-600 dark:text-success-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Cost Analytics</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Track costs by user and time</p>
					</div>
				</div>
				<span class="text-sm text-success-600 dark:text-success-400">View analytics →</span>
			</a>

			<!-- User Metrics Card -->
			<a
				href="/admin/metrics"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-info-300 dark:hover:border-info-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-info-100 dark:bg-info-900/30 rounded-lg">
						<PieChart class="w-6 h-6 text-info-600 dark:text-info-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Usage Metrics</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">User signups, DAU, onboarding funnel</p>
					</div>
				</div>
				<span class="text-sm text-info-600 dark:text-info-400">View metrics →</span>
			</a>

			<!-- Kill History Card -->
			<a
				href="/admin/kill-history"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-error-300 dark:hover:border-error-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-error-100 dark:bg-error-900/30 rounded-lg">
						<History class="w-6 h-6 text-error-600 dark:text-error-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Kill History</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Session termination audit trail</p>
					</div>
				</div>
				<span class="text-sm text-error-600 dark:text-error-400">View history →</span>
			</a>

			<!-- Alert History Card -->
			<a
				href="/admin/alerts/history"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-warning-300 dark:hover:border-warning-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
						<Bell class="w-6 h-6 text-warning-600 dark:text-warning-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Alert History</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">ntfy.sh alert audit trail</p>
					</div>
				</div>
				<span class="text-sm text-warning-600 dark:text-warning-400">View alerts →</span>
			</a>

			<!-- AI Ops Self-Healing Card -->
			<a
				href="/admin/ops"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-accent-300 dark:hover:border-accent-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-accent-100 dark:bg-accent-900/30 rounded-lg">
						<Wrench class="w-6 h-6 text-accent-600 dark:text-accent-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">AI Ops Self-Healing</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Error patterns & auto-remediation</p>
					</div>
				</div>
				<span class="text-sm text-accent-600 dark:text-accent-400">View ops →</span>
			</a>

			<!-- Landing Page Analytics Card -->
			<a
				href="/admin/landing-analytics"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
						<Globe class="w-6 h-6 text-brand-600 dark:text-brand-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Landing Analytics</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Page views, conversions, geo</p>
					</div>
				</div>
				<span class="text-sm text-brand-600 dark:text-brand-400">View analytics →</span>
			</a>

			<!-- Embeddings Visualization Card -->
			<a
				href="/admin/embeddings"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-info-300 dark:hover:border-info-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-info-100 dark:bg-info-900/30 rounded-lg">
						<Database class="w-6 h-6 text-info-600 dark:text-info-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Embeddings</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Visualize stored embeddings</p>
					</div>
				</div>
				<span class="text-sm text-info-600 dark:text-info-400">View embeddings →</span>
			</a>
		</div>

		<!-- Quick Links - User Management -->
		<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">User Management</h2>
		<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
			<!-- Waitlist Card -->
			<a
				href="/admin/waitlist"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-amber-300 dark:hover:border-amber-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
						<Clock class="w-6 h-6 text-amber-600 dark:text-amber-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Waitlist</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Approve beta access requests</p>
					</div>
				</div>
				<span class="text-sm text-amber-600 dark:text-amber-400">
					{#if stats.waitlistPending > 0}
						{stats.waitlistPending} pending →
					{:else}
						View waitlist →
					{/if}
				</span>
			</a>

			<!-- Users Card -->
			<a
				href="/admin/users"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
						<Users class="w-6 h-6 text-brand-600 dark:text-brand-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">User Management</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">View and manage all users</p>
					</div>
				</div>
				<span class="text-sm text-brand-600 dark:text-brand-400">View users →</span>
			</a>

			<!-- Whitelist Card -->
			<a
				href="/admin/whitelist"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-warning-300 dark:hover:border-warning-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
						<List class="w-6 h-6 text-warning-600 dark:text-warning-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Beta Whitelist</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Manage beta access</p>
					</div>
				</div>
				<span class="text-sm text-warning-600 dark:text-warning-400">Manage whitelist →</span>
			</a>

			<!-- Promotions Card -->
			<a
				href="/admin/promotions"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-accent-300 dark:hover:border-accent-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-accent-100 dark:bg-accent-900/30 rounded-lg">
						<Tag class="w-6 h-6 text-accent-600 dark:text-accent-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Promotions</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Manage promo codes</p>
					</div>
				</div>
				<span class="text-sm text-accent-600 dark:text-accent-400">Manage promotions →</span>
			</a>

			<!-- Feedback Card -->
			<a
				href="/admin/feedback"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-info-300 dark:hover:border-info-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-info-100 dark:bg-info-900/30 rounded-lg">
						<MessageSquare class="w-6 h-6 text-info-600 dark:text-info-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">User Feedback</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Feature requests & problems</p>
					</div>
				</div>
				<span class="text-sm text-info-600 dark:text-info-400">View feedback →</span>
			</a>

			<!-- Blog Management Card -->
			<a
				href="/admin/blog"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-success-300 dark:hover:border-success-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
						<FileText class="w-6 h-6 text-success-600 dark:text-success-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Blog Management</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Create & publish SEO content</p>
					</div>
				</div>
				<span class="text-sm text-success-600 dark:text-success-400">Manage blog →</span>
			</a>
		</div>
	</main>
</div>
