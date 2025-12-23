<script lang="ts">
	/**
	 * Admin Feedback Page - Review and manage user feedback
	 * Includes sentiment analysis and theme extraction via Haiku
	 */
	import { onMount } from 'svelte';
	import { Button, Badge } from '$lib/components/ui';
	import { RefreshCw, MessageSquare, Lightbulb, Bug, Clock, CheckCircle, XCircle, Eye, Tag, TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-svelte';
	import {
		adminApi,
		type FeedbackResponse,
		type FeedbackStatsResponse,
		type FeedbackAnalysisSummary,
		type FeedbackType,
		type FeedbackStatus,
		type FeedbackSentiment
	} from '$lib/api/admin';

	// State
	let feedback = $state<FeedbackResponse[]>([]);
	let stats = $state<FeedbackStatsResponse | null>(null);
	let analysisSummary = $state<FeedbackAnalysisSummary | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let typeFilter = $state<FeedbackType | 'all'>('all');
	let statusFilter = $state<FeedbackStatus | 'all'>('all');
	let sentimentFilter = $state<FeedbackSentiment | 'all'>('all');
	let themeFilter = $state<string | null>(null);
	let selectedFeedback = $state<FeedbackResponse | null>(null);
	let isUpdating = $state(false);

	// Status badge variants
	const statusStyles: Record<FeedbackStatus, { variant: 'brand' | 'warning' | 'success' | 'error' | 'info' | 'neutral'; label: string }> = {
		new: { variant: 'brand', label: 'New' },
		reviewing: { variant: 'warning', label: 'Reviewing' },
		resolved: { variant: 'success', label: 'Resolved' },
		closed: { variant: 'neutral', label: 'Closed' }
	};

	// Sentiment styles
	const sentimentStyles: Record<FeedbackSentiment, { icon: typeof TrendingUp; color: string; label: string }> = {
		positive: { icon: TrendingUp, color: 'text-success-600 dark:text-success-400', label: 'Positive' },
		negative: { icon: TrendingDown, color: 'text-error-600 dark:text-error-400', label: 'Negative' },
		neutral: { icon: Minus, color: 'text-neutral-500 dark:text-neutral-400', label: 'Neutral' },
		mixed: { icon: AlertCircle, color: 'text-warning-600 dark:text-warning-400', label: 'Mixed' }
	};

	// Type icons
	function getTypeIcon(type: FeedbackType) {
		return type === 'feature_request' ? Lightbulb : Bug;
	}

	// Get sentiment icon component
	function getSentimentIcon(sentiment: FeedbackSentiment) {
		return sentimentStyles[sentiment]?.icon || Minus;
	}

	// Load data
	async function loadData() {
		isLoading = true;
		error = null;
		try {
			const [feedbackData, statsData, analysisData] = await Promise.all([
				adminApi.listFeedback({
					type: typeFilter === 'all' ? undefined : typeFilter,
					status: statusFilter === 'all' ? undefined : statusFilter,
					sentiment: sentimentFilter === 'all' ? undefined : sentimentFilter,
					theme: themeFilter || undefined,
					limit: 50
				}),
				adminApi.getFeedbackStats(),
				adminApi.getFeedbackAnalysisSummary()
			]);
			feedback = feedbackData.items;
			stats = statsData;
			analysisSummary = analysisData;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load feedback';
		} finally {
			isLoading = false;
		}
	}

	// Filter by theme
	function filterByTheme(theme: string) {
		themeFilter = themeFilter === theme ? null : theme;
	}

	// Update status
	async function updateStatus(id: string, status: FeedbackStatus) {
		isUpdating = true;
		try {
			const updated = await adminApi.updateFeedbackStatus(id, status);
			feedback = feedback.map((f) => (f.id === id ? updated : f));
			if (selectedFeedback?.id === id) {
				selectedFeedback = updated;
			}
			// Reload stats
			stats = await adminApi.getFeedbackStats();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to update status';
		} finally {
			isUpdating = false;
		}
	}

	// Format date
	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	onMount(() => {
		loadData();
	});

	// Reload when filters change
	$effect(() => {
		if (!isLoading) {
			// Access filters to track them
			void typeFilter;
			void statusFilter;
			void sentimentFilter;
			void themeFilter;
			loadData();
		}
	});
</script>

<svelte:head>
	<title>Feedback - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/admin"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
						aria-label="Back to admin dashboard"
					>
						<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</a>
					<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
						User Feedback
					</h1>
				</div>
				<Button variant="secondary" size="sm" onclick={loadData} disabled={isLoading}>
					{#snippet children()}
						<RefreshCw class="w-4 h-4 {isLoading ? 'animate-spin' : ''}" />
						Refresh
					{/snippet}
				</Button>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Stats Cards -->
		{#if stats}
			<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="text-2xl font-bold text-neutral-900 dark:text-white">{stats.total}</div>
					<div class="text-sm text-neutral-500 dark:text-neutral-400">Total Feedback</div>
				</div>
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="text-2xl font-bold text-brand-600 dark:text-brand-400">{stats.by_status?.new ?? 0}</div>
					<div class="text-sm text-neutral-500 dark:text-neutral-400">New</div>
				</div>
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="text-2xl font-bold text-amber-600 dark:text-amber-400">{stats.by_type?.feature_request ?? 0}</div>
					<div class="text-sm text-neutral-500 dark:text-neutral-400">Feature Requests</div>
				</div>
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="text-2xl font-bold text-error-600 dark:text-error-400">{stats.by_type?.problem_report ?? 0}</div>
					<div class="text-sm text-neutral-500 dark:text-neutral-400">Problem Reports</div>
				</div>
			</div>
		{/if}

		<!-- Analysis Summary -->
		{#if analysisSummary && analysisSummary.analyzed_count > 0}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 mb-6">
				<h3 class="text-sm font-medium text-neutral-900 dark:text-white mb-3">Sentiment Analysis</h3>
				<div class="flex flex-wrap gap-4 mb-4">
					<!-- Sentiment distribution -->
					{#each (['positive', 'negative', 'neutral', 'mixed'] as const) as sentiment}
						{@const count = analysisSummary.sentiment_counts[sentiment] ?? 0}
						{@const style = sentimentStyles[sentiment]}
						{@const SentimentIcon = style.icon}
						<button
							class="flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors {sentimentFilter === sentiment ? 'bg-neutral-200 dark:bg-neutral-700' : 'hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
							onclick={() => sentimentFilter = sentimentFilter === sentiment ? 'all' : sentiment}
						>
							<SentimentIcon class="w-4 h-4 {style.color}" />
							<span class="text-sm font-medium text-neutral-900 dark:text-white">{count}</span>
							<span class="text-sm text-neutral-500 dark:text-neutral-400">{style.label}</span>
						</button>
					{/each}
				</div>

				<!-- Top themes -->
				{#if analysisSummary.top_themes.length > 0}
					<h4 class="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-2">Top Themes</h4>
					<div class="flex flex-wrap gap-2">
						{#each analysisSummary.top_themes.slice(0, 10) as { theme, count }}
							<button
								class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-colors {themeFilter === theme ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600'}"
								onclick={() => filterByTheme(theme)}
							>
								<Tag class="w-3 h-3" />
								{theme}
								<span class="text-neutral-500 dark:text-neutral-400">({count})</span>
							</button>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Filter Tabs -->
		<div class="flex flex-wrap gap-4 mb-6">
			<!-- Type Filter -->
			<div class="flex gap-2">
				<span class="text-sm text-neutral-500 dark:text-neutral-400 self-center mr-2">Type:</span>
				<button
					class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors {typeFilter === 'all' ? 'bg-neutral-200 dark:bg-neutral-700 text-neutral-900 dark:text-white' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					onclick={() => typeFilter = 'all'}
				>
					All
				</button>
				<button
					class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors {typeFilter === 'feature_request' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					onclick={() => typeFilter = 'feature_request'}
				>
					<Lightbulb class="w-4 h-4 inline mr-1" />
					Features
				</button>
				<button
					class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors {typeFilter === 'problem_report' ? 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					onclick={() => typeFilter = 'problem_report'}
				>
					<Bug class="w-4 h-4 inline mr-1" />
					Problems
				</button>
			</div>

			<!-- Status Filter -->
			<div class="flex gap-2">
				<span class="text-sm text-neutral-500 dark:text-neutral-400 self-center mr-2">Status:</span>
				<button
					class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors {statusFilter === 'all' ? 'bg-neutral-200 dark:bg-neutral-700 text-neutral-900 dark:text-white' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					onclick={() => statusFilter = 'all'}
				>
					All
				</button>
				<button
					class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors {statusFilter === 'new' ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					onclick={() => statusFilter = 'new'}
				>
					New
				</button>
				<button
					class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors {statusFilter === 'reviewing' ? 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					onclick={() => statusFilter = 'reviewing'}
				>
					Reviewing
				</button>
				<button
					class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors {statusFilter === 'resolved' ? 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					onclick={() => statusFilter = 'resolved'}
				>
					Resolved
				</button>
			</div>
		</div>

		<!-- Error State -->
		{#if error}
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4 mb-6">
				<p class="text-error-800 dark:text-error-200">{error}</p>
				<Button variant="secondary" size="sm" onclick={loadData} class="mt-2">
					{#snippet children()}Retry{/snippet}
				</Button>
			</div>
		{/if}

		<!-- Loading State -->
		{#if isLoading}
			<div class="space-y-4">
				{#each [1, 2, 3] as _}
					<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 animate-pulse">
						<div class="flex items-start gap-4">
							<div class="w-10 h-10 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
							<div class="flex-1">
								<div class="h-5 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3 mb-2"></div>
								<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-2/3"></div>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{:else if feedback.length === 0}
			<!-- Empty State -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-12 text-center">
				<div class="mx-auto w-12 h-12 bg-neutral-100 dark:bg-neutral-700 rounded-full flex items-center justify-center mb-4">
					<MessageSquare class="w-6 h-6 text-neutral-400" />
				</div>
				<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-2">
					No feedback found
				</h3>
				<p class="text-neutral-600 dark:text-neutral-400">
					{#if typeFilter !== 'all' || statusFilter !== 'all'}
						Try adjusting your filters to see more feedback.
					{:else}
						Users haven't submitted any feedback yet.
					{/if}
				</p>
			</div>
		{:else}
			<!-- Feedback List -->
			<div class="space-y-4">
				{#each feedback as item (item.id)}
					{@const TypeIcon = getTypeIcon(item.type)}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 hover:border-neutral-300 dark:hover:border-neutral-600 transition-colors cursor-pointer"
						onclick={() => selectedFeedback = item}
						onkeydown={(e) => e.key === 'Enter' && (selectedFeedback = item)}
						role="button"
						tabindex="0"
					>
						<div class="flex items-start gap-4">
							<!-- Type Icon -->
							<div class={[
								'w-10 h-10 rounded-lg flex items-center justify-center',
								item.type === 'feature_request'
									? 'bg-amber-100 dark:bg-amber-900/30'
									: 'bg-error-100 dark:bg-error-900/30'
							].join(' ')}>
								<TypeIcon class={[
									'w-5 h-5',
									item.type === 'feature_request'
										? 'text-amber-600 dark:text-amber-400'
										: 'text-error-600 dark:text-error-400'
								].join(' ')} />
							</div>

							<!-- Content -->
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 mb-1">
									<h3 class="font-medium text-neutral-900 dark:text-white truncate">
										{item.title}
									</h3>
									<Badge variant={statusStyles[item.status].variant}>
										{statusStyles[item.status].label}
									</Badge>
									<!-- Sentiment badge -->
									{#if item.analysis?.sentiment}
										{@const style = sentimentStyles[item.analysis.sentiment]}
										{@const SentimentIcon = style.icon}
										<span class="flex items-center gap-1 {style.color}" title="{style.label} ({Math.round(item.analysis.sentiment_confidence * 100)}% confidence)">
											<SentimentIcon class="w-4 h-4" />
										</span>
									{/if}
								</div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400 line-clamp-2">
									{item.description}
								</p>
								<!-- Themes -->
								{#if item.analysis?.themes && item.analysis.themes.length > 0}
									<div class="flex flex-wrap gap-1 mt-2">
										{#each item.analysis.themes as theme}
											<button
												class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium transition-colors {themeFilter === theme ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-600'}"
												onclick={(e) => { e.stopPropagation(); filterByTheme(theme); }}
											>
												<Tag class="w-2.5 h-2.5" />
												{theme}
											</button>
										{/each}
									</div>
								{/if}
								<div class="flex items-center gap-4 mt-2 text-xs text-neutral-500 dark:text-neutral-500">
									<span class="flex items-center gap-1">
										<Clock class="w-3 h-3" />
										{formatDate(item.created_at)}
									</span>
									{#if item.context}
										<span class="flex items-center gap-1">
											<Eye class="w-3 h-3" />
											Has context
										</span>
									{/if}
								</div>
							</div>

							<!-- Quick Actions -->
							<div class="flex items-center gap-2" role="toolbar" aria-label="Quick actions">
								{#if item.status === 'new'}
									<Button variant="secondary" size="sm" onclick={() => updateStatus(item.id, 'reviewing')} disabled={isUpdating}>
										{#snippet children()}Start Review{/snippet}
									</Button>
								{:else if item.status === 'reviewing'}
									<Button variant="brand" size="sm" onclick={() => updateStatus(item.id, 'resolved')} disabled={isUpdating}>
										{#snippet children()}Resolve{/snippet}
									</Button>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</main>
</div>

<!-- Detail Modal -->
{#if selectedFeedback}
	{@const TypeIcon = getTypeIcon(selectedFeedback.type)}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onclick={() => selectedFeedback = null} role="presentation">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onclick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" tabindex="-1">
			<!-- Header -->
			<div class="sticky top-0 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 px-6 py-4">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<div class={[
							'w-10 h-10 rounded-lg flex items-center justify-center',
							selectedFeedback.type === 'feature_request'
								? 'bg-amber-100 dark:bg-amber-900/30'
								: 'bg-error-100 dark:bg-error-900/30'
						].join(' ')}>
							<TypeIcon class={[
								'w-5 h-5',
								selectedFeedback.type === 'feature_request'
									? 'text-amber-600 dark:text-amber-400'
									: 'text-error-600 dark:text-error-400'
							].join(' ')} />
						</div>
						<div>
							<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
								{selectedFeedback.title}
							</h2>
							<p class="text-sm text-neutral-500 dark:text-neutral-400">
								{selectedFeedback.type === 'feature_request' ? 'Feature Request' : 'Problem Report'}
							</p>
						</div>
					</div>
					<button
						type="button"
						class="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
						onclick={() => selectedFeedback = null}
						aria-label="Close"
					>
						<XCircle class="w-6 h-6" />
					</button>
				</div>
			</div>

			<!-- Content -->
			<div class="px-6 py-4 space-y-6">
				<!-- Status -->
				<div>
					<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Status</span>
					<div class="flex gap-2">
						{#each (['new', 'reviewing', 'resolved', 'closed'] as const) as status}
							<button
								class={[
									'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
									selectedFeedback.status === status
										? `bg-${statusStyles[status].variant}-100 text-${statusStyles[status].variant}-700 dark:bg-${statusStyles[status].variant}-900/30 dark:text-${statusStyles[status].variant}-300`
										: 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700'
								].join(' ')}
								onclick={() => selectedFeedback && updateStatus(selectedFeedback.id, status)}
								disabled={isUpdating}
							>
								{statusStyles[status].label}
							</button>
						{/each}
					</div>
				</div>

				<!-- Description -->
				<div>
					<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Description</span>
					<p class="text-neutral-600 dark:text-neutral-400 whitespace-pre-wrap">
						{selectedFeedback.description}
					</p>
				</div>

				<!-- Analysis (if available) -->
				{#if selectedFeedback.analysis}
					{@const style = sentimentStyles[selectedFeedback.analysis.sentiment]}
					{@const SentimentIcon = style.icon}
					<div>
						<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">AI Analysis</span>
						<div class="bg-neutral-50 dark:bg-neutral-900 rounded-lg p-4 space-y-3 text-sm">
							<div class="flex items-center justify-between">
								<span class="text-neutral-500 dark:text-neutral-400">Sentiment</span>
								<span class="flex items-center gap-1.5 {style.color}">
									<SentimentIcon class="w-4 h-4" />
									<span class="font-medium">{style.label}</span>
									<span class="text-neutral-400">({Math.round(selectedFeedback.analysis.sentiment_confidence * 100)}%)</span>
								</span>
							</div>
							{#if selectedFeedback.analysis.themes.length > 0}
								<div>
									<span class="text-neutral-500 dark:text-neutral-400 block mb-1.5">Themes</span>
									<div class="flex flex-wrap gap-1.5">
										{#each selectedFeedback.analysis.themes as theme}
											<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-neutral-200 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 text-xs">
												<Tag class="w-3 h-3" />
												{theme}
											</span>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<!-- Context (if available) -->
				{#if selectedFeedback.context}
					<div>
						<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Context</span>
						<div class="bg-neutral-50 dark:bg-neutral-900 rounded-lg p-4 space-y-2 text-sm">
							{#if selectedFeedback.context.user_tier}
								<div class="flex justify-between">
									<span class="text-neutral-500 dark:text-neutral-400">User Tier</span>
									<span class="text-neutral-900 dark:text-white font-medium">{selectedFeedback.context.user_tier}</span>
								</div>
							{/if}
							{#if selectedFeedback.context.page_url}
								<div class="flex justify-between">
									<span class="text-neutral-500 dark:text-neutral-400">Page URL</span>
									<span class="text-neutral-900 dark:text-white font-mono text-xs truncate max-w-xs">{selectedFeedback.context.page_url}</span>
								</div>
							{/if}
							{#if selectedFeedback.context.user_agent}
								<div class="flex justify-between">
									<span class="text-neutral-500 dark:text-neutral-400">Browser</span>
									<span class="text-neutral-900 dark:text-white text-xs truncate max-w-xs">{selectedFeedback.context.user_agent}</span>
								</div>
							{/if}
							{#if selectedFeedback.context.timestamp}
								<div class="flex justify-between">
									<span class="text-neutral-500 dark:text-neutral-400">Reported At</span>
									<span class="text-neutral-900 dark:text-white">{formatDate(selectedFeedback.context.timestamp)}</span>
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<!-- Metadata -->
				<div class="grid grid-cols-2 gap-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
					<div>
						<span class="block text-xs text-neutral-500 dark:text-neutral-400 mb-1">User ID</span>
						<span class="text-sm text-neutral-900 dark:text-white font-mono">{selectedFeedback.user_id}</span>
					</div>
					<div>
						<span class="block text-xs text-neutral-500 dark:text-neutral-400 mb-1">Feedback ID</span>
						<span class="text-sm text-neutral-900 dark:text-white font-mono">{selectedFeedback.id}</span>
					</div>
					<div>
						<span class="block text-xs text-neutral-500 dark:text-neutral-400 mb-1">Created</span>
						<span class="text-sm text-neutral-900 dark:text-white">{formatDate(selectedFeedback.created_at)}</span>
					</div>
					<div>
						<span class="block text-xs text-neutral-500 dark:text-neutral-400 mb-1">Updated</span>
						<span class="text-sm text-neutral-900 dark:text-white">{formatDate(selectedFeedback.updated_at)}</span>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
