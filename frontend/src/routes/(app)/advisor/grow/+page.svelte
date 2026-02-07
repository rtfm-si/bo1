<script lang="ts">
	/**
	 * Advisor - Grow Page
	 * SEO tools for content and growth
	 */
	import SeoTools from '$lib/components/seo/SeoTools.svelte';
</script>

<svelte:head>
	<title>Grow | Advisor | Board of One</title>
	<meta name="description" content="SEO tools and content generation to grow your business" />
</svelte:head>

<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-6">
	<div class="mb-6">
		<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">Grow</h1>
		<p class="mt-1 text-neutral-600 dark:text-neutral-400">
			SEO tools and content generation to grow your business presence.
		</p>
	</div>

	<SeoTools />
</div>
