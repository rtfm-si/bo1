<script lang="ts">
	import { onMount } from 'svelte';
	import { Settings, RefreshCw, Shield, Clock, Lock } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { adminApi, type AlertSettingsResponse } from '$lib/api/admin';

	// State
	let settings = $state<AlertSettingsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function loadSettings() {
		try {
			loading = true;
			settings = await adminApi.getAlertSettings();
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load alert settings';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadSettings();
	});
</script>

<svelte:head>
	<title>Alert Settings - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/admin"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
						aria-label="Back to admin"
					>
						<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</a>
					<div class="flex items-center gap-3">
						<Settings class="w-6 h-6 text-brand-600 dark:text-brand-400" />
						<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">Alert Settings</h1>
					</div>
				</div>
				<div class="flex items-center gap-3">
					<a href="/admin/alerts/history">
						<Button variant="secondary" size="sm">
							View History
						</Button>
					</a>
					<Button variant="secondary" size="sm" onclick={loadSettings}>
						<RefreshCw class="w-4 h-4" />
						Refresh
					</Button>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if error}
			<Alert variant="error" class="mb-6">{error}</Alert>
		{/if}

		<!-- Info Banner -->
		<div class="bg-info-50 dark:bg-info-900/20 border border-info-200 dark:border-info-800 rounded-lg p-4 mb-6">
			<p class="text-sm text-info-700 dark:text-info-300">
				Alert thresholds are configured in <code class="px-1.5 py-0.5 bg-info-100 dark:bg-info-800 rounded text-xs">bo1/constants.py</code> (SecurityAlerts class).
				These settings are read-only and require a code deployment to change.
			</p>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
			</div>
		{:else if settings}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
				<!-- Auth Failure Settings -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 flex items-center gap-3">
						<div class="p-2 bg-error-100 dark:bg-error-900/30 rounded-lg">
							<Shield class="w-5 h-5 text-error-600 dark:text-error-400" />
						</div>
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Auth Failures</h2>
					</div>
					<div class="p-6 space-y-4">
						<div>
							<span class="text-sm text-neutral-500 dark:text-neutral-400">Threshold</span>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{settings.auth_failure_threshold} failures
							</p>
						</div>
						<div>
							<span class="text-sm text-neutral-500 dark:text-neutral-400">Window</span>
							<p class="text-lg text-neutral-700 dark:text-neutral-300">
								{settings.auth_failure_window_minutes} minutes
							</p>
						</div>
						<p class="text-xs text-neutral-500 dark:text-neutral-500">
							Alert sent when an IP exceeds {settings.auth_failure_threshold} failed auth attempts within {settings.auth_failure_window_minutes} minutes.
						</p>
					</div>
				</div>

				<!-- Rate Limit Settings -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 flex items-center gap-3">
						<div class="p-2 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
							<Clock class="w-5 h-5 text-warning-600 dark:text-warning-400" />
						</div>
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Rate Limits</h2>
					</div>
					<div class="p-6 space-y-4">
						<div>
							<span class="text-sm text-neutral-500 dark:text-neutral-400">Threshold</span>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{settings.rate_limit_threshold} hits
							</p>
						</div>
						<div>
							<span class="text-sm text-neutral-500 dark:text-neutral-400">Window</span>
							<p class="text-lg text-neutral-700 dark:text-neutral-300">
								{settings.rate_limit_window_minutes} minutes
							</p>
						</div>
						<p class="text-xs text-neutral-500 dark:text-neutral-500">
							Alert sent when an IP exceeds {settings.rate_limit_threshold} rate limit hits within {settings.rate_limit_window_minutes} minutes.
						</p>
					</div>
				</div>

				<!-- Lockout Settings -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 flex items-center gap-3">
						<div class="p-2 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
							<Lock class="w-5 h-5 text-brand-600 dark:text-brand-400" />
						</div>
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Lockouts</h2>
					</div>
					<div class="p-6 space-y-4">
						<div>
							<span class="text-sm text-neutral-500 dark:text-neutral-400">Threshold</span>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{settings.lockout_threshold} lockouts
							</p>
						</div>
						<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-6">
							Alert sent when an IP triggers {settings.lockout_threshold} account lockouts. Indicates sustained brute force or credential stuffing.
						</p>
					</div>
				</div>
			</div>
		{/if}
	</main>
</div>
