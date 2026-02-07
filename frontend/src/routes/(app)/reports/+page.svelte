<script lang="ts">
	/**
	 * Reports Index - Redirects to competitors
	 */
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	onMount(() => {
		goto('/reports/competitors', { replaceState: true });
	});
</script>

<!-- Fallback while redirecting -->
<div class="flex items-center justify-center py-12">
	<Spinner size="lg" />
</div>
