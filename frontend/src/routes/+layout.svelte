<script lang="ts">
	import { onMount } from 'svelte';
	import '../app.css';
	import CookieConsent from '$lib/components/CookieConsent.svelte';
	import { initAuth } from '$lib/stores/auth';
	import { initializeTheme } from '$lib/design/themes';

	onMount(() => {
		// Initialize theme system on app mount
		initializeTheme();

		// Initialize authentication state on app mount
		initAuth();
	});
</script>

<slot />

<CookieConsent />
