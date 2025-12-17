<script lang="ts">
	/**
	 * Blog Page - SEO-optimized blog with filters, sort, and search
	 */
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';

	// Sample blog posts - replace with API/CMS data
	const posts = [
		{
			id: 'decision-fatigue-founder',
			title: 'How Decision Fatigue is Killing Your Startup',
			excerpt: 'Solo founders make 35+ decisions daily. Learn how cognitive load impacts your judgment and what to do about it.',
			category: 'Founder Insights',
			author: 'Board of One Team',
			date: '2025-01-15',
			readTime: 8,
			image: null,
			featured: true
		},
		{
			id: 'ai-advisory-boards',
			title: 'The Rise of AI Advisory Boards: What Founders Need to Know',
			excerpt: 'Traditional advisory boards are expensive and slow. AI-powered alternatives are changing how founders get strategic advice.',
			category: 'AI & Strategy',
			author: 'Board of One Team',
			date: '2025-01-10',
			readTime: 6,
			image: null,
			featured: true
		},
		{
			id: 'pricing-strategy-saas',
			title: '5 Pricing Decisions That Make or Break SaaS Startups',
			excerpt: 'From freemium to enterprise pricing, we analyze the strategic trade-offs that determine SaaS success.',
			category: 'Strategy',
			author: 'Board of One Team',
			date: '2025-01-05',
			readTime: 10,
			image: null,
			featured: false
		},
		{
			id: 'hiring-first-employee',
			title: 'When to Hire Your First Employee (And Who It Should Be)',
			excerpt: 'The first hire sets the culture. We break down the decision framework for solo founders ready to grow.',
			category: 'Hiring',
			author: 'Board of One Team',
			date: '2024-12-28',
			readTime: 7,
			image: null,
			featured: false
		},
		{
			id: 'structured-thinking',
			title: 'Structured Thinking: The Secret Weapon of Top Founders',
			excerpt: 'Why the best founders use frameworks, and how to implement structured decision-making in your startup.',
			category: 'Founder Insights',
			author: 'Board of One Team',
			date: '2024-12-20',
			readTime: 5,
			image: null,
			featured: false
		},
		{
			id: 'pivot-or-persevere',
			title: 'Pivot or Persevere: A Framework for the Hardest Startup Decision',
			excerpt: 'When traction stalls, founders face an existential choice. Here\'s how to think through it systematically.',
			category: 'Strategy',
			author: 'Board of One Team',
			date: '2024-12-15',
			readTime: 9,
			image: null,
			featured: false
		}
	];

	const categories = ['All', ...new Set(posts.map(p => p.category))];

	// State
	let searchQuery = $state('');
	let selectedCategory = $state('All');
	let sortBy = $state<'newest' | 'oldest' | 'readTime'>('newest');

	// Filtered and sorted posts
	const filteredPosts = $derived.by(() => {
		let result = posts;

		// Filter by search
		if (searchQuery.trim()) {
			const query = searchQuery.toLowerCase();
			result = result.filter(
				p =>
					p.title.toLowerCase().includes(query) ||
					p.excerpt.toLowerCase().includes(query) ||
					p.category.toLowerCase().includes(query)
			);
		}

		// Filter by category
		if (selectedCategory !== 'All') {
			result = result.filter(p => p.category === selectedCategory);
		}

		// Sort
		if (sortBy === 'newest') {
			result = [...result].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
		} else if (sortBy === 'oldest') {
			result = [...result].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
		} else {
			result = [...result].sort((a, b) => a.readTime - b.readTime);
		}

		return result;
	});

	const featuredPosts = $derived(posts.filter(p => p.featured).slice(0, 2));

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}

	const categoryColors: Record<string, string> = {
		'Founder Insights': 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
		'AI & Strategy': 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
		'Strategy': 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
		'Hiring': 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300'
	};

	function getCategoryColor(category: string): string {
		return categoryColors[category] || 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300';
	}
</script>

<svelte:head>
	<title>Blog - Board of One</title>
	<meta name="description" content="Insights on decision-making, startup strategy, and AI-powered advisory for founders and leaders." />
</svelte:head>

<div class="min-h-screen flex flex-col">
	<Header />

	<main class="flex-grow bg-white dark:bg-neutral-900">
		<!-- Hero -->
		<section class="py-16 bg-gradient-to-b from-brand-50 to-white dark:from-neutral-800 dark:to-neutral-900">
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
				{#if featuredPosts.length > 0}
					<div class="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
						{#each featuredPosts as post}
							<a
								href="/blog/{post.id}"
								class="group bg-white dark:bg-neutral-800 rounded-xl border border-neutral-200 dark:border-neutral-700 overflow-hidden hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-lg transition-all"
							>
								<div class="aspect-video bg-gradient-to-br from-brand-100 to-brand-200 dark:from-brand-900/50 dark:to-neutral-800 flex items-center justify-center">
									<span class="text-brand-600 dark:text-brand-400 font-bold text-lg">Featured</span>
								</div>
								<div class="p-6">
									<div class="flex items-center gap-2 mb-3">
										<span class="px-2 py-1 text-xs font-medium rounded-full {getCategoryColor(post.category)}">
											{post.category}
										</span>
										<span class="text-sm text-neutral-500 dark:text-neutral-400">{post.readTime} min read</span>
									</div>
									<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-2 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
										{post.title}
									</h2>
									<p class="text-neutral-600 dark:text-neutral-400 text-sm line-clamp-2">
										{post.excerpt}
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
						<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
						</svg>
						<input
							type="text"
							placeholder="Search articles..."
							bind:value={searchQuery}
							class="w-full pl-10 pr-4 py-2 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
						/>
					</div>

					<!-- Category Filter -->
					<div class="flex gap-2 flex-wrap">
						{#each categories as category}
							<button
								onclick={() => selectedCategory = category}
								class="px-4 py-2 text-sm font-medium rounded-lg transition-colors
									{selectedCategory === category
										? 'bg-brand-600 text-white'
										: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700'}"
							>
								{category}
							</button>
						{/each}
					</div>

					<!-- Sort -->
					<select
						bind:value={sortBy}
						class="px-4 py-2 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-neutral-900 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
					>
						<option value="newest">Newest First</option>
						<option value="oldest">Oldest First</option>
						<option value="readTime">Quick Reads</option>
					</select>
				</div>

				<!-- Posts Grid -->
				{#if filteredPosts.length > 0}
					<div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
						{#each filteredPosts as post}
							<a
								href="/blog/{post.id}"
								class="group bg-white dark:bg-neutral-800 rounded-xl border border-neutral-200 dark:border-neutral-700 p-6 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-md transition-all"
							>
								<div class="flex items-center gap-2 mb-3">
									<span class="px-2 py-1 text-xs font-medium rounded-full {getCategoryColor(post.category)}">
										{post.category}
									</span>
								</div>
								<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors line-clamp-2">
									{post.title}
								</h3>
								<p class="text-neutral-600 dark:text-neutral-400 text-sm mb-4 line-clamp-3">
									{post.excerpt}
								</p>
								<div class="flex items-center justify-between text-sm text-neutral-500 dark:text-neutral-400">
									<span>{formatDate(post.date)}</span>
									<span>{post.readTime} min read</span>
								</div>
							</a>
						{/each}
					</div>
				{:else}
					<div class="text-center py-16">
						<svg class="w-16 h-16 text-neutral-300 dark:text-neutral-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						<h3 class="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-2">No articles found</h3>
						<p class="text-neutral-600 dark:text-neutral-400">Try adjusting your search or filters.</p>
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
