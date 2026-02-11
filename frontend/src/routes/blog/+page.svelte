<script lang="ts">
	/**
	 * Blog Page - SEO-optimized blog with filters, sort, and search
	 * Fetches published posts from the API
	 */
	import { onMount } from 'svelte';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { apiClient } from '$lib/api/client';
	import type { PublicBlogPost } from '$lib/api/types';
	import { createBlogSchema, serializeJsonLd } from '$lib/utils/jsonld';

	import { formatDate } from '$lib/utils/time-formatting';
	// JSON-LD structured data for blog listing
	const blogJsonLd = serializeJsonLd(createBlogSchema());

	// State
	let posts = $state<PublicBlogPost[]>([]);
	let total = $state(0);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let sortBy = $state<'newest' | 'oldest'>('newest');

	// Filtered and sorted posts
	const filteredPosts = $derived.by(() => {
		let result = posts;

		// Filter by search
		if (searchQuery.trim()) {
			const query = searchQuery.toLowerCase();
			result = result.filter(
				(p) =>
					p.title.toLowerCase().includes(query) ||
					(p.excerpt?.toLowerCase().includes(query) ?? false) ||
					(p.meta_description?.toLowerCase().includes(query) ?? false)
			);
		}

		// Sort
		if (sortBy === 'newest') {
			result = [...result].sort(
				(a, b) =>
					new Date(b.published_at || b.created_at).getTime() -
					new Date(a.published_at || a.created_at).getTime()
			);
		} else {
			result = [...result].sort(
				(a, b) =>
					new Date(a.published_at || a.created_at).getTime() -
					new Date(b.published_at || b.created_at).getTime()
			);
		}

		return result;
	});

	const featuredPosts = $derived(filteredPosts.slice(0, 2));

	async function loadPosts() {
		isLoading = true;
		error = null;
		try {
			const response = await apiClient.listPublishedBlogPosts({ limit: 50 });
			posts = response.posts;
			total = response.total;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load posts';
			// Keep showing placeholder posts on error
			posts = [];
		} finally {
			isLoading = false;
		}
	}


	function estimateReadTime(content: string | undefined): number {
		if (!content) return 3;
		const words = content.split(/\s+/).length;
		return Math.max(1, Math.ceil(words / 200));
	}

	onMount(() => {
		loadPosts();
	});
</script>

<svelte:head>
	<title>Blog - Board of One | The Board Room</title>
	<meta
		name="description"
		content="Insights on decision-making, startup strategy, and AI-powered advisory for founders and leaders. Expert thinking for solo founders."
	/>
	<link rel="canonical" href="https://boardof.one/blog" />
	<meta property="og:type" content="website" />
	<meta property="og:url" content="https://boardof.one/blog" />
	<meta property="og:title" content="The Board Room - Board of One Blog" />
	<meta property="og:description" content="Insights on decision-making, startup strategy, and AI-powered advisory for founders and leaders." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="The Board Room - Board of One Blog" />
	<meta name="twitter:description" content="Insights on decision-making, startup strategy, and AI-powered advisory for founders." />
	<meta name="twitter:image" content="https://boardof.one/og-image.png" />
	<!-- JSON-LD Structured Data -->
	{@html `<script type="application/ld+json">${blogJsonLd}</script>`}
</svelte:head>

<div class="min-h-screen flex flex-col">
	<Header />

	<main class="flex-grow bg-white dark:bg-neutral-900">
		<!-- Hero -->
		<section
			class="py-16 bg-gradient-to-b from-brand-50 to-white dark:from-neutral-800 dark:to-neutral-900"
		>
			<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
				<div class="text-center mb-12">
					<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
						The Board Room
					</h1>
					<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
						Insights on decision-making, startup strategy, and the future of AI-powered advisory.
					</p>
				</div>

				<!-- Featured Posts -->
				{#if isLoading}
					<div class="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
						{#each [1, 2] as _}
							<div
								class="bg-white dark:bg-neutral-800 rounded-xl border border-neutral-200 dark:border-neutral-700 overflow-hidden animate-pulse"
							>
								<div
									class="aspect-video bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center"
								></div>
								<div class="p-6 space-y-3">
									<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/4"></div>
									<div class="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4"></div>
									<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-full"></div>
								</div>
							</div>
						{/each}
					</div>
				{:else if featuredPosts.length > 0}
					<div class="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
						{#each featuredPosts as post}
							<a
								href="/blog/{post.slug}"
								class="group bg-white dark:bg-neutral-800 rounded-xl border border-neutral-200 dark:border-neutral-700 overflow-hidden hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-lg transition-all"
							>
								<div
									class="aspect-video bg-gradient-to-br from-brand-100 to-brand-200 dark:from-brand-900/50 dark:to-neutral-800 flex items-center justify-center"
								>
									<span class="text-brand-600 dark:text-brand-400 font-bold text-lg">Featured</span>
								</div>
								<div class="p-6">
									<div class="flex items-center gap-2 mb-3">
										<span
											class="px-2 py-1 text-xs font-medium rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300"
										>
											Article
										</span>
										<span class="text-sm text-neutral-500 dark:text-neutral-400"
											>{estimateReadTime(post.content)} min read</span
										>
									</div>
									<h2
										class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-2 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors"
									>
										{post.title}
									</h2>
									<p class="text-neutral-600 dark:text-neutral-400 text-sm line-clamp-2">
										{post.excerpt || post.meta_description || ''}
									</p>
								</div>
							</a>
						{/each}
					</div>
				{/if}
			</div>
		</section>

		<!-- All Posts -->
		<section class="py-16">
			<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
				<!-- Filters -->
				<div class="flex flex-col md:flex-row gap-4 mb-8">
					<!-- Search -->
					<div class="relative flex-grow max-w-md">
						<svg
							class="absolute left-3 top-1/2 -tranneutral-y-1/2 w-5 h-5 text-neutral-400"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
							/>
						</svg>
						<input
							type="text"
							placeholder="Search articles..."
							bind:value={searchQuery}
							class="w-full pl-10 pr-4 py-2 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
						/>
					</div>

					<!-- Sort -->
					<select
						bind:value={sortBy}
						class="px-4 py-2 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-neutral-900 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
					>
						<option value="newest">Newest First</option>
						<option value="oldest">Oldest First</option>
					</select>
				</div>

				<!-- Error State -->
				{#if error}
					<div
						class="rounded-lg bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 p-4 mb-6"
					>
						<p class="text-sm text-error-700 dark:text-error-400">{error}</p>
						<button
							onclick={() => loadPosts()}
							class="mt-2 text-sm text-error-600 dark:text-error-400 underline hover:no-underline"
						>
							Try again
						</button>
					</div>
				{/if}

				<!-- Loading State -->
				{#if isLoading}
					<div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
						{#each Array(6) as _}
							<div
								class="bg-white dark:bg-neutral-800 rounded-xl border border-neutral-200 dark:border-neutral-700 p-6 animate-pulse"
							>
								<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/4 mb-3"></div>
								<div class="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4 mb-2"></div>
								<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-full mb-4"></div>
								<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2"></div>
							</div>
						{/each}
					</div>
				{:else if filteredPosts.length > 0}
					<!-- Posts Grid -->
					<div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
						{#each filteredPosts as post}
							<a
								href="/blog/{post.slug}"
								class="group bg-white dark:bg-neutral-800 rounded-xl border border-neutral-200 dark:border-neutral-700 p-6 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-md transition-all"
							>
								<div class="flex items-center gap-2 mb-3">
									<span
										class="px-2 py-1 text-xs font-medium rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300"
									>
										Article
									</span>
								</div>
								<h3
									class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors line-clamp-2"
								>
									{post.title}
								</h3>
								<p class="text-neutral-600 dark:text-neutral-400 text-sm mb-4 line-clamp-3">
									{post.excerpt || post.meta_description || ''}
								</p>
								<div
									class="flex items-center justify-between text-sm text-neutral-500 dark:text-neutral-400"
								>
									<span>{formatDate(post.published_at || post.created_at)}</span>
									<span>{estimateReadTime(post.content)} min read</span>
								</div>
							</a>
						{/each}
					</div>
				{:else}
					<!-- Empty State -->
					<div class="text-center py-16">
						<svg
							class="w-16 h-16 text-neutral-300 dark:text-neutral-600 mx-auto mb-4"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
						<h3 class="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-2">
							No articles found
						</h3>
						<p class="text-neutral-600 dark:text-neutral-400">
							{searchQuery ? 'Try adjusting your search.' : 'Check back soon for new content.'}
						</p>
					</div>
				{/if}
			</div>
		</section>

		<!-- Newsletter CTA -->
		<section class="py-16 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
					Stay in the Loop
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6">
					Get weekly insights on decision-making and startup strategy. No spam, unsubscribe anytime.
				</p>
				<form class="flex gap-3 max-w-md mx-auto">
					<input
						type="email"
						placeholder="your@email.com"
						class="flex-grow px-4 py-3 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
					/>
					<button
						type="submit"
						class="px-6 py-3 bg-brand-600 text-white font-semibold rounded-lg hover:bg-brand-700 transition-colors"
					>
						Subscribe
					</button>
				</form>
			</div>
		</section>
	</main>

	<Footer />
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.line-clamp-3 {
		display: -webkit-box;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
