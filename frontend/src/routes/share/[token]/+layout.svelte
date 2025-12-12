<script lang="ts">
	/**
	 * Public share layout - minimal header, no navigation
	 * No authentication required for public share pages
	 */
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();
</script>

<svelte:head>
	<meta name="robots" content="noindex, nofollow" />
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Minimal Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<a href="/" class="flex items-center gap-2 text-xl font-semibold text-neutral-900 dark:text-white">
				<svg class="w-8 h-8" viewBox="0 0 32 32" fill="currentColor" aria-hidden="true">
					<circle cx="16" cy="16" r="14" class="text-brand-500" />
					<text x="16" y="21" font-size="14" text-anchor="middle" fill="white" font-weight="bold">B1</text>
				</svg>
				<span>Board of One</span>
			</a>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{@render children()}
	</main>

	<!-- Footer -->
	<footer class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-center">
		<p class="text-sm text-neutral-500 dark:text-neutral-400">
			Powered by <a href="/" class="text-brand-600 dark:text-brand-400 hover:underline">Board of One</a>
		</p>
	</footer>
</div>
