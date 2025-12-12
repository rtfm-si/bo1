<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { initSuperTokens } from '$lib/supertokens';
	import ThirdParty from "supertokens-web-js/recipe/thirdparty";
	import { browser } from '$app/environment';
	import { env } from '$env/dynamic/public';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let gdprConsent = $state(false);

	// Redirect if already authenticated
	onMount(() => {
		// Initialize SuperTokens
		initSuperTokens();

		const unsubscribe = isAuthenticated.subscribe((authenticated) => {
			if (authenticated) {
				goto('/dashboard');
			}
		});

		// Check for error query param (from backend redirect)
		if (browser) {
			const params = new URLSearchParams(window.location.search);
			const errorParam = params.get('error');

			if (errorParam) {
				// Map error codes to user-friendly messages
				const errorMessages: Record<string, string> = {
					auth_init_failed: 'Failed to initiate sign-in. Please try again.',
					oauth_error: 'OAuth provider returned an error.',
					missing_parameters: 'Missing authorization parameters.',
					csrf_validation_failed: 'Security validation failed. Please try again.',
					state_expired: 'Sign-in session expired. Please try again.',
					invalid_state: 'Invalid sign-in state.',
					token_exchange_failed: 'Failed to exchange authorization code for tokens.',
					invalid_token_response: 'Invalid response from authentication server.',
					missing_user_data: 'Failed to get user data from Google.',
					closed_beta: 'Access limited to beta users. Join our waitlist!',
					callback_failed: 'Authentication callback failed. Please try again.',
				};

				error = errorMessages[errorParam] || 'Authentication failed. Please try again.';
			}
		}

		return unsubscribe;
	});

	/**
	 * Initiate Google OAuth flow via SuperTokens.
	 * Gets authorization URL from backend and redirects browser.
	 */
	async function handleGoogleSignIn() {
		// Require GDPR consent before proceeding
		if (!gdprConsent) {
			error = "Please accept the Privacy Policy to continue.";
			return;
		}

		isLoading = true;
		error = null;

		try {
			// Store GDPR consent in localStorage before OAuth redirect
			// Will be read by callback page and sent to backend
			localStorage.setItem('gdpr_consent_pending', 'true');

			// Get authorization URL from SuperTokens backend
			const authUrl = await ThirdParty.getAuthorisationURLWithQueryParamsAndSetState({
				thirdPartyId: "google",
				// Both frontendRedirectURI and redirectURIOnProviderDashboard should be the frontend callback
				// Google sends a GET request to the frontend, then frontend POSTs to backend /api/auth/signinup
				frontendRedirectURI: `${window.location.origin}/callback`,
				redirectURIOnProviderDashboard: `${window.location.origin}/callback`,
			});

			// Redirect browser to Google OAuth
			window.location.href = authUrl;
		} catch (err: any) {
			console.error("Failed to initiate Google sign-in:", err);
			error = "Failed to initiate sign-in. Please try again.";
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Sign In - Board of One</title>
	<meta name="description" content="Sign in to Board of One" />
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 px-4">
	<div class="max-w-md w-full">
		<!-- Logo -->
		<div class="text-center mb-8">
			<h1 class="text-4xl font-bold text-slate-900 dark:text-white mb-2">
				Board of One
			</h1>
			<p class="text-slate-600 dark:text-slate-400">
				AI-powered strategic decision-making
			</p>
		</div>

		<!-- Sign-in card -->
		<div class="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8 border border-slate-200 dark:border-slate-700">
			<h2 class="text-2xl font-semibold text-slate-900 dark:text-white mb-6">
				Sign in to continue
			</h2>

			<!-- Closed Beta Notice -->
			<div class="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
				<p class="text-sm text-blue-900 dark:text-blue-200">
					<span class="font-semibold">Closed Beta:</span> Access is currently limited to whitelisted users.
					<a href="/waitlist" class="underline hover:text-blue-700 dark:hover:text-blue-300">
						Join the waitlist
					</a>
				</p>
			</div>

			<!-- Error message -->
			{#if error}
				<div class="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
					<p class="text-sm text-red-900 dark:text-red-200">
						{error}
					</p>
					{#if error.includes('beta') || error.includes('whitelist')}
						<a href="/waitlist" class="block mt-2 text-sm text-red-900 dark:text-red-200 underline">
							Join our waitlist for early access
						</a>
					{/if}
				</div>
			{/if}

			<!-- GDPR Consent Checkbox -->
			<label class="flex items-start gap-3 mb-6 cursor-pointer">
				<input
					type="checkbox"
					bind:checked={gdprConsent}
					class="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-700"
				/>
				<span class="text-sm text-slate-600 dark:text-slate-400">
					I agree to the
					<a href="/legal/privacy" class="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 underline" target="_blank">Privacy Policy</a>
					and consent to the processing of my personal data as described therein.
				</span>
			</label>

			<!-- Google Sign-in Button -->
			<button
				onclick={handleGoogleSignIn}
				disabled={isLoading || !gdprConsent}
				class="w-full flex items-center justify-center gap-3 px-6 py-3 bg-white dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{#if isLoading}
					<Spinner size="sm" variant="neutral" ariaLabel="Signing in" />
					<span class="text-slate-700 dark:text-slate-300 font-medium">Redirecting...</span>
				{:else}
					<svg class="w-5 h-5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
						<path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
						<path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
						<path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
						<path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
					</svg>
					<span class="text-slate-700 dark:text-slate-300 font-medium">Sign in with Google</span>
				{/if}
			</button>

			<!-- LinkedIn and GitHub coming soon -->
			<div class="mt-4 space-y-2">
				<button
					disabled
					class="w-full flex items-center justify-center gap-3 px-6 py-3 bg-slate-100 dark:bg-slate-700/50 border-2 border-slate-200 dark:border-slate-700 rounded-lg cursor-not-allowed opacity-50"
				>
					<svg class="w-5 h-5" viewBox="0 0 24 24" fill="#0A66C2" xmlns="http://www.w3.org/2000/svg">
						<path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
					</svg>
					<span class="text-slate-500 dark:text-slate-400 font-medium">LinkedIn (Coming Soon)</span>
				</button>

				<button
					disabled
					class="w-full flex items-center justify-center gap-3 px-6 py-3 bg-slate-100 dark:bg-slate-700/50 border-2 border-slate-200 dark:border-slate-700 rounded-lg cursor-not-allowed opacity-50"
				>
					<svg class="w-5 h-5 text-slate-600 dark:text-slate-400" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
						<path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
					</svg>
					<span class="text-slate-500 dark:text-slate-400 font-medium">GitHub (Coming Soon)</span>
				</button>
			</div>

			<!-- Terms notice -->
			<p class="mt-6 text-xs text-center text-slate-500 dark:text-slate-400">
				By signing in, you also agree to our
				<a href="/legal/terms" class="underline hover:text-slate-700 dark:hover:text-slate-300">Terms of Service</a>.
			</p>
		</div>

		<!-- Back to home -->
		<div class="mt-6 text-center">
			<a href="/" class="text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
				← Back to home
			</a>
		</div>
	</div>
</div>
