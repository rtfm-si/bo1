<script lang="ts">
	/**
	 * HelpSidebar - Collapsible category navigation for help center
	 */
	import { SvelteSet } from 'svelte/reactivity';
	import { ChevronDown, ChevronRight, Rocket, Users, CheckCircle, Database, Settings, HelpCircle, Lightbulb } from 'lucide-svelte';
	import type { HelpCategory, HelpArticle } from '$lib/data/help-content';

	interface Props {
		categories: HelpCategory[];
		articles: HelpArticle[];
		activeSlug?: string;
		onSelectArticle: (slug: string) => void;
	}

	let { categories, articles, activeSlug, onSelectArticle }: Props = $props();

	// Track expanded categories
	let expandedCategories = new SvelteSet<string>(['getting-started']);

	function toggleCategory(categoryId: string) {
		if (expandedCategories.has(categoryId)) {
			expandedCategories.delete(categoryId);
		} else {
			expandedCategories.add(categoryId);
		}
	}

	function getArticlesForCategory(categoryId: string): HelpArticle[] {
		return articles.filter((a) => a.category === categoryId);
	}

	// Icon mapping
	const iconComponents = {
		rocket: Rocket,
		lightbulb: Lightbulb,
		users: Users,
		'check-circle': CheckCircle,
		database: Database,
		settings: Settings,
		'help-circle': HelpCircle,
	};

	function getIcon(iconName: string) {
		return iconComponents[iconName as keyof typeof iconComponents] || HelpCircle;
	}

	// Auto-expand category when an article is selected
	$effect(() => {
		if (activeSlug) {
			const article = articles.find((a) => a.slug === activeSlug);
			if (article && !expandedCategories.has(article.category)) {
				expandedCategories.add(article.category);
			}
		}
	});
</script>

<nav class="space-y-1" aria-label="Help categories">
	{#each categories as category (category.id)}
		{@const categoryArticles = getArticlesForCategory(category.id)}
		{@const isExpanded = expandedCategories.has(category.id)}
		{@const IconComponent = getIcon(category.icon)}
		{@const hasActiveArticle = categoryArticles.some((a) => a.slug === activeSlug)}

		<div class="border-b border-neutral-100 dark:border-neutral-800 last:border-0">
			<button
				type="button"
				class="w-full flex items-center gap-3 px-3 py-3 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors rounded-md {hasActiveArticle
					? 'text-brand-600 dark:text-brand-400'
					: 'text-neutral-700 dark:text-neutral-300'}"
				onclick={() => toggleCategory(category.id)}
				aria-expanded={isExpanded}
			>
				<IconComponent class="w-5 h-5 flex-shrink-0" />
				<span class="font-medium flex-1">{category.label}</span>
				{#if isExpanded}
					<ChevronDown class="w-4 h-4 text-neutral-400" />
				{:else}
					<ChevronRight class="w-4 h-4 text-neutral-400" />
				{/if}
			</button>

			{#if isExpanded}
				<div class="pl-11 pb-2 space-y-1">
					{#each categoryArticles as article (article.slug)}
						<button
							type="button"
							class="w-full text-left px-3 py-2 text-sm rounded-md transition-colors {article.slug ===
							activeSlug
								? 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300 font-medium'
								: 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-800 hover:text-neutral-900 dark:hover:text-neutral-100'}"
							onclick={() => onSelectArticle(article.slug)}
						>
							{article.title}
						</button>
					{/each}
				</div>
			{/if}
		</div>
	{/each}
</nav>
