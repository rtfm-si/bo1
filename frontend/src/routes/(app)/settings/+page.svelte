<script lang="ts">
	import { redirect } from '@sveltejs/kit';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	// Redirect to account settings on mount (client-side)
	onMount(() => {
		goto('/settings/account', { replaceState: true });
	});
</script>

<!-- Fallback while redirecting -->
<div class="flex items-center justify-center py-12">
	<Spinner size="lg" />
</div>
