<script lang="ts">
	/**
	 * Redirect to unified Mentor page (Analysis tab)
	 */
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/mentor?tab=analysis', { replaceState: true });
	});
</script>

<div class="min-h-screen flex items-center justify-center">
	<p class="text-neutral-500">Redirecting to Mentor...</p>
</div>
