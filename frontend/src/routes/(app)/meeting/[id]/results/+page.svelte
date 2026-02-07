<script lang="ts">
	/**
	 * Results Page - Redirects to Meeting Page
	 *
	 * The results view has been consolidated into the meeting page's Summary tab.
	 * This page now redirects users to the meeting page where they can view
	 * the synthesis and export a PDF report.
	 */
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	const sessionId = $page.params.id;

	onMount(() => {
		// Redirect to meeting page - Summary tab will be auto-selected for completed meetings
		goto(`/meeting/${sessionId}`, { replaceState: true });
	});
</script>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex items-center justify-center">
	<div class="text-center">
		<Spinner size="lg" class="mx-auto mb-4" />
		<p class="text-neutral-600 dark:text-neutral-400">Redirecting to meeting...</p>
	</div>
</div>
