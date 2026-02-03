<script lang="ts">
	/**
	 * Decision Page - Individual decision with expert perspectives, synthesis, and FAQs
	 * Includes Article, FAQPage, and BreadcrumbList JSON-LD schema
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { apiClient } from '$lib/api/client';
	import type { PublicDecision, PublicDecisionListItem } from '$lib/api/types';
	import {
		createDecisionArticleSchema,
		createDecisionFAQSchema,
		createDecisionBreadcrumbSchema,
		createDecisionHowToSchema,
		serializeJsonLd
	} from '$lib/utils/jsonld';
	import { parseSynthesisXML } from '$lib/utils/xml-parser';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';
	import {
		BookOpen,
		Users,
		AlertCircle,
		ChevronRight,
		ChevronDown,
		ArrowRight,
		MessageSquare
	} from 'lucide-svelte';

	// State
	let decision = $state<PublicDecision | null>(null);
	let relatedDecisions = $state<PublicDecisionListItem[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let viewTracked = $state(false);
	let expandedFaq = $state<number | null>(null);

	// Parsed synthesis sections
	const sections = $derived(decision?.synthesis ? parseSynthesisXML(decision.synthesis) : null);
	const hasParsedSections = $derived(
		sections &&
			(sections.executive_summary ||
				sections.recommendation ||
				sections.rationale ||
				sections.implementation_considerations)
	);

	// Route params
	const category = $derived($page.params.category);
	const slug = $derived($page.params.slug);
	const categoryTitle = $derived(
		category ? category.charAt(0).toUpperCase() + category.slice(1) : ''
	);

	// SEO fields
	const pageTitle = $derived(decision?.title || 'Decision');
	const pageDescription = $derived(
		decision?.meta_description || 'Expert framework for making this strategic decision.'
	);

	// JSON-LD structured data
	const articleJsonLd = $derived(
		decision && category ? serializeJsonLd(createDecisionArticleSchema(decision, category)) : null
	);
	const faqJsonLd = $derived(
		decision && decision.faqs?.length
			? serializeJsonLd(createDecisionFAQSchema(decision)!)
			: null
	);
	const breadcrumbJsonLd = $derived(
		decision && category ? serializeJsonLd(createDecisionBreadcrumbSchema(decision, category)) : null
	);
	const howToJsonLd = $derived(
		decision && decision.expert_perspectives?.length
			? serializeJsonLd(createDecisionHowToSchema(decision)!)
			: null
	);

	async function loadDecision() {
		if (!category || !slug) return;

		isLoading = true;
		error = null;
		try {
			const [decisionData, relatedData] = await Promise.all([
				apiClient.getPublishedDecision(category, slug),
				apiClient.getRelatedDecisions(category, slug, 3).catch(() => ({ decisions: [], total: 0 }))
			]);
			decision = decisionData;
			relatedDecisions = relatedData.decisions;
		} catch (err) {
			if (err instanceof Error && err.message.includes('404')) {
				error = 'Decision not found';
			} else {
				error = err instanceof Error ? err.message : 'Failed to load decision';
			}
			decision = null;
		} finally {
			isLoading = false;
		}
	}

	async function trackView() {
		if (!browser || !category || !slug || viewTracked) return;

		const viewKey = `decision_view_${category}_${slug}`;
		if (sessionStorage.getItem(viewKey)) return;

		try {
			await apiClient.trackDecisionView(category, slug);
			sessionStorage.setItem(viewKey, '1');
			viewTracked = true;
		} catch {
			// Silently fail
		}
	}

	async function trackClick() {
		if (!browser || !category || !slug) return;

		try {
			await apiClient.trackDecisionClick(category, slug);
		} catch {
			// Silently fail
		}
	}

	function toggleFaq(index: number) {
		expandedFaq = expandedFaq === index ? null : index;
	}

	onMount(() => {
		loadDecision();
	});

	// Track view after decision loads
	$effect(() => {
		if (decision && browser) {
			trackView();
		}
	});
</script>

<svelte:head>
	<title>{pageTitle} | Decision Library - Board of One</title>
	<meta name="description" content={pageDescription} />
	<link rel="canonical" href="https://boardof.one/decisions/{category}/{slug}" />

	{#if articleJsonLd}
		{@html `<script type="application/ld+json">${articleJsonLd}</script>`}
	{/if}
	{#if faqJsonLd}
		{@html `<script type="application/ld+json">${faqJsonLd}</script>`}
	{/if}
	{#if breadcrumbJsonLd}
		{@html `<script type="application/ld+json">${breadcrumbJsonLd}</script>`}
	{/if}
	{#if howToJsonLd}
		{@html `<script type="application/ld+json">${howToJsonLd}</script>`}
	{/if}
</svelte:head>

<Header />

<main class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	{#if isLoading}
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
			<div class="animate-pulse space-y-6">
				<div class="h-4 w-48 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
				<div class="h-10 w-3/4 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
				<div class="h-32 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
				<div class="space-y-4">
					{#each Array(3) as _}
						<div class="h-24 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
					{/each}
				</div>
			</div>
		</div>
	{:else if error}
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
			<AlertCircle class="w-12 h-12 mx-auto text-red-500 mb-4" />
			<h1 class="text-2xl font-bold text-neutral-900 dark:text-white mb-2">{error}</h1>
			<p class="text-neutral-600 dark:text-neutral-400 mb-6">
				The decision you're looking for doesn't exist or has been removed.
			</p>
			<a
				href="/decisions"
				class="inline-flex items-center text-brand-600 dark:text-brand-400 font-medium hover:underline"
			>
				Browse all decisions <ArrowRight class="w-4 h-4 ml-1" />
			</a>
		</div>
	{:else if decision}
		<!-- Breadcrumbs -->
		<div class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
				<nav class="flex items-center text-sm text-neutral-500 dark:text-neutral-400">
					<a href="/" class="hover:text-brand-600 dark:hover:text-brand-400">Home</a>
					<ChevronRight class="w-4 h-4 mx-2" />
					<a href="/decisions" class="hover:text-brand-600 dark:hover:text-brand-400">Decisions</a>
					<ChevronRight class="w-4 h-4 mx-2" />
					<a
						href="/decisions/{category}"
						class="hover:text-brand-600 dark:hover:text-brand-400"
					>
						{categoryTitle}
					</a>
					<ChevronRight class="w-4 h-4 mx-2" />
					<span class="text-neutral-900 dark:text-white font-medium truncate max-w-xs">
						{decision.title}
					</span>
				</nav>
			</div>
		</div>

		<!-- Header -->
		<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
				<div class="flex items-center gap-2 mb-4">
					<BookOpen class="w-5 h-5 text-brand-600 dark:text-brand-400" />
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400">
						Decision Framework
					</span>
				</div>
				<h1 class="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-white mb-4">
					{decision.title}
				</h1>
				{#if decision.meta_description}
					<p class="text-lg text-neutral-600 dark:text-neutral-400">
						{decision.meta_description}
					</p>
				{/if}
			</div>
		</header>

		<!-- Founder Context Box -->
		{#if decision.founder_context && (decision.founder_context.stage || decision.founder_context.constraints?.length || decision.founder_context.situation)}
			<section class="bg-neutral-100 dark:bg-neutral-800/50">
				<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6"
					>
						<div class="flex items-center gap-2 mb-4">
							<Users class="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
							<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
								Who This Is For
							</h2>
						</div>
						<div class="space-y-3 text-neutral-700 dark:text-neutral-300">
							{#if decision.founder_context.stage}
								<div>
									<span class="font-medium">Stage:</span>
									{decision.founder_context.stage}
								</div>
							{/if}
							{#if decision.founder_context.constraints?.length}
								<div>
									<span class="font-medium">Key Constraints:</span>
									<ul class="mt-1 ml-4 list-disc text-neutral-600 dark:text-neutral-400">
										{#each decision.founder_context.constraints as constraint}
											<li>{constraint}</li>
										{/each}
									</ul>
								</div>
							{/if}
							{#if decision.founder_context.situation}
								<div>
									<span class="font-medium">Situation:</span>
									{decision.founder_context.situation}
								</div>
							{/if}
						</div>
					</div>
				</div>
			</section>
		{/if}

		<!-- Expert Perspectives -->
		{#if decision.expert_perspectives && decision.expert_perspectives.length > 0}
			<section class="py-12">
				<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
					<h2 class="text-2xl font-bold text-neutral-900 dark:text-white mb-6">
						What the Board Says
					</h2>
					<div class="space-y-4">
						{#each decision.expert_perspectives as perspective}
							<div
								class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6"
							>
								<div class="flex items-center gap-3 mb-3">
									<div
										class="w-10 h-10 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center"
									>
										<MessageSquare class="w-5 h-5 text-brand-600 dark:text-brand-400" />
									</div>
									<span class="font-semibold text-neutral-900 dark:text-white">
										{perspective.persona_name}
									</span>
								</div>
								<blockquote class="text-neutral-700 dark:text-neutral-300 italic border-l-4 border-brand-300 dark:border-brand-600 pl-4">
									"{perspective.quote}"
								</blockquote>
							</div>
						{/each}
					</div>
				</div>
			</section>
		{/if}

		<!-- Synthesis -->
		{#if decision.synthesis}
			<section class="py-12 bg-white dark:bg-neutral-800">
				<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
					<h2 class="text-2xl font-bold text-neutral-900 dark:text-white mb-6">
						Synthesis & Recommendation
					</h2>

					{#if hasParsedSections && sections}
						<!-- Executive Summary -->
						{#if sections.executive_summary}
							<div class="bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-600 p-4 rounded-r-lg mb-4">
								<h3 class="font-semibold text-blue-900 dark:text-blue-100 mb-2">
									Executive Summary
								</h3>
								<MarkdownContent
									content={sections.executive_summary}
									class="text-sm text-blue-800 dark:text-blue-200"
								/>
							</div>
						{/if}

						<!-- Recommendation -->
						{#if sections.recommendation}
							<div class="bg-green-50 dark:bg-green-900/20 border-l-4 border-green-600 p-4 rounded-r-lg mb-4">
								<h3 class="font-semibold text-green-900 dark:text-green-100 mb-2">
									Recommendation
								</h3>
								<MarkdownContent
									content={sections.recommendation}
									class="text-sm text-green-800 dark:text-green-200"
								/>
							</div>
						{/if}

						<!-- Collapsible Sections -->
						<div class="space-y-2">
							{#if sections.rationale}
								<details class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg overflow-hidden">
									<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-600/50 transition-colors">
										Rationale
									</summary>
									<div class="px-4 pb-4 pt-2">
										<MarkdownContent
											content={sections.rationale}
											class="text-sm text-neutral-600 dark:text-neutral-400"
										/>
									</div>
								</details>
							{/if}

							{#if sections.implementation_considerations}
								<details class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg overflow-hidden">
									<summary class="cursor-pointer font-medium text-neutral-700 dark:text-neutral-300 p-4 hover:bg-neutral-100 dark:hover:bg-neutral-600/50 transition-colors">
										Implementation Considerations
									</summary>
									<div class="px-4 pb-4 pt-2">
										<MarkdownContent
											content={sections.implementation_considerations}
											class="text-sm text-neutral-600 dark:text-neutral-400"
										/>
									</div>
								</details>
							{/if}
						</div>
					{:else}
						<!-- Fallback: raw paragraphs -->
						<div class="prose dark:prose-invert max-w-none text-neutral-700 dark:text-neutral-300">
							{#each decision.synthesis.split('\n\n') as paragraph}
								{#if paragraph.trim()}
									<p>{paragraph}</p>
								{/if}
							{/each}
						</div>
					{/if}
				</div>
			</section>
		{/if}

		<!-- FAQs -->
		{#if decision.faqs && decision.faqs.length > 0}
			<section class="py-12">
				<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
					<h2 class="text-2xl font-bold text-neutral-900 dark:text-white mb-6">
						Frequently Asked Questions
					</h2>
					<div class="space-y-3">
						{#each decision.faqs as faq, i}
							<div
								class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700"
							>
								<button
									class="w-full px-6 py-4 flex items-center justify-between text-left"
									onclick={() => toggleFaq(i)}
								>
									<span class="font-medium text-neutral-900 dark:text-white pr-4">
										{faq.question}
									</span>
									<ChevronDown
										class="w-5 h-5 text-neutral-500 transition-transform {expandedFaq === i
											? 'rotate-180'
											: ''}"
									/>
								</button>
								{#if expandedFaq === i}
									<div class="px-6 pb-4 text-neutral-600 dark:text-neutral-400">
										{faq.answer}
									</div>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			</section>
		{/if}

		<!-- CTA -->
		<section class="py-12 bg-brand-50 dark:bg-brand-900/20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-2xl font-bold text-neutral-900 dark:text-white mb-4">
					Run This Decision in Board of One
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-2xl mx-auto">
					Get personalized expert perspectives tailored to your exact situation. Board of One helps
					you work through strategic decisions with AI-powered advisory.
				</p>
				<div class="flex flex-col sm:flex-row justify-center gap-4">
					<a
						href="/signup"
						onclick={trackClick}
						class="inline-flex items-center justify-center px-6 py-3 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors"
					>
						Try Free
						<ArrowRight class="w-4 h-4 ml-2" />
					</a>
					<a
						href="/pricing"
						class="inline-flex items-center justify-center px-6 py-3 rounded-lg border border-brand-600 text-brand-600 dark:text-brand-400 font-medium hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors"
					>
						See Plans
					</a>
				</div>
			</div>
		</section>

		<!-- Related Decisions -->
		{#if relatedDecisions.length > 0}
			<section class="py-12">
				<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
					<h2 class="text-xl font-bold text-neutral-900 dark:text-white mb-6">Related Decisions</h2>
					<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
						{#each relatedDecisions as related}
							<a
								href="/decisions/{related.category}/{related.slug}"
								class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-600 transition-all"
							>
								<span
									class="px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400"
								>
									{related.category}
								</span>
								<h3 class="mt-2 font-medium text-neutral-900 dark:text-white line-clamp-2">
									{related.title}
								</h3>
							</a>
						{/each}
					</div>
				</div>
			</section>
		{/if}
	{/if}
</main>

<Footer />
