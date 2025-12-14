<script lang="ts">
	/**
	 * BlogGenerateModal - AI-powered blog post generation
	 */
	import { Button, Alert } from '$lib/components/ui';
	import { X, Sparkles, Lightbulb, RefreshCw } from 'lucide-svelte';
	import { adminApi, type BlogPost, type Topic } from '$lib/api/admin';

	interface Props {
		onclose: () => void;
		ongenerated: (post: BlogPost) => void;
	}

	let { onclose, ongenerated }: Props = $props();

	// Form state
	let topic = $state('');
	let keywords = $state('');
	let industry = $state('');

	// UI state
	let isGenerating = $state(false);
	let isDiscovering = $state(false);
	let error = $state<string | null>(null);
	let suggestions = $state<Topic[]>([]);
	let activeTab = $state<'manual' | 'discover'>('manual');

	async function discoverTopics() {
		isDiscovering = true;
		error = null;
		try {
			const response = await adminApi.discoverTopics(industry || undefined);
			suggestions = response.topics;
		} catch (err: unknown) {
			if (err && typeof err === 'object' && 'message' in err) {
				error = (err as { message: string }).message;
			} else {
				error = 'Failed to discover topics';
			}
		} finally {
			isDiscovering = false;
		}
	}

	function selectTopic(t: Topic) {
		topic = t.title;
		keywords = t.keywords.join(', ');
		activeTab = 'manual';
	}

	async function handleGenerate(e: Event) {
		e.preventDefault();
		error = null;

		if (!topic.trim()) {
			error = 'Please enter a topic';
			return;
		}

		isGenerating = true;
		try {
			const keywordList = keywords
				.split(',')
				.map((k) => k.trim())
				.filter(Boolean);

			const response = await adminApi.generateBlogPost(
				{
					topic: topic.trim(),
					keywords: keywordList.length > 0 ? keywordList : undefined
				},
				true // save as draft
			);

			if (response.post_id) {
				const post = await adminApi.getBlogPost(response.post_id);
				ongenerated(post);
			}
		} catch (err: unknown) {
			if (err && typeof err === 'object' && 'message' in err) {
				error = (err as { message: string }).message;
			} else {
				error = 'Failed to generate post';
			}
		} finally {
			isGenerating = false;
		}
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			onclose();
		}
	}

	function getSourceBadgeColor(source: string) {
		switch (source) {
			case 'context':
				return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
			case 'trend':
				return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
			case 'gap':
				return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
			default:
				return 'bg-neutral-100 text-neutral-600';
		}
	}
</script>

{#if true}
	<div
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
		onclick={handleBackdropClick}
		role="button"
		tabindex="-1"
	>
		<div
			class="bg-white dark:bg-neutral-800 rounded-lg w-full max-w-2xl max-h-[90vh] flex flex-col"
			onclick={(e) => e.stopPropagation()}
			role="dialog"
		>
			<!-- Header -->
			<div
				class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700"
			>
				<div class="flex items-center gap-2">
					<Sparkles class="w-5 h-5 text-purple-500" />
					<h2 class="text-xl font-semibold text-neutral-900 dark:text-white">Generate Blog Post</h2>
				</div>
				<button
					class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
					onclick={onclose}
					aria-label="Close"
				>
					<X class="w-5 h-5 text-neutral-500" />
				</button>
			</div>

			<!-- Tabs -->
			<div class="px-6 pt-4">
				<nav class="flex gap-4 border-b border-neutral-200 dark:border-neutral-700">
					<button
						class="px-1 pb-3 text-sm font-medium border-b-2 transition-colors {activeTab === 'manual'
							? 'border-brand-500 text-brand-600 dark:text-brand-400'
							: 'border-transparent text-neutral-500 hover:text-neutral-700'}"
						onclick={() => (activeTab = 'manual')}
					>
						Enter Topic
					</button>
					<button
						class="px-1 pb-3 text-sm font-medium border-b-2 transition-colors {activeTab === 'discover'
							? 'border-brand-500 text-brand-600 dark:text-brand-400'
							: 'border-transparent text-neutral-500 hover:text-neutral-700'}"
						onclick={() => (activeTab = 'discover')}
					>
						Discover Topics
					</button>
				</nav>
			</div>

			<!-- Content -->
			<div class="flex-1 overflow-y-auto p-6">
				{#if error}
					<Alert variant="error" class="mb-4">{error}</Alert>
				{/if}

				{#if activeTab === 'manual'}
					<form onsubmit={handleGenerate} class="space-y-4">
						<div>
							<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
								Topic <span class="text-red-500">*</span>
							</label>
							<input
								type="text"
								bind:value={topic}
								class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent"
								placeholder="e.g., How AI is transforming business decision-making"
								disabled={isGenerating}
							/>
							<p class="text-xs text-neutral-500 mt-1">
								Describe the topic you want to write about
							</p>
						</div>

						<div>
							<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
								Target Keywords
								<span class="text-neutral-400 font-normal">(optional, comma-separated)</span>
							</label>
							<input
								type="text"
								bind:value={keywords}
								class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent"
								placeholder="AI decisions, business strategy, data-driven"
								disabled={isGenerating}
							/>
						</div>

						<div
							class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4 flex items-start gap-3"
						>
							<Sparkles class="w-5 h-5 text-purple-500 flex-shrink-0 mt-0.5" />
							<div class="text-sm text-purple-700 dark:text-purple-300">
								<p class="font-medium mb-1">AI Generation</p>
								<p class="text-purple-600 dark:text-purple-400">
									Claude will generate a 1000-1500 word SEO-optimized blog post with proper
									headings, meta description, and excerpt. The post will be saved as a draft for
									your review.
								</p>
							</div>
						</div>
					</form>
				{:else}
					<div class="space-y-4">
						<div class="flex gap-2">
							<input
								type="text"
								bind:value={industry}
								class="flex-1 px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500"
								placeholder="Enter industry (optional)"
								disabled={isDiscovering}
							/>
							<Button
								variant="outline"
								onclick={discoverTopics}
								disabled={isDiscovering}
							>
								{#if isDiscovering}
									<RefreshCw class="w-4 h-4 mr-1.5 animate-spin" />
								{:else}
									<Lightbulb class="w-4 h-4 mr-1.5" />
								{/if}
								Discover
							</Button>
						</div>

						{#if suggestions.length > 0}
							<div class="space-y-3">
								<p class="text-sm text-neutral-500 dark:text-neutral-400">
									Click a topic to use it:
								</p>
								{#each suggestions as suggestion}
									<button
										class="w-full text-left p-4 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-brand-500 hover:bg-brand-50 dark:hover:bg-brand-900/10 transition-colors"
										onclick={() => selectTopic(suggestion)}
									>
										<div class="flex items-center gap-2 mb-1">
											<span
												class="px-2 py-0.5 rounded text-xs font-medium {getSourceBadgeColor(
													suggestion.source
												)}"
											>
												{suggestion.source}
											</span>
											<span class="text-xs text-neutral-400">
												{Math.round(suggestion.relevance_score * 100)}% relevant
											</span>
										</div>
										<h4 class="font-medium text-neutral-900 dark:text-white">
											{suggestion.title}
										</h4>
										<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
											{suggestion.description}
										</p>
										{#if suggestion.keywords.length > 0}
											<div class="flex flex-wrap gap-1 mt-2">
												{#each suggestion.keywords.slice(0, 5) as keyword}
													<span
														class="px-1.5 py-0.5 text-xs bg-neutral-100 dark:bg-neutral-700 rounded"
													>
														{keyword}
													</span>
												{/each}
											</div>
										{/if}
									</button>
								{/each}
							</div>
						{:else if !isDiscovering}
							<div class="text-center py-8 text-neutral-500 dark:text-neutral-400">
								<Lightbulb class="w-12 h-12 mx-auto mb-3 opacity-50" />
								<p>Click "Discover" to find relevant blog topics</p>
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div
				class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-200 dark:border-neutral-700"
			>
				<Button variant="outline" onclick={onclose} disabled={isGenerating}>Cancel</Button>
				<Button onclick={handleGenerate} disabled={isGenerating || !topic.trim()}>
					{#if isGenerating}
						<RefreshCw class="w-4 h-4 mr-1.5 animate-spin" />
						Generating...
					{:else}
						<Sparkles class="w-4 h-4 mr-1.5" />
						Generate Post
					{/if}
				</Button>
			</div>
		</div>
	</div>
{/if}
