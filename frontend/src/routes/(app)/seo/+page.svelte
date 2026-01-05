<script lang="ts">
	/**
	 * SEO Trend Analyzer Page
	 *
	 * Analyze SEO trends for keywords/industry using AI-powered research.
	 * Manage topics for blog generation workflow.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type {
		SeoTrendAnalysisResponse,
		SeoHistoryEntry,
		SeoTrendOpportunity,
		SeoTopic,
		SeoBlogArticle,
		SeoAutopilotConfig,
		SeoAutopilotConfigResponse,
		SeoPendingArticle
	} from '$lib/api/types';
		import BoCard from '$lib/components/ui/BoCard.svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import BoFormField from '$lib/components/ui/BoFormField.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import ShimmerSkeleton from '$lib/components/ui/loading/ShimmerSkeleton.svelte';
	import ArticleDetailModal from '$lib/components/seo/ArticleDetailModal.svelte';
	import { toast } from '$lib/stores/toast';

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
	let addingTopic = $state<string | null>(null);
	let deletingTopic = $state<number | null>(null);

	// Manual topic form state
	let newTopicKeyword = $state('');
	let newTopicNotes = $state('');
	let addingManualTopic = $state(false);

	// Autogenerate state
	let autogeneratingTopics = $state(false);
	let articles = $state<SeoBlogArticle[]>([]);
	let articlesLoading = $state(true);
	let articlesRemaining = $state<number>(-1);
	let generatingArticle = $state<number | null>(null);
	let deletingArticle = $state<number | null>(null);

	// Autopilot state
	let autopilotConfig = $state<SeoAutopilotConfigResponse | null>(null);
	let autopilotLoading = $state(true);
	let autopilotSaving = $state(false);
	let pendingArticles = $state<SeoPendingArticle[]>([]);
	let approvingArticle = $state<number | null>(null);
	let rejectingArticle = $state<number | null>(null);

	// Article detail modal state
	let selectedArticle = $state<SeoBlogArticle | null>(null);
	let brandTone = $state<string | null>(null);

	// Context state for CTA
	let contextLoaded = $state(false);
	let hasIndustry = $state(false);
	let hasProductDescription = $state(false);

	// Load history, topics, articles, autopilot config, and brand tone on mount
	onMount(async () => {
		await Promise.all([loadHistory(), loadTopics(), loadArticles(), loadAutopilotConfig(), loadBrandTone()]);
	});

	async function loadBrandTone() {
		try {
			const response = await apiClient.getUserContext();
			brandTone = response.context?.brand_tone || null;
			hasIndustry = !!response.context?.industry;
			hasProductDescription = !!response.context?.product_description;
		} catch (err) {
			// Fallback to Professional if context not available
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

	async function loadAutopilotConfig() {
		autopilotLoading = true;
		try {
			const response = await apiClient.getSeoAutopilotConfig();
			autopilotConfig = response;
			if (response.articles_pending_review > 0) {
				const pendingResp = await apiClient.getSeoPendingArticles();
				pendingArticles = pendingResp.articles;
			}
		} catch (err) {
			console.error('Failed to load autopilot config:', err);
		} finally {
			autopilotLoading = false;
		}
	}

	async function toggleAutopilot() {
		if (!autopilotConfig) return;
		autopilotSaving = true;
		try {
			const newEnabled = !autopilotConfig.config.enabled;
			const response = await apiClient.updateSeoAutopilotConfig({
				...autopilotConfig.config,
				enabled: newEnabled
			});
			autopilotConfig = response;
			toast.success(newEnabled ? 'Autopilot enabled' : 'Autopilot disabled');
		} catch (err) {
			console.error('Failed to toggle autopilot:', err);
			toast.error('Failed to update autopilot');
		} finally {
			autopilotSaving = false;
		}
	}

	async function updateAutopilotFrequency(freq: number) {
		if (!autopilotConfig) return;
		autopilotSaving = true;
		try {
			const response = await apiClient.updateSeoAutopilotConfig({
				...autopilotConfig.config,
				frequency_per_week: freq
			});
			autopilotConfig = response;
			toast.success('Frequency updated');
		} catch (err) {
			console.error('Failed to update frequency:', err);
			toast.error('Failed to update frequency');
		} finally {
			autopilotSaving = false;
		}
	}

	async function approveArticle(articleId: number) {
		approvingArticle = articleId;
		try {
			const approved = await apiClient.approveSeoArticle(articleId);
			pendingArticles = pendingArticles.filter((a) => a.id !== articleId);
			articles = [approved, ...articles];
			if (autopilotConfig) {
				autopilotConfig = {
					...autopilotConfig,
					articles_pending_review: autopilotConfig.articles_pending_review - 1
				};
			}
			toast.success('Article published');
		} catch (err) {
			console.error('Failed to approve article:', err);
			toast.error('Failed to approve article');
		} finally {
			approvingArticle = null;
		}
	}

	async function rejectArticle(articleId: number) {
		rejectingArticle = articleId;
		try {
			await apiClient.rejectSeoArticle(articleId);
			pendingArticles = pendingArticles.filter((a) => a.id !== articleId);
			if (autopilotConfig) {
				autopilotConfig = {
					...autopilotConfig,
					articles_pending_review: autopilotConfig.articles_pending_review - 1
				};
			}
			toast.success('Article rejected');
		} catch (err) {
			console.error('Failed to reject article:', err);
			toast.error('Failed to reject article');
		} finally {
			rejectingArticle = null;
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
			if (err && typeof err === 'object' && 'message' in err) {
				error = (err as { message: string }).message;
			} else {
				error = 'Failed to analyze trends. Please try again.';
			}
			toast.error('Analysis failed');
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
			// Update topic status locally
			topics = topics.map((t) => (t.id === topic.id ? { ...t, status: 'writing' as const } : t));
			toast.success(`Article generated for "${topic.keyword}"`);
			// Reload to get updated remaining count
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
</script>

<svelte:head>
	<title>SEO Trend Analyzer | Board of One</title>
	<meta
		name="description"
		content="Analyze SEO trends for your industry and keywords with AI-powered research"
	/>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
	<!-- Page Header -->
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">SEO Trend Analyzer</h1>
		<p class="mt-1 text-neutral-600 dark:text-neutral-400">
			Analyze search trends and discover opportunities for your business.
		</p>
	</div>

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

	<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
		<!-- Main Analysis Area -->
		<div class="lg:col-span-2 space-y-6">
			<!-- Input Form -->
			<BoCard>
				{#snippet header()}
					<div class="flex items-center justify-between">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Analyze Trends
						</h2>
						{#if remaining !== -1}
							<Badge variant="neutral">
								{remaining} analyses remaining
							</Badge>
						{:else}
							<Badge variant="success">Unlimited</Badge>
						{/if}
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
						<Alert variant="error">{error}</Alert>
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
						<div
							class="mx-auto h-12 w-12 text-neutral-400 dark:text-neutral-600 mb-4"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941"
								/>
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
					<form onsubmit={(e) => { e.preventDefault(); addManualTopic(); }} class="flex flex-col sm:flex-row gap-3">
						<div class="flex-1">
							<input
								type="text"
								bind:value={newTopicKeyword}
								placeholder="Enter keyword or topic..."
								class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm"
								disabled={addingManualTopic}
							/>
						</div>
						<div class="flex-1">
							<input
								type="text"
								bind:value={newTopicNotes}
								placeholder="Notes (optional)"
								class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm"
								disabled={addingManualTopic}
							/>
						</div>
						<BoButton
							type="submit"
							variant="brand"
							size="sm"
							loading={addingManualTopic}
							disabled={addingManualTopic || !newTopicKeyword.trim()}
						>
							Add Topic
						</BoButton>
					</form>
				</div>

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
		</div>

		<!-- Sidebar -->
		<div class="lg:col-span-1 space-y-6">
			<!-- Autopilot Settings -->
			<BoCard>
				{#snippet header()}
					<div class="flex items-center justify-between">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Autopilot
						</h2>
						{#if autopilotConfig?.config.enabled}
							<Badge variant="success">Active</Badge>
						{:else}
							<Badge variant="neutral">Off</Badge>
						{/if}
					</div>
				{/snippet}

				{#if autopilotLoading}
					<div class="space-y-3">
						<ShimmerSkeleton type="text" />
						<ShimmerSkeleton type="text" />
					</div>
				{:else if autopilotConfig}
					<div class="space-y-4">
						<p class="text-sm text-neutral-600 dark:text-neutral-400">
							Auto-generate SEO articles from high-intent topics.
						</p>

						<!-- Toggle -->
						<div class="flex items-center justify-between">
							<span id="autopilot-toggle-label" class="text-sm text-neutral-700 dark:text-neutral-300">Enable autopilot</span>
							<button
								type="button"
								role="switch"
								aria-checked={autopilotConfig.config.enabled}
								aria-labelledby="autopilot-toggle-label"
								class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 {autopilotConfig.config.enabled ? 'bg-brand-600' : 'bg-neutral-200 dark:bg-neutral-700'}"
								onclick={toggleAutopilot}
								disabled={autopilotSaving}
							>
								<span
									class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out {autopilotConfig.config.enabled ? 'translate-x-5' : 'translate-x-0'}"
								></span>
							</button>
						</div>

						<!-- Frequency -->
						{#if autopilotConfig.config.enabled}
							<div class="space-y-2">
								<label class="text-sm text-neutral-700 dark:text-neutral-300">Articles per week</label>
								<select
									class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
									onchange={(e) => updateAutopilotFrequency(Number(e.currentTarget.value))}
									disabled={autopilotSaving}
								>
									{#each [1, 2, 3, 5, 7] as freq}
										<option value={freq} selected={autopilotConfig.config.frequency_per_week === freq}>
											{freq} article{freq > 1 ? 's' : ''}/week
										</option>
									{/each}
								</select>
							</div>

							<!-- Stats -->
							<div class="pt-2 border-t border-neutral-200 dark:border-neutral-700 text-sm text-neutral-600 dark:text-neutral-400">
								<div class="flex justify-between mb-1">
									<span>This week:</span>
									<span class="font-medium">{autopilotConfig.articles_this_week} articles</span>
								</div>
								{#if autopilotConfig.next_run}
									<div class="flex justify-between">
										<span>Next run:</span>
										<span class="font-medium">{new Date(autopilotConfig.next_run).toLocaleDateString()}</span>
									</div>
								{/if}
							</div>
						{/if}
					</div>
				{/if}
			</BoCard>

			<!-- Pending Review Queue -->
			{#if pendingArticles.length > 0}
				<BoCard>
					{#snippet header()}
						<div class="flex items-center justify-between">
							<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
								Pending Review
							</h2>
							<Badge variant="warning">{pendingArticles.length}</Badge>
						</div>
					{/snippet}

					<div class="space-y-3">
						{#each pendingArticles as article (article.id)}
							<div class="p-3 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
								<h3 class="text-sm font-medium text-neutral-900 dark:text-white truncate">
									{article.title}
								</h3>
								{#if article.keyword}
									<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
										Keyword: {article.keyword}
									</p>
								{/if}
								<div class="flex gap-2 mt-2">
									<BoButton
										variant="brand"
										size="sm"
										onclick={() => approveArticle(article.id)}
										loading={approvingArticle === article.id}
										disabled={approvingArticle !== null || rejectingArticle !== null}
									>
										Approve
									</BoButton>
									<BoButton
										variant="ghost"
										size="sm"
										onclick={() => rejectArticle(article.id)}
										loading={rejectingArticle === article.id}
										disabled={approvingArticle !== null || rejectingArticle !== null}
									>
										Reject
									</BoButton>
								</div>
							</div>
						{/each}
					</div>
				</BoCard>
			{/if}

			<!-- Recent Analyses -->
			<BoCard>
				{#snippet header()}
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
						Recent Analyses
					</h2>
				{/snippet}

				{#if historyLoading}
					<div class="space-y-3">
						<ShimmerSkeleton type="text" />
						<ShimmerSkeleton type="text" />
						<ShimmerSkeleton type="text" />
					</div>
				{:else if history.length === 0}
					<p class="text-sm text-neutral-500 dark:text-neutral-400 text-center py-4">
						No previous analyses
					</p>
				{:else}
					<div class="space-y-3">
						{#each history as entry}
							<button
								type="button"
								class="w-full text-left p-3 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors"
								onclick={() => loadFromHistory(entry)}
							>
								<div class="font-medium text-sm text-neutral-900 dark:text-white truncate">
									{entry.keywords.join(', ')}
								</div>
								{#if entry.industry}
									<div class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
										{entry.industry}
									</div>
								{/if}
								<div class="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
									{new Date(entry.created_at).toLocaleDateString()}
								</div>
							</button>
						{/each}
					</div>
				{/if}
			</BoCard>

			<!-- Tips -->
			<div class="p-4 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
				<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Tips</h3>
				<ul class="text-sm text-neutral-600 dark:text-neutral-400 space-y-1">
					<li>Use specific, targeted keywords</li>
					<li>Add your industry for better context</li>
					<li>Research competitors' top keywords</li>
					<li>Analyze seasonal trends regularly</li>
				</ul>
			</div>
		</div>
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
