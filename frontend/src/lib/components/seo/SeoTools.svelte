<script lang="ts">
	/**
	 * SEO Tools Component
	 *
	 * Analyze SEO trends for keywords/industry using AI-powered research.
	 * Manage topics for blog generation workflow.
	 */
	import { onMount } from 'svelte';
	import { apiClient, ApiClientError } from '$lib/api/client';
	import type {
		SeoTrendAnalysisResponse,
		SeoHistoryEntry,
		SeoTrendOpportunity,
		SeoTopic,
		SeoBlogArticle,
		TopicSuggestion,
		TrendSuggestion
	} from '$lib/api/types';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import BoFormField from '$lib/components/ui/BoFormField.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import ShimmerSkeleton from '$lib/components/ui/loading/ShimmerSkeleton.svelte';
	import ArticleDetailModal from '$lib/components/seo/ArticleDetailModal.svelte';
	import { toast } from '$lib/stores/toast';

	// Tab state
	let activeTab = $state<'research' | 'content'>('research');
	let historyDropdownOpen = $state(false);

	// State
	let keywords = $state('');
	let industry = $state('');
	let loading = $state(false);
	let historyLoading = $state(true);
	let topicsLoading = $state(true);
	let analysis = $state<SeoTrendAnalysisResponse | null>(null);
	let history = $state<SeoHistoryEntry[]>([]);
	let topics = $state<SeoTopic[]>([]);
	let remaining = $state<number>(-1);
	let error = $state<string | null>(null);
	let isQuotaError = $state(false);
	let addingTopic = $state<string | null>(null);
	let deletingTopic = $state<number | null>(null);

	// Manual topic form state
	let newTopicKeyword = $state('');
	let newTopicNotes = $state('');
	let addingManualTopic = $state(false);

	// Topic analysis state
	let analyzingTopics = $state(false);
	let topicSuggestions = $state<TopicSuggestion[]>([]);
	let addingSuggestion = $state<string | null>(null);
	let skipValidation = $state(false);

	// Autogenerate state
	let autogeneratingTopics = $state(false);

	// Discover trends state
	let discoverLoading = $state(false);
	let discoveredTrends = $state<TrendSuggestion[]>([]);
	let discoverError = $state<string | null>(null);
	let addingDiscoveredTrend = $state<string | null>(null);

	let articles = $state<SeoBlogArticle[]>([]);
	let articlesLoading = $state(true);
	let articlesRemaining = $state<number>(-1);
	let generatingArticle = $state<number | null>(null);
	let deletingArticle = $state<number | null>(null);

	// Article detail modal state
	let selectedArticle = $state<SeoBlogArticle | null>(null);
	let brandTone = $state<string | null>(null);

	// Context state for CTA
	let contextLoaded = $state(false);
	let hasIndustry = $state(false);
	let hasProductDescription = $state(false);

	// Load history, topics, articles, and brand tone on mount
	onMount(async () => {
		await Promise.all([loadHistory(), loadTopics(), loadArticles(), loadBrandTone()]);
	});

	async function loadBrandTone() {
		try {
			const response = await apiClient.getUserContext();
			brandTone = response.context?.brand_tone || null;
			hasIndustry = !!response.context?.industry;
			hasProductDescription = !!response.context?.product_description;
		} catch {
			console.debug('Could not load brand tone, using default');
		} finally {
			contextLoaded = true;
		}
	}

	async function loadHistory() {
		historyLoading = true;
		try {
			const response = await apiClient.getSeoHistory({ limit: 10 });
			history = response.analyses;
			remaining = response.remaining_this_month;
		} catch (err) {
			console.error('Failed to load SEO history:', err);
		} finally {
			historyLoading = false;
		}
	}

	async function loadTopics() {
		topicsLoading = true;
		try {
			const response = await apiClient.getSeoTopics({ limit: 50 });
			topics = response.topics;
		} catch (err) {
			console.error('Failed to load SEO topics:', err);
		} finally {
			topicsLoading = false;
		}
	}

	async function loadArticles() {
		articlesLoading = true;
		try {
			const response = await apiClient.getSeoArticles({ limit: 50 });
			articles = response.articles;
			articlesRemaining = response.remaining_this_month;
		} catch (err) {
			console.error('Failed to load SEO articles:', err);
		} finally {
			articlesLoading = false;
		}
	}

	async function analyzeTrends() {
		if (!keywords.trim()) {
			error = 'Please enter at least one keyword';
			return;
		}

		const keywordList = keywords
			.split(',')
			.map((k) => k.trim())
			.filter((k) => k.length > 0);

		if (keywordList.length === 0) {
			error = 'Please enter at least one keyword';
			return;
		}

		if (keywordList.length > 10) {
			error = 'Maximum 10 keywords allowed';
			return;
		}

		loading = true;
		error = null;
		isQuotaError = false;
		analysis = null;

		try {
			const response = await apiClient.analyzeSeoTrends({
				keywords: keywordList,
				industry: industry.trim() || undefined
			});
			analysis = response;
			remaining = response.remaining_analyses;
			toast.success('Trend analysis complete!');

			// Reload history to include new analysis
			await loadHistory();
		} catch (err: unknown) {
			console.error('Failed to analyze trends:', err);
			if (err instanceof ApiClientError && err.status === 429) {
				isQuotaError = true;
				error = err.message;
				toast.error('Analysis limit reached');
			} else if (err && typeof err === 'object' && 'message' in err) {
				error = (err as { message: string }).message;
				toast.error('Analysis failed');
			} else {
				error = 'Failed to analyze trends. Please try again.';
				toast.error('Analysis failed');
			}
		} finally {
			loading = false;
		}
	}

	function loadFromHistory(entry: SeoHistoryEntry) {
		keywords = entry.keywords.join(', ');
		industry = entry.industry || '';
	}

	function getTrendBadgeVariant(direction: string): 'success' | 'warning' | 'error' {
		switch (direction) {
			case 'rising':
				return 'success';
			case 'declining':
				return 'error';
			default:
				return 'warning';
		}
	}

	function getSeverityBadgeVariant(severity: string): 'error' | 'warning' | 'neutral' {
		switch (severity) {
			case 'high':
				return 'error';
			case 'medium':
				return 'warning';
			default:
				return 'neutral';
		}
	}

	function getStatusBadgeVariant(status: string): 'neutral' | 'warning' | 'success' {
		switch (status) {
			case 'researched':
				return 'neutral';
			case 'writing':
				return 'warning';
			case 'published':
				return 'success';
			default:
				return 'neutral';
		}
	}

	async function addToTopics(opp: SeoTrendOpportunity) {
		if (!analysis) return;
		addingTopic = opp.topic;
		try {
			const newTopic = await apiClient.createSeoTopic({
				keyword: opp.topic,
				source_analysis_id: analysis.id,
				notes: opp.description
			});
			topics = [newTopic, ...topics];
			toast.success(`Added "${opp.topic}" to topics`);
		} catch (err) {
			console.error('Failed to add topic:', err);
			toast.error('Failed to add topic');
		} finally {
			addingTopic = null;
		}
	}

	async function deleteTopic(topic: SeoTopic) {
		deletingTopic = topic.id;
		try {
			await apiClient.deleteSeoTopic(topic.id);
			topics = topics.filter((t) => t.id !== topic.id);
			toast.success(`Removed "${topic.keyword}" from topics`);
		} catch (err) {
			console.error('Failed to delete topic:', err);
			toast.error('Failed to remove topic');
		} finally {
			deletingTopic = null;
		}
	}

	async function generateArticle(topic: SeoTopic) {
		generatingArticle = topic.id;
		try {
			const article = await apiClient.generateSeoArticle(topic.id);
			articles = [article, ...articles];
			topics = topics.map((t) => (t.id === topic.id ? { ...t, status: 'writing' as const } : t));
			toast.success(`Article generated for "${topic.keyword}"`);
			// Auto-open the modal with the newly generated article
			selectedArticle = article;
			await loadArticles();
		} catch (err: unknown) {
			console.error('Failed to generate article:', err);
			if (err && typeof err === 'object' && 'message' in err) {
				toast.error((err as { message: string }).message);
			} else {
				toast.error('Failed to generate article');
			}
		} finally {
			generatingArticle = null;
		}
	}

	async function deleteArticle(article: SeoBlogArticle) {
		deletingArticle = article.id;
		try {
			await apiClient.deleteSeoArticle(article.id);
			articles = articles.filter((a) => a.id !== article.id);
			toast.success('Article deleted');
		} catch (err) {
			console.error('Failed to delete article:', err);
			toast.error('Failed to delete article');
		} finally {
			deletingArticle = null;
		}
	}

	function getArticleStatusBadgeVariant(status: string): 'neutral' | 'success' {
		return status === 'published' ? 'success' : 'neutral';
	}

	function handleArticleUpdate(updated: SeoBlogArticle) {
		articles = articles.map((a) => (a.id === updated.id ? updated : a));
		selectedArticle = updated;
	}

	function openArticleModal(article: SeoBlogArticle) {
		selectedArticle = article;
	}

	function closeArticleModal() {
		selectedArticle = null;
	}

	function isTopicAdded(keyword: string): boolean {
		return topics.some((t) => t.keyword.toLowerCase() === keyword.toLowerCase());
	}

	function hasArticleForTopic(topicId: number): boolean {
		return articles.some((a) => a.topic_id === topicId);
	}

	async function addManualTopic() {
		if (!newTopicKeyword.trim()) return;
		addingManualTopic = true;
		try {
			const newTopic = await apiClient.createSeoTopic({
				keyword: newTopicKeyword.trim(),
				notes: newTopicNotes.trim() || undefined
			});
			topics = [newTopic, ...topics];
			newTopicKeyword = '';
			newTopicNotes = '';
			toast.success(`Added "${newTopic.keyword}" to topics`);
		} catch (err) {
			console.error('Failed to add topic:', err);
			toast.error('Failed to add topic');
		} finally {
			addingManualTopic = false;
		}
	}

	async function autogenerateTopics() {
		autogeneratingTopics = true;
		try {
			const newTopics = await apiClient.autogenerateSeoTopics();
			if (newTopics.length > 0) {
				topics = [...newTopics, ...topics];
				toast.success(`Added ${newTopics.length} AI-suggested topics`);
			} else {
				toast.info('No new topics suggested - try adding some context first');
			}
		} catch (err) {
			console.error('Failed to autogenerate topics:', err);
			toast.error('Failed to autogenerate topics');
		} finally {
			autogeneratingTopics = false;
		}
	}

	async function analyzeTopicIdeas() {
		if (!newTopicKeyword.trim()) return;
		analyzingTopics = true;
		topicSuggestions = [];
		try {
			const words = newTopicKeyword
				.split(',')
				.map((w) => w.trim())
				.filter((w) => w.length > 0);
			if (words.length === 0) return;

			const response = await apiClient.analyzeSeoTopics(words, skipValidation);
			topicSuggestions = response.suggestions;
			if (topicSuggestions.length > 0) {
				const validatedCount = topicSuggestions.filter(
					(s) => s.validation_status === 'validated'
				).length;
				if (validatedCount > 0 && !skipValidation) {
					toast.success(`Found ${topicSuggestions.length} topic ideas (${validatedCount} validated)`);
				} else {
					toast.success(`Found ${topicSuggestions.length} topic ideas`);
				}
			} else {
				toast.info('No suggestions found - try different words');
			}
		} catch (err) {
			console.error('Failed to analyze topics:', err);
			toast.error('Failed to analyze topics');
		} finally {
			analyzingTopics = false;
		}
	}

	async function addSuggestionToTopics(suggestion: TopicSuggestion) {
		addingSuggestion = suggestion.keyword;
		try {
			const newTopic = await apiClient.createSeoTopic({
				keyword: suggestion.keyword,
				notes: suggestion.description
			});
			topics = [newTopic, ...topics];
			toast.success(`Added "${suggestion.keyword}" to topics`);
		} catch (err) {
			console.error('Failed to add suggestion:', err);
			toast.error('Failed to add topic');
		} finally {
			addingSuggestion = null;
		}
	}

	function getSeoPotentalBadgeVariant(potential: string): 'success' | 'warning' | 'neutral' {
		switch (potential) {
			case 'high':
				return 'success';
			case 'medium':
				return 'warning';
			default:
				return 'neutral';
		}
	}

	function getTrendStatusBadgeVariant(status: string): 'success' | 'warning' | 'error' {
		switch (status) {
			case 'rising':
				return 'success';
			case 'stable':
				return 'warning';
			default:
				return 'error';
		}
	}

	function clearSuggestions() {
		topicSuggestions = [];
	}

	async function discoverTrends() {
		discoverLoading = true;
		discoverError = null;
		discoveredTrends = [];
		try {
			const response = await apiClient.discoverTrends();
			discoveredTrends = response.suggestions;
			if (discoveredTrends.length > 0) {
				toast.success(`Discovered ${discoveredTrends.length} trending topics`);
			} else {
				toast.info('No trends found — try adding more business context');
			}
		} catch (err: unknown) {
			console.error('Failed to discover trends:', err);
			if (err instanceof ApiClientError && err.status === 422) {
				discoverError = 'no_context';
			} else if (err && typeof err === 'object' && 'message' in err) {
				discoverError = (err as { message: string }).message;
			} else {
				discoverError = 'Failed to discover trends. Please try again.';
			}
		} finally {
			discoverLoading = false;
		}
	}

	function useForAnalysis(trend: TrendSuggestion) {
		keywords = trend.suggested_keywords.join(', ');
		discoveredTrends = [];
		toast.success(`Keywords loaded — scroll down to analyze "${trend.title}"`);
	}

	async function addDiscoveredTrendToTopics(trend: TrendSuggestion) {
		addingDiscoveredTrend = trend.title;
		try {
			const newTopic = await apiClient.createSeoTopic({
				keyword: trend.title,
				notes: trend.description
			});
			topics = [newTopic, ...topics];
			toast.success(`Added "${trend.title}" to topics`);
		} catch (err) {
			console.error('Failed to add trend as topic:', err);
			toast.error('Failed to add topic');
		} finally {
			addingDiscoveredTrend = null;
		}
	}

	function getTrendSignalBadgeVariant(signal: string): 'success' | 'warning' | 'neutral' {
		switch (signal) {
			case 'rising':
				return 'success';
			case 'emerging':
				return 'warning';
			default:
				return 'neutral';
		}
	}

	function getCompetitorPresenceBadgeVariant(
		presence: string
	): 'error' | 'warning' | 'success' | 'neutral' {
		switch (presence) {
			case 'high':
				return 'error';
			case 'medium':
				return 'warning';
			case 'low':
				return 'success';
			default:
				return 'neutral';
		}
	}

	function getSearchVolumeBadgeVariant(
		volume: string
	): 'success' | 'warning' | 'neutral' {
		switch (volume) {
			case 'high':
				return 'success';
			case 'medium':
				return 'warning';
			default:
				return 'neutral';
		}
	}

	// Track expanded sources state per suggestion
	let expandedSources = $state<Record<string, boolean>>({});

	function toggleSources(keyword: string) {
		expandedSources[keyword] = !expandedSources[keyword];
	}
</script>

<div>
	<!-- Context Setup CTA -->
	{#if contextLoaded && (!hasIndustry || !hasProductDescription)}
		<div class="mb-6">
			<Alert variant="info">
				<div class="flex items-center justify-between gap-4">
					<div>
						<p class="font-medium">Set up your business context for personalized SEO recommendations</p>
						<p class="text-sm mt-1 opacity-80">
							Adding your industry and product details helps us tailor trend analysis to your specific market.
						</p>
					</div>
					<a
						href="/context/overview"
						class="flex-shrink-0 inline-flex items-center px-4 py-2 text-sm font-medium rounded-md bg-brand-600 text-white hover:bg-brand-700 transition-colors"
					>
						Set Up Context
					</a>
				</div>
			</Alert>
		</div>
	{/if}

	<!-- Tab Navigation -->
	<div class="mb-6 border-b border-neutral-200 dark:border-neutral-700">
		<nav class="flex gap-4" aria-label="SEO Tools tabs">
			<button
				type="button"
				class="px-1 py-3 text-sm font-medium border-b-2 transition-colors {activeTab === 'research'
					? 'border-brand-500 text-brand-600 dark:text-brand-400'
					: 'border-transparent text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 hover:border-neutral-300 dark:hover:border-neutral-600'}"
				onclick={() => (activeTab = 'research')}
			>
				Research
			</button>
			<button
				type="button"
				class="px-1 py-3 text-sm font-medium border-b-2 transition-colors {activeTab === 'content'
					? 'border-brand-500 text-brand-600 dark:text-brand-400'
					: 'border-transparent text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 hover:border-neutral-300 dark:hover:border-neutral-600'}"
				onclick={() => (activeTab = 'content')}
			>
				Content{topics.length > 0 || articles.length > 0
					? ` (${topics.length} topic${topics.length !== 1 ? 's' : ''}, ${articles.length} article${articles.length !== 1 ? 's' : ''})`
					: ''}
			</button>
		</nav>
	</div>

	<!-- Tab Content -->
	<div class="space-y-6">
		{#if activeTab === 'research'}
			<!-- Research Tab: Discover + Analyze -->

			<!-- Discover Trends Card -->
			<BoCard>
				{#snippet header()}
					<div class="flex items-center justify-between">
						<div>
							<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
								Discover Trends
							</h2>
							<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
								AI-suggested trending topics based on your business context
							</p>
						</div>
						<BoButton
							variant="brand"
							size="sm"
							onclick={discoverTrends}
							loading={discoverLoading}
							disabled={discoverLoading || !hasIndustry}
						>
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
							{discoverLoading ? 'Discovering...' : 'Discover Trends'}
						</BoButton>
					</div>
				{/snippet}

				{#if !hasIndustry && contextLoaded}
					<Alert variant="info">
						<div class="flex items-center justify-between gap-4">
							<span class="text-sm">Set your industry in business context to enable trend discovery.</span>
							<a
								href="/context/overview"
								class="flex-shrink-0 text-sm font-medium text-brand-600 dark:text-brand-400 hover:underline"
							>
								Set Up Context
							</a>
						</div>
					</Alert>
				{:else if discoverLoading}
					<div class="space-y-3">
						<ShimmerSkeleton type="text" />
						<ShimmerSkeleton type="text" />
						<ShimmerSkeleton type="text" />
					</div>
				{:else if discoverError === 'no_context'}
					<Alert variant="warning">
						<div class="flex items-center justify-between gap-4">
							<span class="text-sm">Please set your industry in business context first.</span>
							<a
								href="/context/overview"
								class="flex-shrink-0 text-sm font-medium text-brand-600 dark:text-brand-400 hover:underline"
							>
								Set Up Context
							</a>
						</div>
					</Alert>
				{:else if discoverError}
					<Alert variant="error">{discoverError}</Alert>
				{:else if discoveredTrends.length > 0}
					<div class="space-y-3">
						{#each discoveredTrends as trend (trend.title)}
							<div class="p-4 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg border border-neutral-200 dark:border-neutral-700">
								<div class="flex items-start justify-between gap-3">
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2 flex-wrap">
											<span class="font-medium text-neutral-900 dark:text-white">
												{trend.title}
											</span>
											<Badge variant={getTrendSignalBadgeVariant(trend.trend_signal)}>
												{trend.trend_signal}
											</Badge>
										</div>
										<p class="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
											{trend.description}
										</p>
										<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-500 italic">
											{trend.relevance_to_business}
										</p>
										{#if trend.suggested_keywords.length > 0}
											<div class="mt-2 flex flex-wrap gap-1">
												{#each trend.suggested_keywords as kw}
													<span class="px-2 py-0.5 text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 rounded">
														{kw}
													</span>
												{/each}
											</div>
										{/if}
									</div>
									<div class="flex flex-col gap-1 flex-shrink-0">
										<BoButton
											variant="outline"
											size="sm"
											onclick={() => useForAnalysis(trend)}
										>
											Analyze
										</BoButton>
										{#if isTopicAdded(trend.title)}
											<Badge variant="neutral">Added</Badge>
										{:else}
											<BoButton
												variant="ghost"
												size="sm"
												onclick={() => addDiscoveredTrendToTopics(trend)}
												loading={addingDiscoveredTrend === trend.title}
												disabled={addingDiscoveredTrend !== null}
											>
												<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
												</svg>
												Add to Topics
											</BoButton>
										{/if}
									</div>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="text-center py-6">
						<div class="mx-auto h-10 w-10 text-neutral-400 dark:text-neutral-600 mb-3">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
						</div>
						<p class="text-sm text-neutral-500 dark:text-neutral-400">
							Click "Discover Trends" to find trending topics for your business
						</p>
					</div>
				{/if}
			</BoCard>

			<!-- Input Form -->
			<BoCard>
				{#snippet header()}
					<div class="flex items-center justify-between">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Analyze Trends
						</h2>
						<div class="flex items-center gap-3">
							<!-- History Dropdown -->
							<div class="relative">
								<BoButton
									variant="ghost"
									size="sm"
									onclick={() => (historyDropdownOpen = !historyDropdownOpen)}
									disabled={historyLoading || history.length === 0}
								>
									<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
									Load from history
								</BoButton>
								{#if historyDropdownOpen && history.length > 0}
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<!-- svelte-ignore a11y_click_events_have_key_events -->
									<div
										class="fixed inset-0 z-40"
										onclick={() => (historyDropdownOpen = false)}
									></div>
									<div class="absolute right-0 top-full mt-1 w-72 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 z-50 max-h-64 overflow-y-auto">
										{#each history as entry (entry.id)}
											<button
												type="button"
												class="w-full text-left px-4 py-3 hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors first:rounded-t-lg last:rounded-b-lg"
												onclick={() => {
													loadFromHistory(entry);
													historyDropdownOpen = false;
												}}
											>
												<div class="font-medium text-sm text-neutral-900 dark:text-white truncate">
													{entry.keywords.join(', ')}
												</div>
												{#if entry.industry}
													<div class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
														{entry.industry}
													</div>
												{/if}
												<div class="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">
													{new Date(entry.created_at).toLocaleDateString()}
												</div>
											</button>
										{/each}
									</div>
								{/if}
							</div>
							{#if remaining !== -1}
								<Badge variant="neutral">
									{remaining} analyses remaining
								</Badge>
							{:else}
								<Badge variant="success">Unlimited</Badge>
							{/if}
						</div>
					</div>
				{/snippet}

				<div class="space-y-4">
					<BoFormField
						label="Keywords"
						description="Enter up to 10 keywords, separated by commas"
						error={error && error.includes('keyword') ? error : undefined}
					>
						<input
							type="text"
							bind:value={keywords}
							placeholder="e.g., project management, task tracking, team collaboration"
							class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
							disabled={loading}
						/>
					</BoFormField>

					<BoFormField label="Industry (optional)" description="Your business industry for context">
						<input
							type="text"
							bind:value={industry}
							placeholder="e.g., SaaS, E-commerce, Fintech"
							class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
							disabled={loading}
						/>
					</BoFormField>

					{#if error && !error.includes('keyword')}
						{#if isQuotaError}
							<Alert variant="warning">
								<div class="flex flex-col gap-2">
									<span>{error}</span>
									<a
										href="/settings/subscription"
										class="inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 dark:text-brand-400 hover:underline"
									>
										Upgrade your plan
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
										</svg>
									</a>
								</div>
							</Alert>
						{:else}
							<Alert variant="error">{error}</Alert>
						{/if}
					{/if}

					<div class="flex justify-end">
						<BoButton
							variant="brand"
							onclick={analyzeTrends}
							disabled={loading || !keywords.trim()}
							{loading}
						>
							{loading ? 'Analyzing...' : 'Analyze Trends'}
						</BoButton>
					</div>
				</div>
			</BoCard>

			<!-- Analysis Results -->
			{#if loading}
				<BoCard>
					<div class="space-y-4">
						<ShimmerSkeleton type="text" />
						<ShimmerSkeleton type="text" />
						<ShimmerSkeleton type="text" />
					</div>
				</BoCard>
			{:else if analysis}
				<BoCard>
					{#snippet header()}
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Analysis Results
						</h2>
					{/snippet}

					<div class="space-y-6">
						<!-- Executive Summary -->
						<div>
							<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
								Executive Summary
							</h3>
							<p class="text-neutral-600 dark:text-neutral-400">
								{analysis.results.executive_summary}
							</p>
						</div>

						<!-- Key Trends -->
						{#if analysis.results.key_trends.length > 0}
							<div>
								<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
									Key Trends
								</h3>
								<ul class="space-y-2">
									{#each analysis.results.key_trends as trend}
										<li
											class="p-3 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg text-sm text-neutral-600 dark:text-neutral-400"
										>
											{trend}
										</li>
									{/each}
								</ul>
							</div>
						{/if}

						<!-- Opportunities -->
						{#if analysis.results.opportunities.length > 0}
							<div>
								<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
									Opportunities
								</h3>
								<div class="space-y-3">
									{#each analysis.results.opportunities as opp}
										<div class="p-3 bg-success-50 dark:bg-success-900/20 rounded-lg border border-success-200 dark:border-success-800">
											<div class="flex items-center justify-between mb-1">
												<span class="font-medium text-neutral-900 dark:text-white">
													{opp.topic}
												</span>
												<div class="flex items-center gap-2">
													<Badge variant={getTrendBadgeVariant(opp.trend_direction)}>
														{opp.trend_direction}
													</Badge>
													{#if isTopicAdded(opp.topic)}
														<Badge variant="neutral">Added</Badge>
													{:else}
														<BoButton
															variant="ghost"
															size="sm"
															onclick={() => addToTopics(opp)}
															loading={addingTopic === opp.topic}
															disabled={addingTopic !== null}
														>
															Add to Topics
														</BoButton>
													{/if}
												</div>
											</div>
											<p class="text-sm text-neutral-600 dark:text-neutral-400">
												{opp.description}
											</p>
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Threats -->
						{#if analysis.results.threats.length > 0}
							<div>
								<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
									Threats
								</h3>
								<div class="space-y-3">
									{#each analysis.results.threats as threat}
										<div class="p-3 bg-error-50 dark:bg-error-900/20 rounded-lg border border-error-200 dark:border-error-800">
											<div class="flex items-center justify-between mb-1">
												<span class="font-medium text-neutral-900 dark:text-white">
													{threat.topic}
												</span>
												<Badge variant={getSeverityBadgeVariant(threat.severity)}>
													{threat.severity}
												</Badge>
											</div>
											<p class="text-sm text-neutral-600 dark:text-neutral-400">
												{threat.description}
											</p>
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Sources -->
						{#if analysis.results.sources.length > 0}
							<div>
								<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
									Sources
								</h3>
								<ul class="text-sm text-neutral-500 dark:text-neutral-500 space-y-1">
									{#each analysis.results.sources as source}
										<li class="truncate">{source}</li>
									{/each}
								</ul>
							</div>
						{/if}
					</div>
				</BoCard>
			{:else}
				<BoCard>
					<div class="text-center py-8">
						<div class="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-600 mb-4">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
							</svg>
						</div>
						<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-1">
							No analysis yet
						</h3>
						<p class="text-neutral-500 dark:text-neutral-400">
							Enter keywords above to analyze SEO trends
						</p>
					</div>
				</BoCard>
			{/if}
		{:else}
			<!-- Content Tab: Topics + Articles -->
			<!-- Topics Table -->
			<BoCard>
				{#snippet header()}
					<div class="flex items-center justify-between">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Your Topics
						</h2>
						<BoButton
							variant="outline"
							size="sm"
							onclick={autogenerateTopics}
							loading={autogeneratingTopics}
							disabled={autogeneratingTopics || topicsLoading}
						>
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
							</svg>
							{autogeneratingTopics ? 'Generating...' : 'Autogenerate Topics'}
						</BoButton>
					</div>
				{/snippet}

				<!-- Manual Topic Form -->
				<div class="mb-4 p-4 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
					<form onsubmit={(e) => { e.preventDefault(); addManualTopic(); }} class="flex flex-col gap-3">
						<div class="flex flex-col sm:flex-row gap-3">
							<div class="flex-1">
								<input
									type="text"
									bind:value={newTopicKeyword}
									placeholder="Enter keyword(s), comma-separated..."
									class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm"
									disabled={addingManualTopic || analyzingTopics}
								/>
							</div>
							<div class="flex-1">
								<input
									type="text"
									bind:value={newTopicNotes}
									placeholder="Notes (optional)"
									class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm"
									disabled={addingManualTopic || analyzingTopics}
								/>
							</div>
							<div class="flex gap-2">
								<BoButton
									type="button"
									variant="outline"
									size="sm"
									onclick={analyzeTopicIdeas}
									loading={analyzingTopics}
									disabled={analyzingTopics || addingManualTopic || !newTopicKeyword.trim()}
								>
									<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
									</svg>
									{analyzingTopics ? 'Analyzing...' : 'Analyze'}
								</BoButton>
								<BoButton
									type="submit"
									variant="brand"
									size="sm"
									loading={addingManualTopic}
									disabled={addingManualTopic || analyzingTopics || !newTopicKeyword.trim()}
								>
									Add Topic
								</BoButton>
							</div>
						</div>
						<div class="flex items-center gap-2">
							<label class="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400 cursor-pointer">
								<input
									type="checkbox"
									bind:checked={skipValidation}
									class="rounded border-neutral-300 dark:border-neutral-600 text-brand-600 focus:ring-brand-500 dark:bg-neutral-700"
									disabled={analyzingTopics}
								/>
								Skip validation (faster)
							</label>
							<span class="text-xs text-neutral-400 dark:text-neutral-500">
								Validation checks competitor presence and search volume
							</span>
						</div>
					</form>
				</div>

				<!-- Topic Suggestions Panel -->
				{#if topicSuggestions.length > 0}
					<div class="mb-4 p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-800">
						<div class="flex items-center justify-between mb-3">
							<h3 class="text-sm font-medium text-brand-900 dark:text-brand-100">
								Topic Suggestions
							</h3>
							<button
								type="button"
								class="text-brand-600 dark:text-brand-400 hover:text-brand-800 dark:hover:text-brand-200 text-sm"
								onclick={clearSuggestions}
							>
								Clear
							</button>
						</div>
						<div class="space-y-3">
							{#each topicSuggestions as suggestion (suggestion.keyword)}
								<div class="p-3 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
									<div class="flex items-start justify-between gap-3">
										<div class="flex-1 min-w-0">
											<div class="flex items-center gap-2 flex-wrap">
												<span class="font-medium text-neutral-900 dark:text-white">
													{suggestion.keyword}
												</span>
												{#if suggestion.validation_status === 'validated'}
													<span title="Validated via web research" class="inline-flex items-center text-success-600 dark:text-success-400">
														<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
															<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
														</svg>
													</span>
												{/if}
												<Badge variant={getSeoPotentalBadgeVariant(suggestion.seo_potential)}>
													{suggestion.seo_potential} SEO
												</Badge>
												<Badge variant={getTrendStatusBadgeVariant(suggestion.trend_status)}>
													{suggestion.trend_status}
												</Badge>
											</div>
											<!-- Validation indicators -->
											{#if suggestion.validation_status === 'validated'}
												<div class="mt-2 flex items-center gap-3 text-xs">
													{#if suggestion.search_volume_indicator !== 'unknown'}
														<span class="flex items-center gap-1">
															<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
															</svg>
															<Badge variant={getSearchVolumeBadgeVariant(suggestion.search_volume_indicator)} size="sm">
																{suggestion.search_volume_indicator} volume
															</Badge>
														</span>
													{/if}
													{#if suggestion.competitor_presence !== 'unknown'}
														<span class="flex items-center gap-1">
															<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
															</svg>
															<Badge variant={getCompetitorPresenceBadgeVariant(suggestion.competitor_presence)} size="sm">
																{suggestion.competitor_presence} competition
															</Badge>
														</span>
													{/if}
												</div>
											{/if}
											<p class="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
												{suggestion.description}
											</p>
											{#if suggestion.related_keywords.length > 0}
												<div class="mt-2 flex flex-wrap gap-1">
													{#each suggestion.related_keywords as kw}
														<span class="px-2 py-0.5 text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 rounded">
															{kw}
														</span>
													{/each}
												</div>
											{/if}
											<!-- Validation sources (collapsible) -->
											{#if suggestion.validation_sources && suggestion.validation_sources.length > 0}
												<div class="mt-2">
													<button
														type="button"
														class="text-xs text-brand-600 dark:text-brand-400 hover:text-brand-800 dark:hover:text-brand-200 flex items-center gap-1"
														onclick={() => toggleSources(suggestion.keyword)}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															class="h-3 w-3 transition-transform {expandedSources[suggestion.keyword] ? 'rotate-90' : ''}"
															fill="none"
															viewBox="0 0 24 24"
															stroke="currentColor"
														>
															<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
														</svg>
														{suggestion.validation_sources.length} source{suggestion.validation_sources.length !== 1 ? 's' : ''}
													</button>
													{#if expandedSources[suggestion.keyword]}
														<ul class="mt-1 space-y-1 text-xs text-neutral-500 dark:text-neutral-400">
															{#each suggestion.validation_sources as source}
																<li class="truncate">
																	{#if source.includes(' - ')}
																		{@const [title, url] = source.split(' - ')}
																		<a
																			href={url}
																			target="_blank"
																			rel="noopener noreferrer"
																			class="hover:text-brand-600 dark:hover:text-brand-400 hover:underline"
																		>
																			{title}
																		</a>
																	{:else}
																		{source}
																	{/if}
																</li>
															{/each}
														</ul>
													{/if}
												</div>
											{/if}
										</div>
										<div class="flex-shrink-0">
											{#if isTopicAdded(suggestion.keyword)}
												<Badge variant="neutral">Added</Badge>
											{:else}
												<BoButton
													variant="ghost"
													size="sm"
													onclick={() => addSuggestionToTopics(suggestion)}
													loading={addingSuggestion === suggestion.keyword}
													disabled={addingSuggestion !== null}
												>
													<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
													</svg>
													Add
												</BoButton>
											{/if}
										</div>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				{#if topicsLoading}
					<div class="space-y-3">
						<ShimmerSkeleton type="text" />
						<ShimmerSkeleton type="text" />
						<ShimmerSkeleton type="text" />
					</div>
				{:else if topics.length === 0}
					<div class="text-center py-8">
						<div class="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-600 mb-4">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
							</svg>
						</div>
						<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-1">
							No topics yet
						</h3>
						<p class="text-neutral-500 dark:text-neutral-400">
							Run an analysis and add opportunities to your topics list
						</p>
					</div>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full">
							<thead>
								<tr class="border-b border-neutral-200 dark:border-neutral-700">
									<th class="text-left py-3 px-4 text-sm font-medium text-neutral-700 dark:text-neutral-300">Keyword</th>
									<th class="text-left py-3 px-4 text-sm font-medium text-neutral-700 dark:text-neutral-300">Status</th>
									<th class="text-left py-3 px-4 text-sm font-medium text-neutral-700 dark:text-neutral-300">Notes</th>
									<th class="text-left py-3 px-4 text-sm font-medium text-neutral-700 dark:text-neutral-300">Added</th>
									<th class="text-right py-3 px-4 text-sm font-medium text-neutral-700 dark:text-neutral-300">Actions</th>
								</tr>
							</thead>
							<tbody>
								{#each topics as topic (topic.id)}
									<tr class="border-b border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
										<td class="py-3 px-4">
											<span class="font-medium text-neutral-900 dark:text-white">{topic.keyword}</span>
										</td>
										<td class="py-3 px-4">
											<Badge variant={getStatusBadgeVariant(topic.status)}>
												{topic.status}
											</Badge>
										</td>
										<td class="py-3 px-4">
											<span class="text-sm text-neutral-600 dark:text-neutral-400 line-clamp-2">
												{topic.notes || '-'}
											</span>
										</td>
										<td class="py-3 px-4">
											<span class="text-sm text-neutral-500 dark:text-neutral-500">
												{new Date(topic.created_at).toLocaleDateString()}
											</span>
										</td>
										<td class="py-3 px-4 text-right">
											<div class="flex items-center justify-end gap-2">
												{#if hasArticleForTopic(topic.id)}
													<Badge variant="neutral">Has Article</Badge>
												{:else}
													<BoButton
														variant="outline"
														size="sm"
														onclick={() => generateArticle(topic)}
														loading={generatingArticle === topic.id}
														disabled={generatingArticle !== null || (articlesRemaining === 0)}
													>
														Generate Article
													</BoButton>
												{/if}
												<BoButton
													variant="ghost"
													size="sm"
													onclick={() => deleteTopic(topic)}
													loading={deletingTopic === topic.id}
													disabled={deletingTopic !== null}
												>
													<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
													</svg>
												</BoButton>
											</div>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</BoCard>

			<!-- Generated Articles -->
			<BoCard>
				{#snippet header()}
					<div class="flex items-center justify-between">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Generated Articles
						</h2>
						{#if articlesRemaining !== -1}
							<Badge variant="neutral">
								{articlesRemaining} generations remaining
							</Badge>
						{:else}
							<Badge variant="success">Unlimited</Badge>
						{/if}
					</div>
				{/snippet}

				{#if articlesLoading}
					<div class="space-y-3">
						<ShimmerSkeleton type="text" />
						<ShimmerSkeleton type="text" />
						<ShimmerSkeleton type="text" />
					</div>
				{:else if articles.length === 0}
					<div class="text-center py-8">
						<div class="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-600 mb-4">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 7.5h1.5m-1.5 3h1.5m-7.5 3h7.5m-7.5 3h7.5m3-9h3.375c.621 0 1.125.504 1.125 1.125V18a2.25 2.25 0 01-2.25 2.25M16.5 7.5V18a2.25 2.25 0 002.25 2.25M16.5 7.5V4.875c0-.621-.504-1.125-1.125-1.125H4.125C3.504 3.75 3 4.254 3 4.875V18a2.25 2.25 0 002.25 2.25h13.5M6 7.5h3v3H6v-3z" />
							</svg>
						</div>
						<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-1">
							No articles yet
						</h3>
						<p class="text-neutral-500 dark:text-neutral-400">
							Generate articles from your topics to see them here
						</p>
					</div>
				{:else}
					<div class="space-y-4">
						{#each articles as article (article.id)}
							<button
								type="button"
								class="w-full text-left p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800/50 hover:border-brand-300 dark:hover:border-brand-700 transition-colors cursor-pointer"
								onclick={() => openArticleModal(article)}
							>
								<div class="flex items-start justify-between gap-4">
									<div class="flex-1 min-w-0">
										<h3 class="font-medium text-neutral-900 dark:text-white truncate">
											{article.title}
										</h3>
										{#if article.excerpt}
											<p class="mt-1 text-sm text-neutral-600 dark:text-neutral-400 line-clamp-2">
												{article.excerpt}
											</p>
										{/if}
										<div class="mt-2 flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-500">
											<Badge variant={getArticleStatusBadgeVariant(article.status)}>
												{article.status}
											</Badge>
											<span>{new Date(article.created_at).toLocaleDateString()}</span>
											<span>{article.content.length.toLocaleString()} chars</span>
										</div>
									</div>
									<div class="flex items-center gap-2 flex-shrink-0">
										<BoButton
											variant="ghost"
											size="sm"
											onclick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(article.content).then(() => toast.success('Content copied!')); }}
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
											</svg>
										</BoButton>
										<BoButton
											variant="ghost"
											size="sm"
											onclick={(e) => { e.stopPropagation(); deleteArticle(article); }}
											loading={deletingArticle === article.id}
											disabled={deletingArticle !== null}
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
											</svg>
										</BoButton>
									</div>
								</div>
							</button>
						{/each}
					</div>
				{/if}
			</BoCard>
		{/if}
	</div>
</div>

<!-- Article Detail Modal -->
{#if selectedArticle}
	<ArticleDetailModal
		article={selectedArticle}
		open={selectedArticle !== null}
		defaultTone={brandTone}
		onclose={closeArticleModal}
		onupdate={handleArticleUpdate}
	/>
{/if}
