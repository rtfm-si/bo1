<script lang="ts">
	/**
	 * Context Layout - Simple wrapper for context pages
	 * Navigation is handled by the header, so no tabs needed here.
	 */
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();
</script>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	{@render children()}
</div>
