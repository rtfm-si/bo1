<script lang="ts">
	/**
	 * Help Center Page
	 * Searchable FAQ and documentation for Board of One
	 */
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Search, HelpCircle } from 'lucide-svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import HelpSidebar from '$lib/components/help/HelpSidebar.svelte';
	import HelpArticle from '$lib/components/help/HelpArticle.svelte';
	import {
		helpCategories,
		helpArticles,
		searchHelpArticles,
		getArticleBySlug,
	} from '$lib/data/help-content';

	// Search state
	let searchQuery = $state('');

	// Get active article from URL hash or default to first
	const activeSlug = $derived($page.url.hash?.slice(1) || 'first-meeting');
	const activeArticle = $derived(getArticleBySlug(activeSlug) || helpArticles[0]);

	// Filtered articles based on search
	const filteredArticles = $derived(searchHelpArticles(searchQuery));
	const isSearching = $derived(searchQuery.trim().length > 0);

	// Handle article selection
	function handleSelectArticle(slug: string) {
		goto(`/help#${slug}`, { replaceState: true, noScroll: true });
		searchQuery = '';
	}

	// Handle search result click
	function handleSearchResultClick(slug: string) {
		handleSelectArticle(slug);
	}
</script>

<svelte:head>
	<title>Help Center | Board of One</title>
	<meta name="description" content="Get help with Board of One - FAQs, tutorials, and documentation" />
</svelte:head>

<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-6">
	<!-- Header -->
	<div class="mb-8">
		<div class="flex items-center gap-3 mb-2">
			<HelpCircle class="w-8 h-8 text-brand-600 dark:text-brand-400" />
			<h1 class="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">Help Center</h1>
		</div>
		<p class="text-neutral-600 dark:text-neutral-400">
			Find answers, tutorials, and documentation for Board of One
		</p>
	</div>

	<!-- Search Bar -->
	<div class="mb-8 relative">
		<div class="relative max-w-xl">
			<Search class="absolute left-3 top-1/2 -tranneutral-y-1/2 w-5 h-5 text-neutral-400" />
			<input
				type="text"
				bind:value={searchQuery}
				placeholder="Search help articles..."
				class="w-full pl-10 pr-4 py-3 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
				aria-label="Search help articles"
			/>
		</div>

		<!-- Search Results Dropdown -->
		{#if isSearching}
			<div class="absolute z-10 mt-2 w-full max-w-xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg max-h-96 overflow-y-auto">
				{#if filteredArticles.length === 0}
					<div class="px-4 py-8 text-center text-neutral-500 dark:text-neutral-400">
						<p>No articles found for "{searchQuery}"</p>
						<p class="text-sm mt-1">Try different keywords</p>
					</div>
				{:else}
					<ul class="divide-y divide-neutral-100 dark:divide-neutral-800">
						{#each filteredArticles as article (article.slug)}
							<li>
								<button
									type="button"
									class="w-full px-4 py-3 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
									onclick={() => handleSearchResultClick(article.slug)}
								>
									<p class="font-medium text-neutral-900 dark:text-neutral-100">
										{article.title}
									</p>
									<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
										{helpCategories.find((c) => c.id === article.category)?.label}
									</p>
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Main Content Grid -->
	<div class="grid grid-cols-1 lg:grid-cols-4 gap-8">
		<!-- Sidebar -->
		<aside class="lg:col-span-1">
			<BoCard padding="sm">
				<HelpSidebar
					categories={helpCategories}
					articles={helpArticles}
					{activeSlug}
					onSelectArticle={handleSelectArticle}
				/>
			</BoCard>
		</aside>

		<!-- Article Content -->
		<main class="lg:col-span-3">
			<BoCard padding="lg">
				{#if activeArticle}
					<HelpArticle article={activeArticle} />
				{:else}
					<div class="text-center py-12">
						<HelpCircle class="w-12 h-12 text-neutral-300 dark:text-neutral-600 mx-auto mb-4" />
						<p class="text-neutral-500 dark:text-neutral-400">
							Select an article from the sidebar to get started
						</p>
					</div>
				{/if}
			</BoCard>
		</main>
	</div>

	<!-- Quick Links Footer -->
	<div class="mt-12 pt-8 border-t border-neutral-200 dark:border-neutral-700">
		<h2 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
			Still need help?
		</h2>
		<div class="flex flex-wrap gap-4">
			<a
				href="/help#contact-support"
				class="text-brand-600 dark:text-brand-400 hover:underline"
				onclick={(e) => { e.preventDefault(); handleSelectArticle('contact-support'); }}
			>
				Contact Support
			</a>
			<span class="text-neutral-300 dark:text-neutral-600">|</span>
			<a
				href="mailto:support@boardofone.com"
				class="text-brand-600 dark:text-brand-400 hover:underline"
			>
				support@boardofone.com
			</a>
		</div>
	</div>
</div>
