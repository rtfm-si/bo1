<script lang="ts">
	/**
	 * Billing Success Page - Shown after successful Stripe checkout
	 */
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';

	let isLoading = $state(true);
	let countdown = $state(5);

	onMount(() => {
		// Get session_id from URL params (passed by Stripe)
		const sessionId = $page.url.searchParams.get('session_id');
		if (sessionId) {
			console.log('Checkout session completed:', sessionId);
		}

		// Start countdown then redirect
		const interval = setInterval(() => {
			countdown--;
			if (countdown <= 0) {
				clearInterval(interval);
				goto('/settings/billing');
			}
		}, 1000);

		isLoading = false;

		return () => clearInterval(interval);
	});
</script>

<svelte:head>
	<title>Payment Successful - Board of One</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-neutral-900 p-4">
	<div class="max-w-md w-full">
		<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-lg p-8 text-center">
			<!-- Success Icon -->
			<div class="w-16 h-16 mx-auto mb-6 rounded-full bg-success-100 dark:bg-success-900/30 flex items-center justify-center">
				<svg class="w-8 h-8 text-success-600 dark:text-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
				</svg>
			</div>

			<h1 class="text-2xl font-bold text-neutral-900 dark:text-white mb-2">
				Payment Successful!
			</h1>

			<p class="text-neutral-600 dark:text-neutral-400 mb-6">
				Thank you for upgrading your subscription. Your new plan is now active.
			</p>

			<Alert variant="success" class="mb-6">
				Your account has been upgraded and you now have access to all the features included in your new plan.
			</Alert>

			<div class="space-y-3">
				<Button variant="brand" onclick={() => goto('/settings/billing')} class="w-full">
					Go to Billing Settings
				</Button>
				<Button variant="secondary" onclick={() => goto('/')} class="w-full">
					Return to Dashboard
				</Button>
			</div>

			<p class="mt-4 text-sm text-neutral-500 dark:text-neutral-400">
				Redirecting in {countdown} seconds...
			</p>
		</div>
	</div>
</div>
