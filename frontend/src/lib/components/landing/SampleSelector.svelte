<script lang="ts">
	/**
	 * Sample Selector - Grid of sample decision cards for landing page
	 */
	import type { SampleDecision } from '$lib/data/samples';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		samples: SampleDecision[];
		onSelectSample: (sample: SampleDecision) => void;
		featured?: number; // Number of samples to show, default shows all
	}

	let { samples, onSelectSample, featured }: Props = $props();

	// Show featured samples or all samples
	const displaySamples = $derived(featured ? samples.slice(0, featured) : samples);

	// Category color mapping for visual variety
	const categoryColors: Record<string, string> = {
		Marketing: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
		Hiring: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
		Product: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
		Finance: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
		Growth: 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300'
	};

	function getCategoryColor(category: string): string {
		return (
			categoryColors[category] ||
			'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300'
		);
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
			{#each displaySamples as sample}
				<div
					class="group bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 cursor-pointer"
					onclick={() => onSelectSample(sample)}
					role="button"
					tabindex="0"
					onkeydown={(e) => {
						if (e.key === 'Enter' || e.key === ' ') {
							e.preventDefault();
							onSelectSample(sample);
						}
					}}
				>
					<!-- Category badge -->
					<div class="flex items-center justify-between mb-4">
						<span class="inline-block px-3 py-1 rounded-full text-xs font-semibold {getCategoryColor(sample.category)}">
							{sample.category}
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
							<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
							<polyline points="15 3 21 3 21 9" />
							<line x1="10" y1="14" x2="21" y2="3" />
						</svg>
					</div>

					<!-- Question -->
					<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-3 leading-tight">
						{sample.question}
					</h3>

					<!-- Recommendation preview (truncated) -->
					<p class="text-sm text-neutral-600 dark:text-neutral-400 line-clamp-2 mb-4">
						{sample.recommendation}
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
							class="group-hover:translate-x-1 transition-transform"
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
