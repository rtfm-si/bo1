<script lang="ts">
	/**
	 * Cookie Consent Banner - Uses design system components
	 * Auto-hides during active meetings to reduce distraction
	 */

	import { onMount } from 'svelte';
	import Cookies from 'js-cookie';
	import { Button } from '$lib/components/ui';
	import { activeMeeting } from '$lib/stores/meeting';

	let needsConsent = $state(false);
	const CONSENT_COOKIE = 'bo1_cookie_consent';

	// Pre-read store to ensure subscription happens outside reactive context
	// This prevents state_unsafe_mutation when store is first accessed in $derived
	$activeMeeting;

	// Derived: show banner only if consent needed AND no active meeting
	let shouldShow = $derived(needsConsent && !$activeMeeting.isActive);

	onMount(() => {
		// Check if user has already given consent
		const existingConsent = Cookies.get(CONSENT_COOKIE);
		if (!existingConsent) {
			needsConsent = true;
		}
	});

	function acceptAll() {
		// Store consent with analytics enabled
		// Essential: Auth tokens, consent preference, session data
		// Analytics: Usage tracking, performance monitoring (when implemented)
		Cookies.set(
			CONSENT_COOKIE,
			JSON.stringify({
				essential: true,
				analytics: true,
				timestamp: new Date().toISOString()
			}),
			{ expires: 365, sameSite: 'Lax', secure: true }
		);

		needsConsent = false;

		// TODO: Enable analytics tracking here (e.g., Plausible Analytics)
		// Note: We use privacy-friendly analytics (Plausible/Fathom), not Google Analytics
		console.log('Analytics cookies accepted');
	}

	function acceptEssential() {
		// Store consent with only essential cookies
		// Essential cookies used:
		// - bo1_cookie_consent: Stores this preference (this cookie)
		// - auth tokens: Supabase JWT (when auth enabled)
		// - theme preference: Stored in localStorage (not a cookie)
		Cookies.set(
			CONSENT_COOKIE,
			JSON.stringify({
				essential: true,
				analytics: false,
				timestamp: new Date().toISOString()
			}),
			{ expires: 365, sameSite: 'Lax', secure: true }
		);

		needsConsent = false;
		console.log('Only essential cookies accepted');
	}
</script>

{#if shouldShow}
	<div
		class="fixed bottom-0 left-0 right-0 bg-neutral-900 dark:bg-neutral-950 text-white p-6 shadow-2xl z-50 border-t border-neutral-700"
	>
		<div
			class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4"
		>
			<div class="flex-1">
				<h3 class="text-lg font-semibold mb-2">Cookie Consent</h3>
				<p class="text-neutral-300 text-sm">
					We use cookies to enhance your experience. Essential cookies (authentication, preferences) are necessary for the site to function. Optional analytics cookies help us improve the service.
					<a href="/privacy" class="underline hover:text-neutral-100 ml-1">Learn more</a>
				</p>
			</div>

			<div class="flex flex-col sm:flex-row gap-3">
				<Button variant="ghost" size="md" onclick={acceptEssential}>
					Essential Only
				</Button>
				<Button variant="brand" size="md" onclick={acceptAll}>
					Accept All
				</Button>
			</div>
		</div>
	</div>
{/if}
