<script lang="ts">
	/**
	 * Reports Index - Redirects to competitors
	 */
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/reports/competitors', { replaceState: true });
	});
</script>

<!-- Fallback while redirecting -->
<div class="flex items-center justify-center py-12">
	<div class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"></div>
</div>
