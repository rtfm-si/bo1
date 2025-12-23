<script lang="ts">
	/**
	 * Integrations Settings - Connect external services
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { apiClient } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';

	// State
	let calendarConnected = $state(false);
	let calendarConnectedAt = $state<string | null>(null);
	let calendarFeatureEnabled = $state(true);
	let calendarSyncEnabled = $state(true);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);
	let isDisconnecting = $state(false);
	let isTogglingSync = $state(false);

	// Check for callback params
	$effect(() => {
		const calendarError = $page.url.searchParams.get('calendar_error');
		const calendarSuccess = $page.url.searchParams.get('calendar_connected');

		if (calendarError) {
			const errorMessages: Record<string, string> = {
				access_denied: 'You denied access to Google Calendar',
				invalid_request: 'Invalid OAuth request',
				invalid_state: 'Session expired. Please try again.',
				token_exchange_failed: 'Failed to connect. Please try again.',
				unexpected_error: 'An unexpected error occurred'
			};
			error = errorMessages[calendarError] || 'Connection failed';

			// Clean URL
			const url = new URL(window.location.href);
			url.searchParams.delete('calendar_error');
			window.history.replaceState({}, '', url);
		}

		if (calendarSuccess === 'true') {
			success = 'Google Calendar connected successfully!';
			calendarConnected = true;

			// Clean URL
			const url = new URL(window.location.href);
			url.searchParams.delete('calendar_connected');
			window.history.replaceState({}, '', url);
		}
	});

	// Load status on mount
	onMount(async () => {
		try {
			const status = await apiClient.getCalendarStatus();
			calendarConnected = status.connected;
			calendarConnectedAt = status.connected_at ?? null;
			calendarFeatureEnabled = status.feature_enabled;
			calendarSyncEnabled = status.sync_enabled;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load integration status';
		} finally {
			isLoading = false;
		}
	});

	// Connect Google Calendar
	function connectCalendar() {
		// Redirect to OAuth endpoint
		window.location.href = '/api/v1/integrations/calendar/connect';
	}

	// Disconnect Google Calendar
	async function disconnectCalendar() {
		if (!confirm('Are you sure you want to disconnect Google Calendar? Existing calendar events will not be removed.')) {
			return;
		}

		isDisconnecting = true;
		error = null;

		try {
			await apiClient.disconnectCalendar();
			calendarConnected = false;
			calendarConnectedAt = null;
			success = 'Google Calendar disconnected';
			setTimeout(() => { success = null; }, 3000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to disconnect';
		} finally {
			isDisconnecting = false;
		}
	}

	// Toggle sync on/off
	async function toggleSync() {
		isTogglingSync = true;
		error = null;

		try {
			const newEnabled = !calendarSyncEnabled;
			const status = await apiClient.toggleCalendarSync(newEnabled);
			calendarSyncEnabled = status.sync_enabled;
			success = newEnabled ? 'Calendar sync enabled' : 'Calendar sync paused';
			setTimeout(() => { success = null; }, 3000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to toggle sync';
		} finally {
			isTogglingSync = false;
		}
	}

	// Format connected date
	const connectedDateDisplay = $derived(() => {
		if (!calendarConnectedAt) return null;
		try {
			return new Date(calendarConnectedAt).toLocaleDateString(undefined, {
				year: 'numeric',
				month: 'long',
				day: 'numeric'
			});
		} catch {
			return null;
		}
	});
</script>

<svelte:head>
	<title>Integrations - Board of One</title>
</svelte:head>

<div class="space-y-6">
	<!-- Page Header -->
	<div>
		<h1 class="text-2xl font-bold text-slate-900 dark:text-white">
			Integrations
		</h1>
		<p class="mt-1 text-sm text-slate-600 dark:text-slate-400">
			Connect external services to enhance your workflow.
		</p>
	</div>

	{#if error}
		<Alert variant="error" dismissable ondismiss={() => (error = null)}>{error}</Alert>
	{/if}

	{#if success}
		<Alert variant="success" dismissable ondismiss={() => (success = null)}>{success}</Alert>
	{/if}

	<!-- Google Calendar Integration -->
	<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
		<div class="flex items-start gap-4">
			<!-- Icon -->
			<div class="flex-shrink-0 w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
				<svg class="w-7 h-7 text-blue-600 dark:text-blue-400" viewBox="0 0 24 24" fill="currentColor">
					<path d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V10h14v10zm0-12H5V6h14v2z"/>
				</svg>
			</div>

			<!-- Content -->
			<div class="flex-1 min-w-0">
				<h2 class="text-lg font-semibold text-slate-900 dark:text-white">
					Google Calendar
				</h2>
				<p class="mt-1 text-sm text-slate-600 dark:text-slate-400">
					Automatically sync action due dates to your Google Calendar. Events are created when you set or update due dates.
				</p>

				{#if isLoading}
					<div class="mt-4 flex items-center gap-2">
						<div class="animate-spin h-4 w-4 border-2 border-brand-600 border-t-transparent rounded-full"></div>
						<span class="text-sm text-slate-500">Checking status...</span>
					</div>
				{:else if !calendarFeatureEnabled}
					<div class="mt-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3">
						<p class="text-sm text-amber-800 dark:text-amber-200">
							Google Calendar integration is not yet available. Check back soon!
						</p>
					</div>
				{:else if calendarConnected}
					<div class="mt-4 space-y-4">
						<div class="flex items-center gap-2">
							<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
								<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
								</svg>
								Connected
							</span>
							{#if connectedDateDisplay()}
								<span class="text-sm text-slate-500 dark:text-slate-400">
									since {connectedDateDisplay()}
								</span>
							{/if}
						</div>

						<!-- Sync Toggle -->
						<div class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
							<div>
								<p class="text-sm font-medium text-slate-900 dark:text-white">
									Sync actions to calendar
								</p>
								<p class="text-xs text-slate-500 dark:text-slate-400">
									{calendarSyncEnabled ? 'Actions with due dates will appear in your calendar' : 'Sync paused - no new events will be created'}
								</p>
							</div>
							<button
								type="button"
								class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-slate-800 disabled:opacity-50 disabled:cursor-not-allowed {calendarSyncEnabled ? 'bg-brand-600' : 'bg-slate-300 dark:bg-slate-600'}"
								role="switch"
								aria-checked={calendarSyncEnabled}
								disabled={isTogglingSync}
								onclick={toggleSync}
							>
								<span class="sr-only">Toggle calendar sync</span>
								<span
									class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out {calendarSyncEnabled ? 'translate-x-5' : 'translate-x-0'}"
								></span>
							</button>
						</div>

						<div class="flex gap-2">
							<Button
								variant="secondary"
								size="sm"
								loading={isDisconnecting}
								onclick={disconnectCalendar}
							>
								Disconnect
							</Button>
						</div>
					</div>
				{:else}
					<div class="mt-4 space-y-3">
						<p class="text-sm text-slate-500 dark:text-slate-400">
							Connect your Google account to sync action due dates to your calendar.
						</p>

						<Button variant="brand" onclick={connectCalendar}>
							Connect Google Calendar
						</Button>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<!-- Future Integrations Placeholder -->
	<div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-6">
		<div class="text-center">
			<svg class="mx-auto h-12 w-12 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z"/>
			</svg>
			<h3 class="mt-2 text-sm font-medium text-slate-900 dark:text-white">More integrations coming soon</h3>
			<p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
				We're working on integrations with Slack, Notion, and more.
			</p>
		</div>
	</div>
</div>
