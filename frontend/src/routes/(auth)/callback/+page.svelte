<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { handleOAuthCallback } from '$lib/stores/auth';

	let isLoading = true;
	let error: string | null = null;
	let statusMessage = 'Processing sign-in...';

	onMount(async () => {
		try {
			// Check for OAuth errors
			const errorParam = $page.url.searchParams.get('error');
			if (errorParam) {
				const errorDescription = $page.url.searchParams.get('error_description');
				throw new Error(`OAuth error: ${errorDescription || errorParam}`);
			}

			// Get authorization code from query params (PKCE flow)
			const code = $page.url.searchParams.get('code');
			if (!code) {
				throw new Error('Missing authorization code from OAuth provider');
			}

			// Retrieve PKCE code verifier from sessionStorage
			const codeVerifier = sessionStorage.getItem('pkce_code_verifier');
			if (!codeVerifier) {
				throw new Error('PKCE code verifier not found. Please try signing in again.');
			}

			// Clear the code verifier from storage (one-time use)
			sessionStorage.removeItem('pkce_code_verifier');

			// Exchange code for session via backend (with PKCE verifier)
			statusMessage = 'Verifying with server...';
			const redirectUri = `${window.location.origin}/callback`;

			await handleOAuthCallback(code, redirectUri, codeVerifier);

			// Success - redirect to dashboard
			statusMessage = 'Sign-in successful! Redirecting...';
			setTimeout(() => {
				goto('/dashboard');
			}, 1000);

		} catch (err) {
			console.error('OAuth callback failed:', err);
			isLoading = false;

			if (err instanceof Error) {
				error = err.message;
				// Log full error details for debugging
				console.error('Full error:', err);
			} else {
				error = 'Failed to complete sign-in. Please try again.';
			}
		}
	});

	function handleRetry() {
		goto('/login');
	}
</script>

<svelte:head>
	<title>Signing in... - Board of One</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 px-4">
	<div class="max-w-md w-full">
		<div class="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8 border border-slate-200 dark:border-slate-700">

			{#if isLoading}
				<!-- Loading state -->
				<div class="text-center">
					<div class="mb-6">
						<svg class="animate-spin h-12 w-12 text-blue-600 dark:text-blue-400 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
					</div>

					<h2 class="text-2xl font-semibold text-slate-900 dark:text-white mb-2">
						Signing you in
					</h2>

					<p class="text-slate-600 dark:text-slate-400">
						{statusMessage}
					</p>

					<div class="mt-4 flex items-center justify-center gap-2 text-sm text-slate-500 dark:text-slate-500">
						<span class="inline-block w-2 h-2 bg-blue-600 dark:bg-blue-400 rounded-full animate-pulse"></span>
						<span>This should only take a moment...</span>
					</div>
				</div>
			{:else if error}
				<!-- Error state -->
				<div class="text-center">
					<div class="mb-6">
						<svg class="h-12 w-12 text-red-600 dark:text-red-400 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
						</svg>
					</div>

					<h2 class="text-2xl font-semibold text-slate-900 dark:text-white mb-2">
						Sign-in failed
					</h2>

					<div class="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
						<p class="text-sm text-red-900 dark:text-red-200">
							{error}
						</p>
					</div>

					{#if error.includes('closed_beta') || error.includes('whitelist')}
						<p class="mb-6 text-slate-600 dark:text-slate-400 text-sm">
							We're currently in closed beta.
							<a href="/waitlist" class="text-blue-600 dark:text-blue-400 hover:underline">
								Join our waitlist
							</a> to get early access.
						</p>
					{/if}

					<button
						on:click={handleRetry}
						class="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200"
					>
						Try again
					</button>

					<a href="/" class="block mt-4 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200">
						← Back to home
					</a>
				</div>
			{/if}
		</div>
	</div>
</div>
