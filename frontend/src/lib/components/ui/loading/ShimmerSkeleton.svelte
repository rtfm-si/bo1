<script lang="ts">
	/**
	 * ShimmerSkeleton - Content Placeholder with Shimmer Animation
	 *
	 * Research shows shimmer animation perceived 20-30% faster than pulse.
	 * Left-to-right sweep matches reading direction for Western users.
	 */

	interface Props {
		type?: 'text' | 'card' | 'avatar' | 'button' | 'custom';
		lines?: number;
		class?: string;
		width?: string;
		height?: string;
	}

	let {
		type = 'text',
		lines = 3,
		class: className = '',
		width,
		height
	}: Props = $props();
</script>

{#if type === 'text'}
	<div class="space-y-2 {className}" role="status" aria-label="Loading content">
		{#each Array(lines) as _, i (i)}
			<div
				class="skeleton-shimmer h-4 rounded {i === lines - 1 ? 'w-3/4' : 'w-full'}"
			></div>
		{/each}
		<span class="sr-only">Loading...</span>
	</div>
{:else if type === 'card'}
	<div class="skeleton-shimmer rounded-lg p-4 {className}" role="status" aria-label="Loading card">
		<div class="flex items-start gap-3">
			<div class="w-10 h-10 rounded-full bg-neutral-200/50 dark:bg-neutral-700/50"></div>
			<div class="flex-1 space-y-2">
				<div class="h-4 w-1/3 rounded bg-neutral-200/50 dark:bg-neutral-700/50"></div>
				<div class="h-3 w-full rounded bg-neutral-200/50 dark:bg-neutral-700/50"></div>
				<div class="h-3 w-2/3 rounded bg-neutral-200/50 dark:bg-neutral-700/50"></div>
			</div>
		</div>
		<span class="sr-only">Loading...</span>
	</div>
{:else if type === 'avatar'}
	<div
		class="skeleton-shimmer rounded-full {className}"
		class:w-10={!width}
		class:h-10={!height}
		style:width={width}
		style:height={height}
		role="status"
		aria-label="Loading avatar"
	>
		<span class="sr-only">Loading...</span>
	</div>
{:else if type === 'button'}
	<div
		class="skeleton-shimmer h-10 rounded-lg {className}"
		class:w-24={!width}
		style:width={width}
		style:height={height}
		role="status"
		aria-label="Loading button"
	>
		<span class="sr-only">Loading...</span>
	</div>
{:else}
	<!-- Custom type - user provides dimensions via class or style -->
	<div
		class="skeleton-shimmer rounded {className}"
		style:width={width}
		style:height={height}
		role="status"
		aria-label="Loading"
	>
		<span class="sr-only">Loading...</span>
	</div>
{/if}

<style>
	.skeleton-shimmer {
		position: relative;
		overflow: hidden;
		background-color: rgb(229 231 235); /* neutral-200 */
	}

	:global(.dark) .skeleton-shimmer {
		background-color: rgb(55 65 81); /* neutral-700 */
	}

	.skeleton-shimmer::after {
		content: '';
		position: absolute;
		inset: 0;
		transform: translateX(-100%);
		background: linear-gradient(
			90deg,
			transparent 0%,
			rgba(255, 255, 255, 0.4) 50%,
			transparent 100%
		);
		animation: shimmer 1.5s ease-in-out infinite;
	}

	:global(.dark) .skeleton-shimmer::after {
		background: linear-gradient(
			90deg,
			transparent 0%,
			rgba(255, 255, 255, 0.1) 50%,
			transparent 100%
		);
	}

	@keyframes shimmer {
		100% {
			transform: translateX(100%);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.skeleton-shimmer::after {
			animation: none;
			transform: translateX(0);
			background: rgba(255, 255, 255, 0.2);
		}
	}
</style>
