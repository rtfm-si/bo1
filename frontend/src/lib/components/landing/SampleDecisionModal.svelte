<script lang="ts">
	/**
	 * Sample Decision Modal - Shows example decision output.
	 */
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		show: boolean;
		onClose: () => void;
	}

	let { show, onClose }: Props = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
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
				<h3 class="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
					Sample Decision Output
				</h3>
				<button
					onclick={onClose}
					class="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 text-2xl leading-none"
				>
					×
				</button>
			</div>
			<div class="space-y-6 text-left">
				<div>
					<h4 class="font-semibold text-brand-600 dark:text-brand-400 mb-2">Question:</h4>
					<p class="text-neutral-700 dark:text-neutral-300">
						"Should I invest $50K in paid ads or hire a content marketer?"
					</p>
				</div>
				<div>
					<h4 class="font-semibold text-brand-600 dark:text-brand-400 mb-2">Recommendation:</h4>
					<p class="text-neutral-700 dark:text-neutral-300">
						<span class="font-semibold">Hire a content marketer first</span> — then allocate 30% of
						the remaining budget ($15K) to amplify their best content with paid ads.
					</p>
				</div>
				<div>
					<h4 class="font-semibold text-brand-600 dark:text-brand-400 mb-2">Why This Works:</h4>
					<ul class="list-disc list-inside space-y-2 text-neutral-700 dark:text-neutral-300">
						<li>Content compounds over time; ads stop when budget runs out</li>
						<li>Reduces dependency on paid acquisition long-term</li>
						<li>Creates owned audience assets (email list, SEO authority)</li>
					</ul>
				</div>
				<div>
					<h4 class="font-semibold text-brand-600 dark:text-brand-400 mb-2">
						Blind Spots Identified:
					</h4>
					<ul class="list-disc list-inside space-y-2 text-neutral-700 dark:text-neutral-300">
						<li>You may underestimate content production time (3-6 month lag)</li>
						<li>Need clear KPIs for content marketer performance</li>
					</ul>
				</div>
				<div>
					<h4 class="font-semibold text-brand-600 dark:text-brand-400 mb-2">Next Steps:</h4>
					<ol class="list-decimal list-inside space-y-2 text-neutral-700 dark:text-neutral-300">
						<li>Define content goals: SEO, thought leadership, or conversion?</li>
						<li>Write job description with clear 90-day success metrics</li>
						<li>Budget $15K for ad testing in Q2 once content is live</li>
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
