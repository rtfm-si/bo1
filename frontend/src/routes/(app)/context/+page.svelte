<script lang="ts">
	/**
	 * Context Index - Redirects to overview
	 */
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	onMount(() => {
		// Preserve query params when redirecting (e.g., ?welcome=true)
		const queryString = $page.url.search;
		goto(`/context/overview${queryString}`, { replaceState: true });
	});
</script>

<!-- Fallback while redirecting -->
<div class="flex items-center justify-center py-12">
	<Spinner size="lg" />
</div>
