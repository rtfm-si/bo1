<script lang="ts">
	/**
	 * Context Index - Redirects to overview
	 */
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		// Preserve query params when redirecting (e.g., ?welcome=true)
		const queryString = $page.url.search;
		goto(`/context/overview${queryString}`, { replaceState: true });
	});
</script>

<!-- Fallback while redirecting -->
<div class="flex items-center justify-center py-12">
	<div class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"></div>
</div>
