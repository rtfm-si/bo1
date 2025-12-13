<script lang="ts">
	/**
	 * Billing Cancel Page - Shown when user cancels Stripe checkout
	 */
	import { goto } from '$app/navigation';
	import Button from '$lib/components/ui/Button.svelte';
</script>

<svelte:head>
	<title>Checkout Cancelled - Board of One</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 p-4">
	<div class="max-w-md w-full">
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-8 text-center">
			<!-- Info Icon -->
			<div class="w-16 h-16 mx-auto mb-6 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
				<svg class="w-8 h-8 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
				</svg>
			</div>

			<h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">
				Checkout Cancelled
			</h1>

			<p class="text-slate-600 dark:text-slate-400 mb-6">
				Your checkout was cancelled. No charges have been made to your account.
			</p>

			<div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4 mb-6">
				<p class="text-sm text-slate-600 dark:text-slate-400">
					Changed your mind? You can upgrade your plan anytime from your billing settings.
				</p>
			</div>

			<div class="space-y-3">
				<Button variant="brand" onclick={() => goto('/settings/billing')} class="w-full">
					View Billing Options
				</Button>
				<Button variant="secondary" onclick={() => goto('/')} class="w-full">
					Return to Dashboard
				</Button>
			</div>

			<p class="mt-6 text-sm text-slate-500 dark:text-slate-400">
				Questions about our plans? <a href="mailto:support@boardof.one" class="text-brand-600 hover:underline">Contact support</a>
			</p>
		</div>
	</div>
</div>
