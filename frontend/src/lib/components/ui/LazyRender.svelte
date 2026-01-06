<script lang="ts">
	/**
	 * LazyRender - Renders children only when visible in viewport
	 * Uses IntersectionObserver for efficient visibility detection
	 *
	 * Usage:
	 * <LazyRender height={150}>
	 *   <ExpensiveComponent />
	 * </LazyRender>
	 */

	import { untrack } from 'svelte';

	interface Props {
		/** Minimum height for placeholder (prevents layout shift) */
		height?: number;
		/** Root margin for intersection observer (loads items earlier) */
		rootMargin?: string;
		/** Unique key for the item (helps with keyed each blocks) */
		key?: string | number;
		/** CSS class for wrapper */
		class?: string;
		/** Children to render when visible */
		children: any;
	}

	let {
		height = 100,
		rootMargin = '100px 0px',
		key,
		class: className = '',
		children,
	}: Props = $props();

	let element: HTMLDivElement | null = $state(null);
	let isVisible = $state(false);
	let hasBeenVisible = $state(false);

	$effect(() => {
		if (!element) return;

		const observer = new IntersectionObserver(
			(entries) => {
				// Defer state mutations to avoid state_unsafe_mutation
				// Use setTimeout(0) not queueMicrotask - microtasks can still be in same render batch
				setTimeout(() => {
					for (const entry of entries) {
						if (entry.isIntersecting) {
							isVisible = true;
							hasBeenVisible = true;
						} else {
							isVisible = false;
						}
					}
				}, 0);
			},
			{
				rootMargin,
				threshold: 0,
			}
		);

		observer.observe(element);

		return () => observer.disconnect();
	});
</script>

<div
	bind:this={element}
	class={className}
	style={!hasBeenVisible ? `min-height: ${height}px` : undefined}
>
	{#if hasBeenVisible}
		{@render children()}
	{:else}
		<!-- Placeholder skeleton -->
		<div class="animate-pulse bg-slate-100 dark:bg-slate-800 rounded-lg" style="height: {height}px">
		</div>
	{/if}
</div>
