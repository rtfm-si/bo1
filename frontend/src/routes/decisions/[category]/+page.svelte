<script lang="ts">
	/**
	 * Decision Category Page - List decisions in a category
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { apiClient } from '$lib/api/client';
	import type { PublicDecisionListItem } from '$lib/api/types';
	import {
		createDecisionCategoryBreadcrumbSchema,
		createDecisionCategoryCollectionSchema,
		serializeJsonLd
	} from '$lib/utils/jsonld';
	import { BookOpen, ArrowRight, Users, ChevronRight } from 'lucide-svelte';

	// State
	let decisions = $state<PublicDecisionListItem[]>([]);
	let total = $state(0);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	const category = $derived($page.params.category);
	const categoryTitle = $derived(category ? category.charAt(0).toUpperCase() + category.slice(1) : '');

	const categoryDescriptions: Record<string, string> = {
		hiring: 'Decisions about building your team - from first hire to scaling',
		pricing: 'Pricing strategies, models, and when to change prices',
		fundraising: 'Raising capital, bootstrapping, and funding decisions',
		marketing: 'Marketing channels, budgets, and growth strategies',
		strategy: 'Strategic pivots, positioning, and competitive decisions',
		product: 'Product development, features, and roadmap decisions',
		operations: 'Operational decisions, tools, and process improvements',
		growth: 'Growth strategies, metrics, and expansion decisions'
	};

	// JSON-LD structured data
	const breadcrumbJsonLd = $derived(
		category ? serializeJsonLd(createDecisionCategoryBreadcrumbSchema(category)) : null
	);
	const collectionJsonLd = $derived(
		category
			? serializeJsonLd(
					createDecisionCategoryCollectionSchema(
						category,
						categoryDescriptions[category] || '',
						total
					)
				)
			: null
	);

	async function loadDecisions() {
		if (!category) return;
		isLoading = true;
		error = null;
		try {
			const response = await apiClient.getPublishedDecisions({ category, limit: 50 });
			decisions = response.decisions;
			total = response.total;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load decisions';
		} finally {
			isLoading = false;
		}
	}

	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	onMount(() => {
		loadDecisions();
	});

	// Reload when category changes
	$effect(() => {
		if (category) {
			loadDecisions();
		}
	});
</script>

<svelte:head>
	<title>{categoryTitle} Decisions - Decision Library | Board of One</title>
	<meta
		name="description"
		content="{(category && categoryDescriptions[category]) || `${categoryTitle} decisions for founders`}. Expert frameworks to help you make better strategic choices."
	/>
	<link rel="canonical" href="https://boardof.one/decisions/{category}" />

	{#if breadcrumbJsonLd}
		{@html `<script type="application/ld+json">${breadcrumbJsonLd}</script>`}
	{/if}
	{#if collectionJsonLd}
		{@html `<script type="application/ld+json">${collectionJsonLd}</script>`}
	{/if}
</svelte:head>

<Header />

<main class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Breadcrumbs -->
	<div class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
			<nav class="flex items-center text-sm text-neutral-500 dark:text-neutral-400">
				<a href="/" class="hover:text-brand-600 dark:hover:text-brand-400">Home</a>
				<ChevronRight class="w-4 h-4 mx-2" />
				<a href="/decisions" class="hover:text-brand-600 dark:hover:text-brand-400">Decisions</a>
				<ChevronRight class="w-4 h-4 mx-2" />
				<span class="text-neutral-900 dark:text-white font-medium">{categoryTitle}</span>
			</nav>
		</div>
	</div>

	<!-- Header -->
	<section class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
			<div class="flex items-center gap-3 mb-4">
				<BookOpen class="w-8 h-8 text-brand-600 dark:text-brand-400" />
				<h1 class="text-3xl font-bold text-neutral-900 dark:text-white">
					{categoryTitle} Decisions
				</h1>
			</div>
			<p class="text-lg text-neutral-600 dark:text-neutral-400 max-w-3xl">
				{(category && categoryDescriptions[category]) ||
					`Strategic frameworks for ${category || ''} decisions. Expert perspectives to help you make better choices.`}
			</p>
			<p class="mt-3 text-sm text-neutral-500 dark:text-neutral-400">
				{total} {total === 1 ? 'decision framework' : 'decision frameworks'}
			</p>
		</div>
	</section>

	<!-- Decision List -->
	<section class="py-12">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			{#if isLoading}
				<div class="space-y-4">
					{#each Array(5) as _}
						<div class="h-32 bg-neutral-200 dark:bg-neutral-700 rounded-lg animate-pulse"></div>
					{/each}
				</div>
			{:else if error}
				<div class="rounded-lg bg-error-50 dark:bg-error-900/20 p-6 text-center">
					<p class="text-error-700 dark:text-error-400">{error}</p>
				</div>
			{:else if decisions.length === 0}
				<div class="text-center py-16">
					<BookOpen class="w-12 h-12 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" />
					<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-2">
						No decisions yet in this category
					</h3>
					<p class="text-neutral-500 dark:text-neutral-400 mb-6">
						Check back soon for new decision frameworks.
					</p>
					<a
						href="/decisions"
						class="inline-flex items-center text-brand-600 dark:text-brand-400 font-medium hover:underline"
					>
						Browse all categories <ArrowRight class="w-4 h-4 ml-1" />
					</a>
				</div>
			{:else}
				<div class="space-y-4">
					{#each decisions as decision}
						<a
							href="/decisions/{decision.category}/{decision.slug}"
							class="block bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-600 transition-all group"
						>
							<h2
								class="text-xl font-semibold text-neutral-900 dark:text-white mb-2 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors"
							>
								{decision.title}
							</h2>
							{#if decision.meta_description}
								<p class="text-neutral-600 dark:text-neutral-400 mb-4">
									{decision.meta_description}
								</p>
							{/if}
							<div class="flex items-center justify-between text-sm text-neutral-500">
								<div class="flex items-center gap-4">
									{#if decision.founder_context?.stage}
										<span class="flex items-center gap-1">
											<Users class="w-4 h-4" />
											{decision.founder_context.stage}
										</span>
									{/if}
									{#if decision.founder_context?.constraints?.length}
										<span>{decision.founder_context.constraints.length} constraints</span>
									{/if}
								</div>
								<span>{formatDate(decision.published_at)}</span>
							</div>
						</a>
					{/each}
				</div>
			{/if}
		</div>
	</section>

	<!-- CTA -->
	<section class="py-12 bg-white dark:bg-neutral-800">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
			<h2 class="text-xl font-bold text-neutral-900 dark:text-white mb-4">
				Don't see your specific situation?
			</h2>
			<p class="text-neutral-600 dark:text-neutral-400 mb-6">
				Board of One can help you work through any strategic decision with expert perspectives
				tailored to your exact context.
			</p>
			<a
				href="/signup"
				class="inline-flex items-center px-5 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors"
			>
				Start a Decision Session
				<ArrowRight class="w-4 h-4 ml-2" />
			</a>
		</div>
	</section>
</main>

<Footer />
