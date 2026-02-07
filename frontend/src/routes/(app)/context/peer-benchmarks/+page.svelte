<script lang="ts">
	/**
	 * Redirect: /context/peer-benchmarks -> /reports/benchmarks?tab=peer
	 * Peer benchmarks have been consolidated into the Reports > Benchmarks page.
	 */
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	onMount(() => {
		goto('/reports/benchmarks?tab=peer', { replaceState: true });
	});
</script>

<div class="flex items-center justify-center py-12">
	<div class="text-center">
		<Spinner size="lg" class="mx-auto mb-4" />
		<p class="text-neutral-500 dark:text-neutral-400">Redirecting to Benchmarks...</p>
	</div>
</div>
