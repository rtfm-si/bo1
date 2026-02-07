<script lang="ts">
	/**
	 * Sample Selector - Grid of sample decision cards for landing page
	 * Supports both legacy SampleDecision (for modal) and FeaturedDecision (for links)
	 */
	import { goto } from '$app/navigation';
	import type { SampleDecision } from '$lib/data/samples';
	import type { FeaturedDecision } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';

	type DecisionItem = SampleDecision | FeaturedDecision;

	interface Props {
		samples?: SampleDecision[];
		decisions?: FeaturedDecision[];
		onSelectSample?: (sample: SampleDecision) => void;
		featured?: number; // Number of items to show, default shows all
	}

	let { samples, decisions, onSelectSample, featured }: Props = $props();

	// Determine if using new featured decisions or legacy samples
	const useFeatured = $derived(decisions && decisions.length > 0);

	// Show featured items or all items
	const displayItems = $derived.by(() => {
		const items = useFeatured ? decisions! : (samples ?? []);
		return featured ? items.slice(0, featured) : items;
	});

	function isFeaturedDecision(item: DecisionItem): item is FeaturedDecision {
		return 'slug' in item && 'synthesis' in item;
	}

	function getTitle(item: DecisionItem): string {
		if (isFeaturedDecision(item)) {
			return item.title;
		}
		return item.question;
	}

	function getDescription(item: DecisionItem): string {
		if (isFeaturedDecision(item)) {
			return item.synthesis || item.meta_description || '';
		}
		return item.recommendation;
	}

	function getCategory(item: DecisionItem): string {
		return item.category;
	}

	function handleClick(item: DecisionItem) {
		if (isFeaturedDecision(item)) {
			goto(`/decisions/${item.category}/${item.slug}`);
		} else if (onSelectSample) {
			onSelectSample(item as SampleDecision);
		}
	}

	// Category color mapping for visual variety (both capitalized and lowercase)
	const categoryColors: Record<string, string> = {
		Marketing: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
		marketing: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
		Hiring: 'bg-info-100 dark:bg-info-900/30 text-info-700 dark:text-info-300',
		hiring: 'bg-info-100 dark:bg-info-900/30 text-info-700 dark:text-info-300',
		Product: 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300',
		product: 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300',
		Finance: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
		pricing: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
		Growth: 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300',
		growth: 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300',
		strategy: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300',
		fundraising: 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300',
		operations: 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300'
	};

	function getCategoryColor(category: string): string {
		return (
			categoryColors[category] ||
			'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300'
		);
	}

	function formatCategory(category: string): string {
		return category.charAt(0).toUpperCase() + category.slice(1);
	}
</script>

<section
	id="samples"
	class="py-24 bg-neutral-50 dark:bg-neutral-800 border-y border-neutral-200 dark:border-neutral-800"
>
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
		<div class="text-center mb-12">
			<h2
				class="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-4 leading-tight"
			>
				See <span class="text-brand-600 dark:text-brand-400 italic font-extrabold"
					>Board of One</span
				> in Action
			</h2>
			<p class="text-lg text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
				Real examples of how we turn complex decisions into clear, actionable recommendations.
			</p>
		</div>

		<!-- Sample cards grid -->
		<div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
			{#each displayItems as item}
				<div
					class="group bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 hover:shadow-lg hover:-tranneutral-y-1 cursor-pointer"
					onclick={() => handleClick(item)}
					role="button"
					tabindex="0"
					onkeydown={(e) => {
						if (e.key === 'Enter' || e.key === ' ') {
							e.preventDefault();
							handleClick(item);
						}
					}}
				>
					<!-- Category badge -->
					<div class="flex items-center justify-between mb-4">
						<span class="inline-block px-3 py-1 rounded-full text-xs font-semibold {getCategoryColor(getCategory(item))}">
							{formatCategory(getCategory(item))}
						</span>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
							class="text-neutral-400 dark:text-neutral-600 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors"
						>
							<path d="M5 12h14" />
							<path d="M12 5l7 7-7 7" />
						</svg>
					</div>

					<!-- Question/Title -->
					<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-3 leading-tight">
						{getTitle(item)}
					</h3>

					<!-- Description preview (truncated) -->
					<p class="text-sm text-neutral-600 dark:text-neutral-400 line-clamp-2 mb-4">
						{getDescription(item)}
					</p>

					<!-- View button -->
					<div class="flex items-center gap-2 text-brand-600 dark:text-brand-400 font-medium text-sm">
						<span>View Full Analysis</span>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="16"
							height="16"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
							class="group-hover:tranneutral-x-1 transition-transform"
						>
							<path d="M5 12h14" />
							<path d="M12 5l7 7-7 7" />
						</svg>
					</div>
				</div>
			{/each}
		</div>

		<!-- CTA below samples -->
		<div class="text-center mt-12">
			<p class="text-neutral-600 dark:text-neutral-400 mb-4">
				Want insights like these for your own decisions?
			</p>
			<Button
				variant="brand"
				size="lg"
				onclick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
				class="transform hover:scale-105 transition-transform duration-300"
			>
				Request Early Access
			</Button>
		</div>
	</div>
</section>
