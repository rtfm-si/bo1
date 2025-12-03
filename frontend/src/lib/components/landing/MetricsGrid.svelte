<script lang="ts">
	/**
	 * Metrics Grid - Quantified value metrics section.
	 */
	interface Metric {
		value: string;
		label: string;
		description: string;
	}

	interface Props {
		metrics: readonly Metric[];
		visible: boolean;
	}

	let { metrics, visible }: Props = $props();
</script>

<section
	id="metrics-section"
	class="py-16 bg-white dark:bg-neutral-900 border-y border-neutral-200 dark:border-neutral-800"
>
	<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
		<div class="grid grid-cols-2 lg:grid-cols-4 gap-8 md:gap-12">
			{#each metrics as metric, i}
				<div class="text-center metric-card" class:stagger-item={visible}>
					<div
						class="metric-value text-4xl md:text-5xl font-extrabold text-brand-600 dark:text-brand-400 mb-2 emphasis-word"
					>
						{metric.value}
					</div>
					<div class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-1">
						{metric.label}
					</div>
					<div class="text-sm text-neutral-600 dark:text-neutral-400">
						{metric.description}
					</div>
				</div>
			{/each}
		</div>
	</div>
</section>

<style>
	/* Pulse for metrics */
	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
			transform: scale(1);
		}
		50% {
			opacity: 0.9;
			transform: scale(1.05);
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

	/* Staggered fade-in animations */
	.stagger-item {
		opacity: 0;
		animation: fadeInUp 0.6s ease forwards;
	}

	.stagger-item:nth-child(1) {
		animation-delay: 0.1s;
	}
	.stagger-item:nth-child(2) {
		animation-delay: 0.2s;
	}
	.stagger-item:nth-child(3) {
		animation-delay: 0.3s;
	}
	.stagger-item:nth-child(4) {
		animation-delay: 0.4s;
	}

	/* Metric pulse */
	.metric-card:hover .metric-value {
		animation: pulse 2s ease-in-out infinite;
	}
</style>
