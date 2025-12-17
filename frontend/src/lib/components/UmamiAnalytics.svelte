<script lang="ts">
	/**
	 * Umami Analytics Script Loader
	 *
	 * Conditionally injects Umami tracking script when PUBLIC_UMAMI_WEBSITE_ID is configured.
	 * SSR-safe: only loads in browser environment.
	 *
	 * Usage: Add <UmamiAnalytics /> to root +layout.svelte
	 *
	 * Custom event tracking (optional):
	 *   window.umami?.track('event-name', { key: 'value' });
	 */
	import { onMount } from 'svelte';
	import { env } from '$env/dynamic/public';

	const umamiHost = env.PUBLIC_UMAMI_HOST;
	const websiteId = env.PUBLIC_UMAMI_WEBSITE_ID;
	const enabled = !!websiteId && !!umamiHost;

	onMount(() => {
		if (!enabled) return;

		// Check if script already exists
		if (document.querySelector(`script[data-website-id="${websiteId}"]`)) {
			return;
		}

		// Dynamically inject Umami script
		const script = document.createElement('script');
		script.defer = true;
		script.src = `${umamiHost}/script.js`;
		script.dataset.websiteId = websiteId;
		document.head.appendChild(script);
	});
</script>
