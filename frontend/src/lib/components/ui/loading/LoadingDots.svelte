<script lang="ts">
	/**
	 * LoadingDots - AI Thinking Indicator
	 *
	 * Three-dot animation used for AI "thinking" states.
	 * Based on UX research: staggered bounce perceived as more responsive.
	 */

	interface Props {
		variant?: 'thinking' | 'typing';
		size?: 'sm' | 'md' | 'lg';
		class?: string;
	}

	let { variant = 'thinking', size = 'md', class: className = '' }: Props = $props();

	const sizeMap = {
		sm: { dot: 'w-1 h-1', gap: 'gap-1' },
		md: { dot: 'w-1.5 h-1.5', gap: 'gap-1.5' },
		lg: { dot: 'w-2 h-2', gap: 'gap-2' },
	};

	const variantMap = {
		thinking: 'bg-brand-500 dark:bg-brand-400',
		typing: 'bg-neutral-400 dark:bg-neutral-500',
	};

	const dotClass = $derived([
		'rounded-full',
		sizeMap[size].dot,
		variantMap[variant],
	].join(' '));
</script>

<div
	class="inline-flex items-center {sizeMap[size].gap} {className}"
	role="status"
	aria-label="Loading"
>
	<span class="{dotClass} animate-loading-dot" style="animation-delay: 0ms"></span>
	<span class="{dotClass} animate-loading-dot" style="animation-delay: 150ms"></span>
	<span class="{dotClass} animate-loading-dot" style="animation-delay: 300ms"></span>
	<span class="sr-only">Loading...</span>
</div>

<style>
	@keyframes loading-dot {
		0%, 80%, 100% {
			transform: translateY(0);
			opacity: 0.6;
		}
		40% {
			transform: translateY(-4px);
			opacity: 1;
		}
	}

	.animate-loading-dot {
		animation: loading-dot 1s ease-in-out infinite;
	}

	@media (prefers-reduced-motion: reduce) {
		.animate-loading-dot {
			animation: none;
			opacity: 0.8;
		}
	}
</style>
