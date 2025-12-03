<script lang="ts">
	/**
	 * Context Layout - Simple wrapper for context pages
	 * Navigation is handled by the sidebar, so no tabs needed here.
	 */
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();
</script>

{@render children()}
