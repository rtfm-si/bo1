<script lang="ts">
	import { onMount } from 'svelte';
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/stores';
	import '../app.css';

	// Scroll to top on navigation (standard UX behavior)
	afterNavigate(() => {
		window.scrollTo(0, 0);
	});
	import CookieConsent from '$lib/components/CookieConsent.svelte';
	import UmamiAnalytics from '$lib/components/UmamiAnalytics.svelte';
	import { initAuth } from '$lib/stores/auth';
	import { initSuperTokens } from '$lib/supertokens';
	import { themeStore } from '$lib/stores/theme';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	onMount(() => {
		// Initialize SuperTokens SDK first
		initSuperTokens();

		// Initialize theme system - auto-follows system preference
		themeStore.initialize();

		// Don't initialize auth on callback page - let callback complete OAuth first
		// initAuth will be called after redirect to dashboard
		if ($page.url.pathname !== '/callback') {
			initAuth();
		}
	});
</script>

<!-- SSR-safe theme initialization script - runs before hydration -->
<svelte:head>
	<script>
		// Immediately apply theme before page renders to prevent FOUC
		(function() {
			if (typeof window === 'undefined') return;

			const stored = localStorage.getItem('theme');
			const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
			const mode = stored || 'auto';
			const effectiveTheme = mode === 'auto' ? (systemDark ? 'dark' : 'light') : mode;

			const root = document.documentElement;

			// Add theme classes immediately
			if (mode === 'auto') {
				root.classList.add('theme-auto', `theme-${effectiveTheme}`);
			} else {
				root.classList.add(`theme-${effectiveTheme}`);
			}

			// Add dark class for dark/ocean themes
			if (effectiveTheme === 'dark' || effectiveTheme === 'ocean') {
				root.classList.add('dark');
			}
		})();
	</script>
</svelte:head>

{@render children()}

<CookieConsent />
<UmamiAnalytics />
