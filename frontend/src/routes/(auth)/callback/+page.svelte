<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { initSuperTokens } from '$lib/supertokens';
	import ThirdParty from "supertokens-web-js/recipe/thirdparty";

	let error: string | null = null;

	onMount(async () => {
		// Initialize SuperTokens
		initSuperTokens();

		try {
			// Handle OAuth callback - SuperTokens exchanges code for tokens
			// and creates session with httpOnly cookies
			await ThirdParty.signInAndUp();

			// Success! Redirect to dashboard
			goto('/dashboard');
		} catch (err: any) {
			console.error("OAuth callback error:", err);
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
{:else}
	<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 px-4">
		<div class="max-w-md w-full bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8 border border-slate-200 dark:border-slate-700">
			<div class="text-center">
				<div class="mx-auto flex items-center justify-center mb-4">
					<svg class="animate-spin h-12 w-12 text-blue-600 dark:text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
				</div>
				<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-2">
					Completing sign in...
				</h2>
				<p class="text-slate-600 dark:text-slate-400">
					Please wait while we verify your account.
				</p>
			</div>
		</div>
	</div>
{/if}
