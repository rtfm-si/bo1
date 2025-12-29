<script lang="ts">
	/**
	 * Blog Post Page - Individual post with SEO meta tags and JSON-LD structured data
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import DOMPurify from 'isomorphic-dompurify';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { apiClient } from '$lib/api/client';
	import type { PublicBlogPost } from '$lib/api/types';
	import { createArticleSchema, serializeJsonLd } from '$lib/utils/jsonld';

	// State
	let post = $state<PublicBlogPost | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let viewTracked = $state(false);

	// Get slug from route params
	const slug = $derived($page.params.slug);

	// SEO fields
	const pageTitle = $derived(post?.meta_title || post?.title || 'Blog Post');
	const pageDescription = $derived(
		post?.meta_description || post?.excerpt || 'Read this article on Board of One.'
	);

	// JSON-LD structured data
	const articleJsonLd = $derived(post ? serializeJsonLd(createArticleSchema(post)) : null);

	async function loadPost() {
		if (!slug) return;

		isLoading = true;
		error = null;
		try {
			post = await apiClient.getBlogPostBySlug(slug);
		} catch (err) {
			if (err instanceof Error && err.message.includes('404')) {
				error = 'Post not found';
			} else {
				error = err instanceof Error ? err.message : 'Failed to load post';
			}
			post = null;
		} finally {
			isLoading = false;
		}
	}

	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}

	function estimateReadTime(content: string | undefined): number {
		if (!content) return 3;
		const words = content.split(/\s+/).length;
		return Math.max(1, Math.ceil(words / 200));
	}

	// Track view once per session per post
	async function trackView() {
		if (!browser || !slug || viewTracked) return;

		// Use sessionStorage to track views per session
		const viewKey = `blog_view_${slug}`;
		if (sessionStorage.getItem(viewKey)) return;

		try {
			await apiClient.trackBlogView(slug);
			sessionStorage.setItem(viewKey, '1');
			viewTracked = true;
		} catch {
			// Silently fail - analytics shouldn't break the page
		}
	}

	// Track CTA click
	async function trackClick() {
		if (!browser || !slug) return;

		try {
			await apiClient.trackBlogClick(slug);
		} catch {
			// Silently fail
		}
	}

	// Process inline markdown (bold, italic, links, code)
	function processInline(text: string): string {
		return text
			// Bold: **text** or __text__
			.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-neutral-900 dark:text-neutral-100">$1</strong>')
			.replace(/__(.+?)__/g, '<strong class="font-semibold text-neutral-900 dark:text-neutral-100">$1</strong>')
			// Italic: *text* or _text_
			.replace(/\*([^*]+)\*/g, '<em>$1</em>')
			.replace(/_([^_]+)_/g, '<em>$1</em>')
			// Inline code: `code`
			.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 bg-neutral-100 dark:bg-neutral-800 rounded text-sm font-mono">$1</code>')
			// Links: [text](url)
			.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-brand-600 dark:text-brand-400 hover:underline">$1</a>');
	}

	// Render markdown content
	function renderContent(content: string | undefined): string {
		if (!content) return '';
		return content
			.split('\n\n')
			.map((para) => {
				// Headers
				if (para.startsWith('### ')) {
					return `<h3 class="text-xl font-bold mt-8 mb-4 text-neutral-900 dark:text-neutral-100">${processInline(para.slice(4))}</h3>`;
				}
				if (para.startsWith('## ')) {
					return `<h2 class="text-2xl font-bold mt-10 mb-4 text-neutral-900 dark:text-neutral-100">${processInline(para.slice(3))}</h2>`;
				}
				if (para.startsWith('# ')) {
					return `<h1 class="text-3xl font-bold mt-12 mb-6 text-neutral-900 dark:text-neutral-100">${processInline(para.slice(2))}</h1>`;
				}
				// Lists
				if (para.match(/^[-*] /m)) {
					const items = para.split('\n').map((line) => {
						if (line.match(/^[-*] /)) {
							return `<li class="ml-4">${processInline(line.slice(2))}</li>`;
						}
						return processInline(line);
					});
					return `<ul class="list-disc list-inside my-4 space-y-2 text-neutral-700 dark:text-neutral-300">${items.join('')}</ul>`;
				}
				// Regular paragraphs
				return `<p class="my-4 text-neutral-700 dark:text-neutral-300 leading-relaxed">${processInline(para)}</p>`;
			})
			.join('');
	}

	onMount(() => {
		loadPost();
	});

	// Track view when post loads successfully
	$effect(() => {
		if (post && !viewTracked) {
			trackView();
		}
	});

	// Reload when slug changes
	$effect(() => {
		if (slug) {
			loadPost();
		}
	});
</script>

<svelte:head>
	<title>{pageTitle} - Board of One</title>
	<meta name="description" content={pageDescription} />
	{#if post?.seo_keywords?.length}
		<meta name="keywords" content={post.seo_keywords.join(', ')} />
	{/if}
	<!-- Open Graph -->
	<meta property="og:title" content={pageTitle} />
	<meta property="og:description" content={pageDescription} />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/blog/{slug}" />
	<!-- Twitter Card -->
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content={pageTitle} />
	<meta name="twitter:description" content={pageDescription} />
	<!-- Article metadata -->
	{#if post?.published_at}
		<meta property="article:published_time" content={post.published_at} />
	{/if}
	<!-- Canonical URL -->
	<link rel="canonical" href="https://boardof.one/blog/{slug}" />
	<!-- JSON-LD Structured Data -->
	{#if articleJsonLd}
		{@html `<script type="application/ld+json">${articleJsonLd}</script>`}
	{/if}
</svelte:head>

<div class="min-h-screen flex flex-col">
	<Header />

	<main class="flex-grow bg-white dark:bg-neutral-900">
		<!-- Loading State -->
		{#if isLoading}
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
				<div class="animate-pulse space-y-6">
					<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/4"></div>
					<div class="h-10 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4"></div>
					<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2"></div>
					<div class="space-y-4 mt-8">
						<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-full"></div>
						<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-full"></div>
						<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4"></div>
					</div>
				</div>
			</div>
		{:else if error}
			<!-- Error State -->
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
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
				<h1 class="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">{error}</h1>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6">
					The article you're looking for doesn't exist or has been removed.
				</p>
				<a
					href="/blog"
					class="inline-flex items-center px-4 py-2 bg-brand-600 text-white font-medium rounded-lg hover:bg-brand-700 transition-colors"
				>
					<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M10 19l-7-7m0 0l7-7m-7 7h18"
						/>
					</svg>
					Back to Blog
				</a>
			</div>
		{:else if post}
			<!-- Article -->
			<article class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
				<!-- Breadcrumb -->
				<nav class="mb-8">
					<a
						href="/blog"
						class="inline-flex items-center text-sm text-brand-600 dark:text-brand-400 hover:underline"
					>
						<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 19l-7-7m0 0l7-7m-7 7h18"
							/>
						</svg>
						Back to Blog
					</a>
				</nav>

				<!-- Header -->
				<header class="mb-12">
					<div class="flex items-center gap-3 mb-4">
						<span
							class="px-3 py-1 text-sm font-medium rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300"
						>
							Article
						</span>
						<span class="text-neutral-500 dark:text-neutral-400">
							{estimateReadTime(post.content)} min read
						</span>
					</div>

					<h1 class="text-3xl md:text-4xl lg:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
						{post.title}
					</h1>

					{#if post.excerpt}
						<p class="text-xl text-neutral-600 dark:text-neutral-400 mb-6">
							{post.excerpt}
						</p>
					{/if}

					<div class="flex items-center gap-4 text-sm text-neutral-500 dark:text-neutral-400">
						<span>Board of One Team</span>
						<span>|</span>
						<time datetime={post.published_at || post.created_at}>
							{formatDate(post.published_at || post.created_at)}
						</time>
					</div>
				</header>

				<!-- Content -->
				<div class="prose prose-lg max-w-none">
					{@html DOMPurify.sanitize(renderContent(post.content))}
				</div>

				<!-- Keywords -->
				{#if post.seo_keywords?.length}
					<div class="mt-12 pt-8 border-t border-neutral-200 dark:border-neutral-700">
						<h3 class="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-3">
							Related Topics
						</h3>
						<div class="flex flex-wrap gap-2">
							{#each post.seo_keywords as keyword}
								<span
									class="px-3 py-1 text-sm bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 rounded-full"
								>
									{keyword}
								</span>
							{/each}
						</div>
					</div>
				{/if}

				<!-- CTA -->
				<div
					class="mt-12 p-8 bg-gradient-to-br from-brand-50 to-brand-100 dark:from-brand-900/20 dark:to-brand-800/20 rounded-xl"
				>
					<h3 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
						Make better decisions with Board of One
					</h3>
					<p class="text-neutral-600 dark:text-neutral-400 mb-4">
						Get AI-powered strategic advice from a virtual board of experts.
					</p>
					<a
						href="/"
						onclick={trackClick}
						class="inline-flex items-center px-6 py-3 bg-brand-600 text-white font-semibold rounded-lg hover:bg-brand-700 transition-colors"
					>
						Get Started Free
					</a>
				</div>
			</article>
		{/if}
	</main>

	<Footer />
</div>
