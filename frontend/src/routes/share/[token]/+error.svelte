<script lang="ts">
	/**
	 * Error page for public shares - handles 404, 410, and other errors
	 */
	import { page } from '$app/stores';
	import { Link2Off, Clock, AlertCircle, Home } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';

	const statusCode = $derived($page.status);
	const errorTitle = $derived(
		statusCode === 404
			? 'Share Not Found'
			: statusCode === 410
				? 'Share Expired'
				: 'Error'
	);
	const errorDescription = $derived($page.error?.message || 'An unexpected error occurred while loading this share.');

	const iconMap = {
		404: Link2Off,
		410: Clock,
	} as const;

	const Icon = $derived(iconMap[statusCode as keyof typeof iconMap] || AlertCircle);

	// Compute title based on status code
	const pageTitle = $derived(
		statusCode === 404
			? 'Share Not Found | Board of One'
			: statusCode === 410
				? 'Share Expired | Board of One'
				: 'Error | Board of One'
	);
</script>

<svelte:head>
	<title>{pageTitle}</title>
</svelte:head>

<div class="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-6">
	<div class="w-16 h-16 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center">
		<Icon size={32} class="text-neutral-500 dark:text-neutral-400" />
	</div>

	<div class="space-y-2">
		<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
			{errorTitle}
		</h1>
		<p class="text-neutral-600 dark:text-neutral-400 max-w-md">
			{errorDescription}
		</p>
	</div>

	<div class="flex gap-3">
		<Button variant="brand" size="md" onclick={() => window.location.href = '/'}>
			{#snippet children()}
				<Home size={16} />
				<span>Go to Homepage</span>
			{/snippet}
		</Button>
	</div>
</div>
