<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	let status = $state<'verifying' | 'error'>('verifying');
	let errorMessage = $state<string>('');

	onMount(async () => {
		if (!browser) return;

		// Get token from URL
		const params = new URLSearchParams(window.location.search);
		const token = params.get('token');

		if (!token) {
			status = 'error';
			errorMessage = 'No verification token provided.';
			return;
		}

		// Redirect to backend verification endpoint
		// The backend will validate the token and redirect back to /login with a message
		window.location.href = `/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`;
	});
</script>

<svelte:head>
	<title>Verify Email - Board of One</title>
	<meta name="description" content="Verify your email address" />
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800 px-4">
	<div class="max-w-md w-full">
		<!-- Logo -->
		<div class="text-center mb-8">
			<h1 class="text-4xl font-bold text-neutral-900 dark:text-white mb-2">
				Board of One
			</h1>
		</div>

		<!-- Verification Card -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-lg p-8 border border-neutral-200 dark:border-neutral-700 text-center">
			{#if status === 'verifying'}
				<div class="flex flex-col items-center gap-4">
					<Spinner size="lg" variant="neutral" ariaLabel="Verifying email" />
					<h2 class="text-xl font-semibold text-neutral-900 dark:text-white">
						Verifying your email...
					</h2>
					<p class="text-neutral-600 dark:text-neutral-400">
						Please wait while we verify your email address.
					</p>
				</div>
			{:else if status === 'error'}
				<div class="flex flex-col items-center gap-4">
					<svg class="w-16 h-16 text-error-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
					</svg>
					<h2 class="text-xl font-semibold text-neutral-900 dark:text-white">
						Verification Failed
					</h2>
					<p class="text-neutral-600 dark:text-neutral-400">
						{errorMessage}
					</p>
					<a
						href="/login"
						class="mt-4 inline-block px-6 py-3 bg-info-600 hover:bg-info-700 text-white font-medium rounded-lg transition-colors"
					>
						Back to Sign In
					</a>
				</div>
			{/if}
		</div>

		<!-- Back to home -->
		<div class="mt-6 text-center">
			<a href="/" class="text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-200 transition-colors">
				Back to home
			</a>
		</div>
	</div>
</div>
