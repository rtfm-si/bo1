<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import '../app.css';
	import CookieConsent from '$lib/components/CookieConsent.svelte';
	import { initAuth } from '$lib/stores/auth';
	import { initializeTheme } from '$lib/design/themes';
	import { initSuperTokens } from '$lib/supertokens';

	onMount(() => {
		// Initialize SuperTokens SDK first
		initSuperTokens();

		// Initialize theme system on app mount
		initializeTheme();

		// Don't initialize auth on callback page - let callback complete OAuth first
		// initAuth will be called after redirect to dashboard
		if ($page.url.pathname !== '/callback') {
			initAuth();
		}
	});
</script>

<slot />

<CookieConsent />
