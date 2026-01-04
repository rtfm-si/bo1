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
	import { APP_VERSION } from '$lib/config/version';

	// State for meeting preferences
	let skipClarification = $state(false);
	let isLoadingPrefs = $state(true);
	let isSavingPrefs = $state(false);
	let prefsError = $state<string | null>(null);

	// State for tour restart
	let isRestartingTour = $state(false);

	// State for working pattern
	let workingDays = $state<number[]>([1, 2, 3, 4, 5]); // Default Mon-Fri
	let isLoadingPattern = $state(true);
	let isSavingPattern = $state(false);
	let patternError = $state<string | null>(null);

	// State for heatmap history depth
	let heatmapDepth = $state<1 | 3 | 6>(3); // Default 3 months
	let isLoadingDepth = $state(true);
	let isSavingDepth = $state(false);
	let depthError = $state<string | null>(null);

	// State for preferred currency
	let preferredCurrency = $state<'GBP' | 'USD' | 'EUR'>('GBP');
	let isLoadingCurrency = $state(true);
	let isSavingCurrency = $state(false);
	let currencyError = $state<string | null>(null);

	// Depth options
	const depthOptions: { value: 1 | 3 | 6; label: string }[] = [
		{ value: 1, label: '1 month' },
		{ value: 3, label: '3 months' },
		{ value: 6, label: '6 months' }
	];

	// Currency options
	const currencyOptions: { value: 'GBP' | 'USD' | 'EUR'; label: string; symbol: string }[] = [
		{ value: 'GBP', label: 'British Pound', symbol: '£' },
		{ value: 'USD', label: 'US Dollar', symbol: '$' },
		{ value: 'EUR', label: 'Euro', symbol: '€' }
	];

	// Day labels (ISO weekday: 1=Mon, 7=Sun)
	const dayLabels = [
		{ value: 1, label: 'Mon' },
		{ value: 2, label: 'Tue' },
		{ value: 3, label: 'Wed' },
		{ value: 4, label: 'Thu' },
		{ value: 5, label: 'Fri' },
		{ value: 6, label: 'Sat' },
		{ value: 7, label: 'Sun' }
	];

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

	// Update preferred currency and auto-save
	async function selectCurrency(currency: 'GBP' | 'USD' | 'EUR') {
		if (isSavingCurrency || currency === preferredCurrency) return;

		const previousCurrency = preferredCurrency;
		preferredCurrency = currency; // Optimistic update
		isSavingCurrency = true;
		currencyError = null;

		try {
			const result = await apiClient.updateUserPreferences({ preferred_currency: currency });
			preferredCurrency = result.preferred_currency as 'GBP' | 'USD' | 'EUR';
		} catch (e) {
			preferredCurrency = previousCurrency; // Revert on error
			currencyError = e instanceof Error ? e.message : 'Failed to save currency preference';
		} finally {
			isSavingCurrency = false;
		}
	}

	// Update heatmap depth and auto-save
	async function selectHeatmapDepth(depth: 1 | 3 | 6) {
		if (isSavingDepth || depth === heatmapDepth) return;

		const previousDepth = heatmapDepth;
		heatmapDepth = depth; // Optimistic update
		isSavingDepth = true;
		depthError = null;

		try {
			const result = await apiClient.updateHeatmapDepth(depth);
			heatmapDepth = result.depth.history_months;
		} catch (e) {
			heatmapDepth = previousDepth; // Revert on error
			depthError = e instanceof Error ? e.message : 'Failed to save heatmap depth';
		} finally {
			isSavingDepth = false;
		}
	}

	// Toggle working day and auto-save
	async function toggleWorkingDay(day: number) {
		if (isSavingPattern) return;

		const previousDays = [...workingDays];
		let newDays: number[];

		if (workingDays.includes(day)) {
			// Don't allow removing last day
			if (workingDays.length <= 1) {
				patternError = 'At least one working day is required';
				return;
			}
			newDays = workingDays.filter((d) => d !== day);
		} else {
			newDays = [...workingDays, day].sort((a, b) => a - b);
		}

		workingDays = newDays; // Optimistic update
		isSavingPattern = true;
		patternError = null;

		try {
			const result = await apiClient.updateWorkingPattern(newDays);
			workingDays = result.pattern.working_days;
		} catch (e) {
			workingDays = previousDays; // Revert on error
			patternError = e instanceof Error ? e.message : 'Failed to save working days';
		} finally {
			isSavingPattern = false;
		}
	}

	// Load preferences, working pattern, heatmap depth, and currency on mount
	onMount(async () => {
		// Load meeting preferences (includes currency)
		try {
			const prefs = await apiClient.getUserPreferences();
			skipClarification = prefs.skip_clarification;
			preferredCurrency = (prefs.preferred_currency || 'GBP') as 'GBP' | 'USD' | 'EUR';
		} catch (e) {
			prefsError = e instanceof Error ? e.message : 'Failed to load preferences';
		} finally {
			isLoadingPrefs = false;
			isLoadingCurrency = false;
		}

		// Load working pattern
		try {
			const patternResp = await apiClient.getWorkingPattern();
			workingDays = patternResp.pattern.working_days;
		} catch (e) {
			patternError = e instanceof Error ? e.message : 'Failed to load working pattern';
		} finally {
			isLoadingPattern = false;
		}

		// Load heatmap depth
		try {
			const depthResp = await apiClient.getHeatmapDepth();
			heatmapDepth = depthResp.depth.history_months;
		} catch (e) {
			depthError = e instanceof Error ? e.message : 'Failed to load heatmap depth';
		} finally {
			isLoadingDepth = false;
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

	<!-- Currency Preference Section -->
	<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
		<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
			Currency Display
		</h2>
		<p class="text-sm text-slate-600 dark:text-slate-400 mb-6">
			Choose your preferred currency for displaying financial metrics and values.
		</p>

		{#if currencyError}
			<Alert variant="error" class="mb-4" dismissable ondismiss={() => (currencyError = null)}>{currencyError}</Alert>
		{/if}

		{#if isLoadingCurrency}
			<div class="flex items-center justify-center py-4">
				<div class="animate-spin h-6 w-6 border-3 border-brand-600 border-t-transparent rounded-full"></div>
			</div>
		{:else}
			<div class="flex flex-wrap gap-2">
				{#each currencyOptions as { value, label, symbol }}
					<button
						type="button"
						disabled={isSavingCurrency}
						onclick={() => selectCurrency(value)}
						class="px-4 py-2 rounded-full text-sm font-medium transition-colors
							{preferredCurrency === value
								? 'bg-brand-600 text-white hover:bg-brand-700'
								: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'}
							{isSavingCurrency ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}"
					>
						{symbol} {label}
					</button>
				{/each}
			</div>
			<p class="mt-3 text-xs text-slate-500 dark:text-slate-400">
				Changes save automatically. This affects how values are shown in the dashboard and key metrics.
			</p>
		{/if}
	</div>

	<!-- Working Pattern Section -->
	<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
		<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
			Working Days
		</h2>
		<p class="text-sm text-slate-600 dark:text-slate-400 mb-6">
			Select which days you typically work. Non-working days are greyed out in activity visualizations.
		</p>

		{#if patternError}
			<Alert variant="error" class="mb-4" dismissable ondismiss={() => (patternError = null)}>{patternError}</Alert>
		{/if}

		{#if isLoadingPattern}
			<div class="flex items-center justify-center py-4">
				<div class="animate-spin h-6 w-6 border-3 border-brand-600 border-t-transparent rounded-full"></div>
			</div>
		{:else}
			<div class="flex flex-wrap gap-2">
				{#each dayLabels as { value, label }}
					<button
						type="button"
						disabled={isSavingPattern}
						onclick={() => toggleWorkingDay(value)}
						class="px-4 py-2 rounded-full text-sm font-medium transition-colors
							{workingDays.includes(value)
								? 'bg-brand-600 text-white hover:bg-brand-700'
								: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'}
							{isSavingPattern ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}"
					>
						{label}
					</button>
				{/each}
			</div>
			<p class="mt-3 text-xs text-slate-500 dark:text-slate-400">
				Changes save automatically. At least one day must be selected.
			</p>
		{/if}
	</div>

	<!-- Activity Heatmap Section -->
	<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
		<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
			Activity Heatmap
		</h2>
		<p class="text-sm text-slate-600 dark:text-slate-400 mb-6">
			Choose how much history to display in the activity heatmap on your dashboard.
		</p>

		{#if depthError}
			<Alert variant="error" class="mb-4" dismissable ondismiss={() => (depthError = null)}>{depthError}</Alert>
		{/if}

		{#if isLoadingDepth}
			<div class="flex items-center justify-center py-4">
				<div class="animate-spin h-6 w-6 border-3 border-brand-600 border-t-transparent rounded-full"></div>
			</div>
		{:else}
			<div class="flex flex-wrap gap-2">
				{#each depthOptions as { value, label }}
					<button
						type="button"
						disabled={isSavingDepth}
						onclick={() => selectHeatmapDepth(value)}
						class="px-4 py-2 rounded-full text-sm font-medium transition-colors
							{heatmapDepth === value
								? 'bg-brand-600 text-white hover:bg-brand-700'
								: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'}
							{isSavingDepth ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}"
					>
						{label}
					</button>
				{/each}
			</div>
			<p class="mt-3 text-xs text-slate-500 dark:text-slate-400">
				Changes save automatically. A shorter history shows a more compact heatmap.
			</p>
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

	<!-- Version Footer -->
	<p class="text-center text-sm text-slate-400 dark:text-slate-500">
		Board of One v{APP_VERSION}
	</p>
</div>
