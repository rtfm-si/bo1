<script lang="ts">
	/**
	 * Tooltip Component - Hover-triggered contextual information
	 * Used for explaining advisor expertise, truncated text, etc.
	 */

	import { onMount } from 'svelte';

	// Props
	export let text: string;
	export let position: 'top' | 'bottom' | 'left' | 'right' = 'top';
	export let variant: 'dark' | 'light' = 'dark';

	// State
	let visible = false;
	let tooltipElement: HTMLDivElement;
	let triggerElement: HTMLDivElement;

	// Variant styles
	const variants = {
		dark: 'bg-neutral-900 text-white dark:bg-neutral-800',
		light: 'bg-white text-neutral-900 border border-neutral-200 dark:bg-neutral-100 dark:text-neutral-900',
	};

	// Position styles
	const positions = {
		top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
		bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
		left: 'right-full top-1/2 -translate-y-1/2 mr-2',
		right: 'left-full top-1/2 -translate-y-1/2 ml-2',
	};

	// Arrow positions
	const arrowPositions = {
		top: 'top-full left-1/2 -translate-x-1/2 -mt-1',
		bottom: 'bottom-full left-1/2 -translate-x-1/2 -mb-1',
		left: 'left-full top-1/2 -translate-y-1/2 -ml-1',
		right: 'right-full top-1/2 -translate-y-1/2 -mr-1',
	};

	// Arrow rotations
	const arrowRotations = {
		top: 'rotate-180',
		bottom: '',
		left: 'rotate-90',
		right: '-rotate-90',
	};

	// Show/hide handlers
	function show() {
		visible = true;
	}

	function hide() {
		visible = false;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			hide();
		}
	}

	// Compute classes
	$: tooltipClasses = [
		'absolute z-tooltip px-2 py-1 text-xs rounded shadow-lg',
		'whitespace-nowrap pointer-events-none',
		'transition-opacity duration-150',
		visible ? 'opacity-100' : 'opacity-0',
		variants[variant],
		positions[position],
	].join(' ');

	$: arrowClasses = [
		'absolute w-2 h-2',
		variants[variant],
		arrowPositions[position],
		arrowRotations[position],
	].join(' ');
</script>

<div
	class="relative inline-block"
	bind:this={triggerElement}
	on:mouseenter={show}
	on:mouseleave={hide}
	on:focus={show}
	on:blur={hide}
	on:keydown={handleKeydown}
	role="button"
	tabindex="0"
>
	<!-- Trigger (slot) -->
	<slot />

	<!-- Tooltip -->
	{#if visible}
		<div
			bind:this={tooltipElement}
			class={tooltipClasses}
			role="tooltip"
		>
			{text}
			<!-- Arrow -->
			<div
				class={arrowClasses}
				style="clip-path: polygon(50% 0%, 0% 100%, 100% 100%);"
			></div>
		</div>
	{/if}
</div>
