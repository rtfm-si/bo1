<script lang="ts">
	/**
	 * Account Settings - User profile and preferences
	 */
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores/auth';
	import { apiClient } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { resetTour } from '$lib/stores/tour';

	// State for meeting preferences
	let skipClarification = $state(false);
	let isLoadingPrefs = $state(true);
	let isSavingPrefs = $state(false);
	let prefsError = $state<string | null>(null);

	// State for tour restart
	let isRestartingTour = $state(false);

	// Restart onboarding tour
	async function restartTour() {
		isRestartingTour = true;
		try {
			await resetTour();
			// Navigate to dashboard where tour will auto-start
			goto('/dashboard');
		} catch (err) {
			console.error('Failed to restart tour:', err);
		} finally {
			isRestartingTour = false;
		}
	}

	// Load preferences on mount
	onMount(async () => {
		try {
			const prefs = await apiClient.getUserPreferences();
			skipClarification = prefs.skip_clarification;
		} catch (e) {
			prefsError = e instanceof Error ? e.message : 'Failed to load preferences';
		} finally {
			isLoadingPrefs = false;
		}
	});

	// Toggle and auto-save preference
	async function toggleAndSave() {
		if (isSavingPrefs) return;

		const previousValue = skipClarification;
		skipClarification = !skipClarification; // Optimistic update
		isSavingPrefs = true;
		prefsError = null;

		try {
			const result = await apiClient.updateUserPreferences({
				skip_clarification: skipClarification
			});
			skipClarification = result.skip_clarification;
		} catch (e) {
			skipClarification = previousValue; // Revert on error
			prefsError = e instanceof Error ? e.message : 'Failed to save preference';
		} finally {
			isSavingPrefs = false;
		}
	}

	// Get display email (hide placeholder emails)
	const displayEmail = $derived(
		$user?.email && !$user.email.endsWith('@placeholder.local')
			? $user.email
			: 'Not set'
	);

	// Get tier display
	const tierDisplay = $derived.by(() => {
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

	<!-- Meeting Preferences Section -->
	<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
		<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
			Meeting Preferences
		</h2>
		<p class="text-sm text-slate-600 dark:text-slate-400 mb-6">
			Customize how meetings work for you.
		</p>

		{#if prefsError}
			<Alert variant="error" class="mb-4" dismissable ondismiss={() => (prefsError = null)}>{prefsError}</Alert>
		{/if}


		{#if isLoadingPrefs}
			<div class="flex items-center justify-center py-4">
				<div class="animate-spin h-6 w-6 border-3 border-brand-600 border-t-transparent rounded-full"></div>
			</div>
		{:else}
			<div class="space-y-4">
				<label class="flex items-center justify-between cursor-pointer">
					<div>
						<p class="font-medium text-slate-900 dark:text-white">Skip clarifying questions</p>
						<p class="text-sm text-slate-500 dark:text-slate-400">
							Start meetings directly without pre-meeting questions. Use your business profile for context instead.
						</p>
					</div>
					<button
						type="button"
						role="switch"
						aria-checked={skipClarification}
						aria-label="Toggle skip clarifying questions"
						disabled={isSavingPrefs}
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {skipClarification
							? 'bg-brand-600'
							: 'bg-slate-300 dark:bg-slate-600'} {isSavingPrefs ? 'opacity-60 cursor-not-allowed' : ''}"
						onclick={toggleAndSave}
					>
						{#if isSavingPrefs}
							<span class="absolute inset-0 flex items-center justify-center">
								<span class="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
							</span>
						{:else}
							<span
								class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {skipClarification
									? 'translate-x-6'
									: 'translate-x-1'}"
							></span>
						{/if}
					</button>
				</label>
			</div>

			<div class="mt-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4">
				<p class="text-sm text-amber-800 dark:text-amber-200">
					<strong>Note:</strong> Changes are saved automatically. Clarifying questions help the experts understand your specific situation.
					Skipping them may result in more generic recommendations unless you've provided detailed business context.
				</p>
			</div>
		{/if}
	</div>

	<!-- Subscription Section -->
	<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
		<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
			Subscription
		</h2>

		<div class="flex items-center justify-between">
			<div>
				<p class="text-sm text-neutral-700 dark:text-neutral-300">Current Plan</p>
				<p class="text-xl font-semibold text-slate-900 dark:text-white">{tierDisplay}</p>
			</div>

			<a href="/settings/billing">
				<Button variant="secondary">
					Manage Plan
				</Button>
			</a>
		</div>
	</div>

	<!-- Privacy & Data Link -->
	<div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-6">
		<div class="flex items-center gap-4">
			<div class="text-2xl">&#128274;</div>
			<div class="flex-1">
				<h3 class="font-medium text-slate-700 dark:text-slate-300">Privacy & Data</h3>
				<p class="text-sm text-slate-500 dark:text-slate-400">
					Manage email preferences, export your data, or delete your account
				</p>
			</div>
			<a href="/settings/privacy">
				<Button variant="secondary">
					Privacy Settings
				</Button>
			</a>
		</div>
	</div>

	<!-- Onboarding Tour -->
	<div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-6">
		<div class="flex items-center gap-4">
			<div class="text-2xl">&#127891;</div>
			<div class="flex-1">
				<h3 class="font-medium text-slate-700 dark:text-slate-300">Onboarding Tour</h3>
				<p class="text-sm text-slate-500 dark:text-slate-400">
					Take a guided tour of Board of One features
				</p>
			</div>
			<Button variant="secondary" onclick={restartTour} loading={isRestartingTour}>
				Restart Tour
			</Button>
		</div>
	</div>
</div>
