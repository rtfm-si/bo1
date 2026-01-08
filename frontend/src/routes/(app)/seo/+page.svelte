<script lang="ts">
	/**
	 * Redirect to Advisor Grow page
	 */
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/advisor/grow', { replaceState: true });
	});
</script>

<div class="min-h-screen flex items-center justify-center">
	<p class="text-neutral-500">Redirecting to Advisor...</p>
</div>
