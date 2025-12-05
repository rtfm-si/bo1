<script lang="ts" generics="T">
	/**
	 * VirtualizedList - A simple virtualized list component for Svelte 5
	 * Only renders items that are visible in the viewport plus a buffer
	 *
	 * Usage:
	 * <VirtualizedList items={myItems} itemHeight={100}>
	 *   {#snippet children(item, index)}
	 *     <MyItemComponent {item} />
	 *   {/snippet}
	 * </VirtualizedList>
	 */

	import { untrack } from 'svelte';

	interface Props {
		items: T[];
		itemHeight: number;
		bufferSize?: number;
		containerHeight?: string;
		class?: string;
		children: (item: T, index: number) => any;
	}

	let {
		items,
		itemHeight,
		bufferSize = 5,
		containerHeight = 'calc(100vh - 400px)',
		class: className = '',
		children,
	}: Props = $props();

	let containerRef: HTMLDivElement | null = $state(null);
	let scrollTop = $state(0);
	let containerClientHeight = $state(600);

	// Calculate visible range
	const totalHeight = $derived(items.length * itemHeight);

	const visibleStartIndex = $derived(
		Math.max(0, Math.floor(scrollTop / itemHeight) - bufferSize)
	);

	const visibleEndIndex = $derived(
		Math.min(
			items.length,
			Math.ceil((scrollTop + containerClientHeight) / itemHeight) + bufferSize
		)
	);

	const visibleItems = $derived(items.slice(visibleStartIndex, visibleEndIndex));

	const offsetY = $derived(visibleStartIndex * itemHeight);

	function handleScroll(event: Event) {
		const target = event.target as HTMLDivElement;
		scrollTop = target.scrollTop;
	}

	// Initialize container height on mount
	$effect(() => {
		if (containerRef) {
			containerClientHeight = containerRef.clientHeight;

			const resizeObserver = new ResizeObserver((entries) => {
				for (const entry of entries) {
					containerClientHeight = entry.contentRect.height;
				}
			});

			resizeObserver.observe(containerRef);

			return () => resizeObserver.disconnect();
		}
	});
</script>

<div
	bind:this={containerRef}
	class="overflow-y-auto {className}"
	style="height: {containerHeight};"
	onscroll={handleScroll}
>
	<div style="height: {totalHeight}px; position: relative;">
		<div style="transform: translateY({offsetY}px);">
			{#each visibleItems as item, i (visibleStartIndex + i)}
				{@render children(item, visibleStartIndex + i)}
			{/each}
		</div>
	</div>
</div>
