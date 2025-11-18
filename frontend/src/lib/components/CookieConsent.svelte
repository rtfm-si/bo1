<script lang="ts">
	/**
	 * Cookie Consent Banner - Uses design system components
	 */

	import { onMount } from 'svelte';
	import Cookies from 'js-cookie';
	import { Button } from '$lib/components/ui';

	let showBanner = false;
	const CONSENT_COOKIE = 'bo1_cookie_consent';

	onMount(() => {
		// Check if user has already given consent
		const existingConsent = Cookies.get(CONSENT_COOKIE);
		if (!existingConsent) {
			showBanner = true;
		}
	});

	function acceptAll() {
		// Store consent with analytics enabled
		Cookies.set(
			CONSENT_COOKIE,
			JSON.stringify({
				essential: true,
				analytics: true,
				timestamp: new Date().toISOString()
			}),
			{ expires: 365 }
		);

		showBanner = false;

		// TODO: Enable analytics tracking here (e.g., Google Analytics)
		console.log('Analytics cookies accepted');
	}

	function acceptEssential() {
		// Store consent with only essential cookies
		Cookies.set(
			CONSENT_COOKIE,
			JSON.stringify({
				essential: true,
				analytics: false,
				timestamp: new Date().toISOString()
			}),
			{ expires: 365 }
		);

		showBanner = false;
		console.log('Only essential cookies accepted');
	}
</script>

{#if showBanner}
	<div
		class="fixed bottom-0 left-0 right-0 bg-neutral-900 dark:bg-neutral-950 text-white p-6 shadow-2xl z-50 border-t border-neutral-700"
	>
		<div
			class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4"
		>
			<div class="flex-1">
				<h3 class="text-lg font-semibold mb-2">Cookie Consent</h3>
				<p class="text-neutral-300 text-sm">
					We use cookies to enhance your experience. Essential cookies are required for
					authentication. Analytics cookies help us improve the service (optional).
				</p>
			</div>

			<div class="flex gap-3">
				<Button variant="secondary" size="md" on:click={acceptEssential}>
					Essential Only
				</Button>
				<Button variant="brand" size="md" on:click={acceptAll}>
					Accept All
				</Button>
			</div>
		</div>
	</div>
{/if}
