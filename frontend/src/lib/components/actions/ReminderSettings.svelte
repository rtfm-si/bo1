<script lang="ts">
	import { apiClient } from '$lib/api/client';
	import type { ReminderSettingsResponse } from '$lib/api/types';
	import { Bell, BellOff, Clock, Loader2 } from 'lucide-svelte';

	interface Props {
		actionId: string;
		onUpdate?: () => void;
	}

	let { actionId, onUpdate }: Props = $props();

	let settings = $state<ReminderSettingsResponse | null>(null);
	let isLoading = $state(true);
	let isUpdating = $state(false);
	let error = $state<string | null>(null);
	let showSnoozeOptions = $state(false);

	// Load settings on mount
	$effect(() => {
		loadSettings();
	});

	async function loadSettings() {
		isLoading = true;
		error = null;
		try {
			settings = await apiClient.getActionReminderSettings(actionId);
		} catch (e) {
			error = 'Failed to load reminder settings';
			console.error('Failed to load reminder settings:', e);
		} finally {
			isLoading = false;
		}
	}

	async function toggleReminders() {
		if (!settings) return;

		isUpdating = true;
		error = null;
		try {
			settings = await apiClient.updateActionReminderSettings(actionId, {
				reminders_enabled: !settings.reminders_enabled
			});
			onUpdate?.();
		} catch (e) {
			error = 'Failed to update settings';
			console.error('Failed to update reminder settings:', e);
		} finally {
			isUpdating = false;
		}
	}

	async function updateFrequency(days: number) {
		if (!settings) return;

		isUpdating = true;
		error = null;
		try {
			settings = await apiClient.updateActionReminderSettings(actionId, {
				reminder_frequency_days: days
			});
			onUpdate?.();
		} catch (e) {
			error = 'Failed to update frequency';
			console.error('Failed to update reminder frequency:', e);
		} finally {
			isUpdating = false;
		}
	}

	async function snooze(days: number) {
		isUpdating = true;
		error = null;
		try {
			await apiClient.snoozeActionReminder(actionId, days);
			// Reload to get updated snoozed_until
			await loadSettings();
			showSnoozeOptions = false;
			onUpdate?.();
		} catch (e) {
			error = 'Failed to snooze';
			console.error('Failed to snooze reminder:', e);
		} finally {
			isUpdating = false;
		}
	}

	function formatSnoozedUntil(dateStr: string): string {
		try {
			const date = new Date(dateStr);
			const now = new Date();
			const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
			if (diffDays <= 0) return 'today';
			if (diffDays === 1) return 'tomorrow';
			return `in ${diffDays} days`;
		} catch {
			return dateStr;
		}
	}
</script>

<div class="bg-white dark:bg-neutral-900 rounded-xl p-4 shadow-sm border border-neutral-200 dark:border-neutral-800">
	<div class="flex items-center justify-between mb-3">
		<h3 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider">
			<Bell class="w-4 h-4 text-warning-500" />
			Reminders
		</h3>
		{#if isLoading}
			<Loader2 class="w-4 h-4 animate-spin text-neutral-400" />
		{/if}
	</div>

	{#if error}
		<p class="text-sm text-error-600 dark:text-error-400 mb-2">{error}</p>
	{/if}

	{#if isLoading}
		<div class="space-y-3">
			<div class="h-8 bg-neutral-100 dark:bg-neutral-800 rounded animate-pulse"></div>
			<div class="h-6 bg-neutral-100 dark:bg-neutral-800 rounded animate-pulse w-2/3"></div>
		</div>
	{:else if settings}
		<div class="space-y-3">
			<!-- Toggle reminders -->
			<div class="flex items-center justify-between">
				<span class="text-sm text-neutral-600 dark:text-neutral-400">Email reminders</span>
				<button
					onclick={toggleReminders}
					disabled={isUpdating}
					aria-label={settings.reminders_enabled ? 'Disable email reminders' : 'Enable email reminders'}
					aria-pressed={settings.reminders_enabled}
					class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 {settings.reminders_enabled ? 'bg-brand-600' : 'bg-neutral-200 dark:bg-neutral-700'}"
				>
					<span
						class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out {settings.reminders_enabled ? 'tranneutral-x-5' : 'tranneutral-x-0'}"
					></span>
				</button>
			</div>

			{#if settings.reminders_enabled}
				<!-- Frequency selector -->
				<div class="flex items-center justify-between">
					<span class="text-sm text-neutral-600 dark:text-neutral-400">Remind every</span>
					<select
						value={settings.reminder_frequency_days}
						onchange={(e) => updateFrequency(parseInt(e.currentTarget.value))}
						disabled={isUpdating}
						class="text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg px-2 py-1 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
					>
						<option value="1">1 day</option>
						<option value="2">2 days</option>
						<option value="3">3 days</option>
						<option value="5">5 days</option>
						<option value="7">1 week</option>
						<option value="14">2 weeks</option>
					</select>
				</div>

				<!-- Snoozed status -->
				{#if settings.snoozed_until}
					<div class="flex items-center gap-2 text-sm text-warning-600 dark:text-warning-400">
						<Clock class="w-4 h-4" />
						<span>Snoozed until {formatSnoozedUntil(settings.snoozed_until)}</span>
					</div>
				{/if}

				<!-- Snooze options -->
				<div class="pt-2 border-t border-neutral-200 dark:border-neutral-700">
					{#if showSnoozeOptions}
						<div class="flex flex-wrap gap-2">
							<span class="text-xs text-neutral-500 dark:text-neutral-400 w-full mb-1">Snooze for:</span>
							{#each [1, 3, 7] as days}
								<button
									onclick={() => snooze(days)}
									disabled={isUpdating}
									class="px-2 py-1 text-xs font-medium text-neutral-600 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded transition-colors disabled:opacity-50"
								>
									{days} day{days !== 1 ? 's' : ''}
								</button>
							{/each}
							<button
								onclick={() => showSnoozeOptions = false}
								class="px-2 py-1 text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
							>
								Cancel
							</button>
						</div>
					{:else}
						<button
							onclick={() => showSnoozeOptions = true}
							class="flex items-center gap-1.5 text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300"
						>
							<BellOff class="w-4 h-4" />
							Snooze reminders
						</button>
					{/if}
				</div>
			{:else}
				<p class="text-xs text-neutral-500 dark:text-neutral-400">
					Enable reminders to get notified when this action is overdue or has an approaching deadline.
				</p>
			{/if}
		</div>
	{/if}
</div>
