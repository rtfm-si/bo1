<script lang="ts">
	/**
	 * Redirect to unified Context Metrics page
	 * Key Metrics functionality has been consolidated into context/metrics
	 * Dashboard ValueMetricsPanel provides the focused view
	 */
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		goto('/context/metrics', { replaceState: true });
	});
</script>

<div class="min-h-screen flex items-center justify-center">
	<p class="text-neutral-500">Redirecting to Metrics...</p>
</div>
