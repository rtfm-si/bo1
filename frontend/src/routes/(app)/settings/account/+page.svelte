<script lang="ts">
	/**
	 * Account Settings - User profile and preferences
	 */
	import { user } from '$lib/stores/auth';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';

	// Get display email (hide placeholder emails)
	const displayEmail = $derived(
		$user?.email && !$user.email.endsWith('@placeholder.local')
			? $user.email
			: 'Not set'
	);

	// Get tier display
	const tierDisplay = $derived(() => {
		const tier = $user?.subscription_tier || 'free';
		const tierLabels: Record<string, string> = {
			free: 'Free',
			starter: 'Starter',
			pro: 'Pro',
			enterprise: 'Enterprise'
		};
		return tierLabels[tier] || 'Free';
	});
</script>

<svelte:head>
	<title>Account Settings - Board of One</title>
</svelte:head>

<div class="space-y-6">
	<!-- Profile Section -->
	<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
		<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
			Profile
		</h2>

		<div class="space-y-4">
			<div>
				<p class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
					Email Address
				</p>
				<p class="text-slate-900 dark:text-white">{displayEmail}</p>
			</div>

			<div>
				<p class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
					User ID
				</p>
				<p class="text-sm text-slate-500 dark:text-slate-400 font-mono">{$user?.id || 'Unknown'}</p>
			</div>
		</div>
	</div>

	<!-- Subscription Section -->
	<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
		<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
			Subscription
		</h2>

		<div class="flex items-center justify-between">
			<div>
				<p class="text-sm text-neutral-700 dark:text-neutral-300">Current Plan</p>
				<p class="text-xl font-semibold text-slate-900 dark:text-white">{tierDisplay()}</p>
			</div>

			<a href="/settings/billing">
				<Button variant="secondary">
					Manage Plan
				</Button>
			</a>
		</div>
	</div>

	<!-- Coming Soon Section -->
	<div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-6">
		<div class="text-center">
			<div class="text-3xl mb-3">🔒</div>
			<h3 class="text-lg font-medium text-slate-700 dark:text-slate-300 mb-2">
				More Account Settings Coming Soon
			</h3>
			<p class="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
				Password changes, notification preferences, and account deletion will be available in a future update.
			</p>
		</div>
	</div>
</div>
