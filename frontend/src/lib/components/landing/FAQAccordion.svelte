<script lang="ts">
	/**
	 * FAQ Accordion - Expandable FAQ section.
	 */
	interface FAQ {
		question: string;
		answer: string;
	}

	interface Props {
		faqs: readonly FAQ[];
	}

	let { faqs }: Props = $props();

	let openIndex: number | null = $state(null);

	function toggle(index: number) {
		openIndex = openIndex === index ? null : index;
	}
</script>

<section class="py-24 bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800">
	<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
		<h2 class="text-3xl md:text-4xl font-bold mb-12 text-center leading-tight">
			<span class="text-neutral-700 dark:text-neutral-300 font-normal">Questions?</span>
			<span class="text-brand-600 dark:text-brand-400 italic font-extrabold emphasis-word"
				>We've Got Answers.</span
			>
		</h2>
		<div class="space-y-4">
			{#each faqs as faq, i}
				<div
					class="border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden bg-white dark:bg-neutral-800"
				>
					<button
						onclick={() => toggle(i)}
						class="w-full px-6 py-4 text-left flex items-center justify-between hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
					>
						<span class="font-semibold text-neutral-900 dark:text-neutral-100 pr-4"
							>{faq.question}</span
						>
						<span
							class="text-brand-600 dark:text-brand-400 text-xl flex-shrink-0 transform transition-transform duration-300"
							class:rotate-180={openIndex === i}
						>
							↓
						</span>
					</button>
					{#if openIndex === i}
						<div class="faq-answer px-6 pb-4">
							<p class="text-neutral-600 dark:text-neutral-400 leading-relaxed">
								{faq.answer}
							</p>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</div>
</section>

<style>
	/* Slide down for FAQ */
	@keyframes slideDown {
		from {
			opacity: 0;
			max-height: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
			max-height: 500px;
			transform: translateY(0);
		}
	}

	/* Subtle emphasis animation for key words */
	@keyframes emphasis-glow {
		0%,
		100% {
			text-shadow: 0 0 8px rgba(0, 200, 179, 0.15);
		}
		50% {
			text-shadow: 0 0 12px rgba(0, 200, 179, 0.25);
		}
	}

	.emphasis-word {
		animation: emphasis-glow 3s ease-in-out infinite;
	}

	/* FAQ accordion animation */
	.faq-answer {
		animation: slideDown 0.3s ease forwards;
		overflow: hidden;
	}
</style>
