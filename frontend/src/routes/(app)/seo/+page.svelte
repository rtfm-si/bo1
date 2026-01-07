<script lang="ts">
	/**
	 * SEO Page - Redirects to Assistant SEO tab
	 */
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/mentor?tab=seo', { replaceState: true });
	});
</script>

<div class="min-h-screen flex items-center justify-center">
	<p class="text-neutral-500">Redirecting to Assistant...</p>
</div>
