<script lang="ts">
	/**
	 * Decisions Index Page - List all published decision categories and decisions
	 */
	import { onMount } from 'svelte';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { apiClient } from '$lib/api/client';
	import type { PublicDecisionListItem, DecisionCategoryCount } from '$lib/api/types';
	import { BookOpen, ArrowRight, Users } from 'lucide-svelte';

	// State
	let categories = $state<DecisionCategoryCount[]>([]);
	let featuredDecisions = $state<PublicDecisionListItem[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	const categoryDescriptions: Record<string, string> = {
		hiring: 'First hires, contractors vs employees, when to scale',
		pricing: 'Pricing strategies, freemium vs paid, price changes',
		fundraising: 'When to raise, how much, bootstrapping alternatives',
		marketing: 'Channel selection, ads vs content, when to hire marketing',
		strategy: 'Pivots, market positioning, competitive moves',
		product: 'Feature prioritization, MVP scope, product-market fit',
		operations: 'Processes, tools, scaling infrastructure',
		growth: 'Growth strategies, metrics, expansion timing'
	};

	async function loadData() {
		isLoading = true;
		error = null;
		try {
			const [catResponse, decisionsResponse] = await Promise.all([
				apiClient.getDecisionCategories(),
				apiClient.getPublishedDecisions({ limit: 6 })
			]);
			categories = catResponse.categories.filter((c) => c.count > 0);
			featuredDecisions = decisionsResponse.decisions;
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

	function getCategoryColor(category: string): string {
		const colors: Record<string, string> = {
			hiring: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
			pricing: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
			fundraising: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
			marketing: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
			strategy: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
			product: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
			operations: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
			growth: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
		};
		return colors[category] || 'bg-neutral-100 text-neutral-600';
	}

	onMount(() => {
		loadData();
	});
</script>

<svelte:head>
	<title>Decision Library - Strategic Frameworks for Founders | Board of One</title>
	<meta
		name="description"
		content="Expert-backed decision frameworks for solo founders. Get structured guidance on hiring, pricing, fundraising, marketing, and more."
	/>
	<link rel="canonical" href="https://boardofone.com/decisions" />
</svelte:head>

<Header />

<main class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Hero -->
	<section class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
			<div
				class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400 text-sm font-medium mb-6"
			>
				<BookOpen class="w-4 h-4" />
				Decision Library
			</div>
			<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-white mb-4">
				Strategic Frameworks for Founders
			</h1>
			<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
				Expert-backed guidance on the decisions that shape your startup. Each framework synthesizes
				multiple perspectives to help you think through complex choices.
			</p>
		</div>
	</section>

	<!-- Categories -->
	<section class="py-16">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<h2 class="text-2xl font-bold text-neutral-900 dark:text-white mb-8">Browse by Category</h2>

			{#if isLoading}
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
					{#each Array(8) as _}
						<div class="h-32 bg-neutral-200 dark:bg-neutral-700 rounded-lg animate-pulse"></div>
					{/each}
				</div>
			{:else if error}
				<div class="rounded-lg bg-red-50 dark:bg-red-900/20 p-6 text-center">
					<p class="text-red-700 dark:text-red-400">{error}</p>
				</div>
			{:else}
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
					{#each categories as cat}
						<a
							href="/decisions/{cat.category}"
							class="group bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-5 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-600 transition-all"
						>
							<div class="flex items-center justify-between mb-3">
								<span
									class="px-2.5 py-1 rounded-full text-xs font-semibold {getCategoryColor(
										cat.category
									)}"
								>
									{cat.category}
								</span>
								<span class="text-sm text-neutral-500 dark:text-neutral-400">
									{cat.count} {cat.count === 1 ? 'decision' : 'decisions'}
								</span>
							</div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400">
								{categoryDescriptions[cat.category] || 'Strategic decisions'}
							</p>
							<div
								class="mt-3 flex items-center text-brand-600 dark:text-brand-400 text-sm font-medium group-hover:translate-x-1 transition-transform"
							>
								View all <ArrowRight class="w-4 h-4 ml-1" />
							</div>
						</a>
					{/each}
				</div>
			{/if}
		</div>
	</section>

	<!-- Featured Decisions -->
	{#if featuredDecisions.length > 0}
		<section class="py-16 bg-white dark:bg-neutral-800">
			<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl font-bold text-neutral-900 dark:text-white mb-8">
					Recent Decision Frameworks
				</h2>

				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
					{#each featuredDecisions as decision}
						<a
							href="/decisions/{decision.category}/{decision.slug}"
							class="group bg-neutral-50 dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-600 transition-all"
						>
							<div class="flex items-center gap-2 mb-3">
								<span
									class="px-2 py-0.5 rounded text-xs font-medium {getCategoryColor(
										decision.category
									)}"
								>
									{decision.category}
								</span>
							</div>
							<h3
								class="text-lg font-semibold text-neutral-900 dark:text-white mb-2 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors"
							>
								{decision.title}
							</h3>
							{#if decision.meta_description}
								<p class="text-sm text-neutral-600 dark:text-neutral-400 line-clamp-2 mb-4">
									{decision.meta_description}
								</p>
							{/if}
							<div class="flex items-center justify-between text-xs text-neutral-500">
								{#if decision.founder_context?.stage}
									<span class="flex items-center gap-1">
										<Users class="w-3 h-3" />
										{decision.founder_context.stage}
									</span>
								{:else}
									<span></span>
								{/if}
								<span>{formatDate(decision.published_at)}</span>
							</div>
						</a>
					{/each}
				</div>
			</div>
		</section>
	{/if}

	<!-- CTA -->
	<section class="py-16">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
			<h2 class="text-2xl font-bold text-neutral-900 dark:text-white mb-4">
				Need help with a specific decision?
			</h2>
			<p class="text-lg text-neutral-600 dark:text-neutral-400 mb-8">
				Board of One helps founders work through strategic decisions with AI-powered expert
				perspectives tailored to your situation.
			</p>
			<a
				href="/signup"
				class="inline-flex items-center px-6 py-3 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors"
			>
				Try Board of One Free
				<ArrowRight class="w-4 h-4 ml-2" />
			</a>
		</div>
	</section>
</main>

<Footer />
