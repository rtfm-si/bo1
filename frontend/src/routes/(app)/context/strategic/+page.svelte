<script lang="ts">
	/**
	 * Redirect to unified Context Overview page
	 * Strategic content has been consolidated into context/overview
	 * Trend data moved to reports/trends
	 */
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/context/overview', { replaceState: true });
	});
</script>

<div class="min-h-screen flex items-center justify-center">
	<p class="text-neutral-500">Redirecting to Context Overview...</p>
</div>
