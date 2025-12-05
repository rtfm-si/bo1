<script lang="ts">
	/**
	 * Sample Decision Modal - Shows example decision output.
	 */
	import Button from '$lib/components/ui/Button.svelte';
	import type { SampleDecision } from '$lib/data/samples';

	interface Props {
		show: boolean;
		sample: SampleDecision;
		onClose: () => void;
		onPrevious?: () => void;
		onNext?: () => void;
		showNavigation?: boolean;
	}

	let { show, sample, onClose, onPrevious, onNext, showNavigation = false }: Props = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
		if (e.key === 'ArrowLeft' && onPrevious) onPrevious();
		if (e.key === 'ArrowRight' && onNext) onNext();
	}

	function handleBackdropClick() {
		onClose();
	}

	function handleCloseAndScroll() {
		onClose();
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}
</script>

{#if show}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay bg-black/50"
		onclick={handleBackdropClick}
		onkeydown={handleKeydown}
		role="button"
		tabindex="0"
	>
		<div
			class="modal-content bg-white dark:bg-neutral-900 rounded-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-8 border border-neutral-200 dark:border-neutral-700"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			tabindex="-1"
		>
			<div class="flex justify-between items-start mb-6">
				<div class="flex-1">
					<div
						class="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 mb-3"
					>
						{sample.category}
					</div>
					<h3 class="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
						Sample Decision Output
					</h3>
				</div>
				<button
					onclick={onClose}
					class="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 text-2xl leading-none"
				>
					×
				</button>
			</div>

			<!-- Navigation arrows -->
			{#if showNavigation && (onPrevious || onNext)}
				<div class="flex justify-between items-center mb-6 -mt-2">
					<button
						onclick={onPrevious}
						disabled={!onPrevious}
						class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent"
					>
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
						>
							<path d="M15 18l-6-6 6-6" />
						</svg>
						Previous
					</button>
					<button
						onclick={onNext}
						disabled={!onNext}
						class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent"
					>
						Next
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
						>
							<path d="M9 18l6-6-6-6" />
						</svg>
					</button>
				</div>
			{/if}

			<div class="space-y-6 text-left">
				<div>
					<h4 class="font-semibold text-brand-600 dark:text-brand-400 mb-2">Question:</h4>
					<p class="text-neutral-700 dark:text-neutral-300">
						"{sample.question}"
					</p>
				</div>
				<div>
					<h4 class="font-semibold text-brand-600 dark:text-brand-400 mb-2">Recommendation:</h4>
					<p class="text-neutral-700 dark:text-neutral-300">
						{sample.recommendation}
					</p>
				</div>
				<div>
					<h4 class="font-semibold text-brand-600 dark:text-brand-400 mb-2">Why This Works:</h4>
					<ul class="list-disc list-inside space-y-2 text-neutral-700 dark:text-neutral-300">
						{#each sample.keyPoints as point}
							<li>{point}</li>
						{/each}
					</ul>
				</div>
				<div>
					<h4 class="font-semibold text-brand-600 dark:text-brand-400 mb-2">
						Blind Spots Identified:
					</h4>
					<ul class="list-disc list-inside space-y-2 text-neutral-700 dark:text-neutral-300">
						{#each sample.blindSpots as blindSpot}
							<li>{blindSpot}</li>
						{/each}
					</ul>
				</div>
				<div>
					<h4 class="font-semibold text-brand-600 dark:text-brand-400 mb-2">Next Steps:</h4>
					<ol class="list-decimal list-inside space-y-2 text-neutral-700 dark:text-neutral-300">
						{#each sample.nextSteps as step}
							<li>{step}</li>
						{/each}
					</ol>
				</div>
			</div>
			<div class="mt-8 pt-6 border-t border-neutral-200 dark:border-neutral-700">
				<Button variant="brand" size="lg" onclick={handleCloseAndScroll} class="w-full">
					Request Early Access to Try It
				</Button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* Modal overlay */
	.modal-overlay {
		backdrop-filter: blur(8px);
		animation: fadeIn 0.2s ease;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	/* Fade in from bottom */
	@keyframes fadeInUp {
		from {
			opacity: 0;
			transform: translateY(30px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.modal-content {
		animation: fadeInUp 0.3s ease;
	}
</style>
