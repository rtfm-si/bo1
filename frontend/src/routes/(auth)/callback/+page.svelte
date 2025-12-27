<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { initSuperTokens } from '$lib/supertokens';
	import { initAuth } from '$lib/stores/auth';
	import { ActivityStatus, LOADING_MESSAGES } from '$lib/components/ui/loading';
	import ThirdParty from "supertokens-web-js/recipe/thirdparty";
	import TermsConsentModal from '$lib/components/TermsConsentModal.svelte';
	import { apiClient } from '$lib/api/client';

	let error = $state<string | null>(null);
	let showTermsModal = $state(false);
	let isCheckingTerms = $state(false);

	async function checkTermsConsent(): Promise<boolean> {
		try {
			const status = await apiClient.getTermsConsentStatus();
			return status.has_consented;
		} catch (err) {
			// If no active T&C or API error, consider consented to avoid blocking
			console.warn('[Callback] Terms consent check failed:', err);
			return true;
		}
	}

	function handleTermsAccept() {
		showTermsModal = false;
		goto('/dashboard');
	}

	onMount(async () => {
		console.log('[Callback] Starting OAuth callback processing...');
		console.log('[Callback] URL:', window.location.href);
		console.log('[Callback] Search params:', window.location.search);

		// Initialize SuperTokens
		initSuperTokens();

		try {
			// Handle OAuth callback - SuperTokens exchanges code for tokens
			// and creates session with httpOnly cookies
			console.log('[Callback] Calling ThirdParty.signInAndUp()...');
			const response = await ThirdParty.signInAndUp();
			console.log('[Callback] signInAndUp response:', response);

			// Check if sign-in was successful
			if (response.status === 'OK') {
				console.log('[Callback] Sign-in successful!');

				// Wait a moment for cookies to be fully set
				await new Promise(resolve => setTimeout(resolve, 100));

				// Initialize auth store with the new session (sets up CSRF cookie)
				console.log('[Callback] Initializing auth store...');
				await initAuth();

				// Record GDPR consent if pending from login page
				// Must be after initAuth() so CSRF cookie is available for apiClient
				const gdprConsentPending = localStorage.getItem('gdpr_consent_pending');
				if (gdprConsentPending === 'true') {
					try {
						await apiClient.recordGdprConsent();
						console.log('[Callback] GDPR consent recorded');
					} catch (consentErr) {
						console.warn('[Callback] Failed to record GDPR consent:', consentErr);
					} finally {
						localStorage.removeItem('gdpr_consent_pending');
					}
				}

				// Check T&C consent before redirecting
				console.log('[Callback] Checking T&C consent...');
				isCheckingTerms = true;
				const hasConsented = await checkTermsConsent();
				isCheckingTerms = false;

				if (!hasConsented) {
					console.log('[Callback] User needs to accept T&C');
					showTermsModal = true;
					return; // Don't redirect - wait for modal acceptance
				}

				console.log('[Callback] Redirecting to dashboard...');
				// Success! Redirect to dashboard
				goto('/dashboard');
			} else {
				console.error('[Callback] Sign-in failed with status:', response.status);
				error = 'Authentication failed. Please try again.';
				setTimeout(() => goto('/login'), 3000);
			}
		} catch (err: any) {
			console.error('[Callback] OAuth callback error:', err);
			console.error('[Callback] Error details:', JSON.stringify(err, null, 2));
			error = err.message || "Authentication failed";

			// Wait 3 seconds, then redirect to login
			setTimeout(() => goto('/login'), 3000);
		}
	});
</script>

<svelte:head>
	<title>Completing sign in...</title>
</svelte:head>

{#if error}
	<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 px-4">
		<div class="max-w-md w-full bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8 border border-slate-200 dark:border-slate-700">
			<div class="text-center">
				<div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 dark:bg-red-900/20 mb-4">
					<svg class="h-6 w-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</div>
				<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-2">
					Authentication Failed
				</h2>
				<p class="text-slate-600 dark:text-slate-400 mb-4">
					{error}
				</p>
				<p class="text-sm text-slate-500 dark:text-slate-500">
					Redirecting to login...
				</p>
			</div>
		</div>
	</div>
{:else if showTermsModal}
	<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 px-4">
		<TermsConsentModal bind:open={showTermsModal} onAccept={handleTermsAccept} />
	</div>
{:else}
	<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 px-4">
		<div class="max-w-md w-full bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8 border border-slate-200 dark:border-slate-700">
			<ActivityStatus
				variant="card"
				message={isCheckingTerms ? 'Checking terms...' : LOADING_MESSAGES.auth.completing}
				phase="Please wait while we verify your account."
			/>
		</div>
	</div>
{/if}
