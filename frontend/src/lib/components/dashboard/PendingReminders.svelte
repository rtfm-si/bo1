<script lang="ts">
	import { apiClient } from '$lib/api/client';
	import type { ActionRemindersResponse, ActionReminderResponse } from '$lib/api/types';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { Button } from '$lib/components/ui';

	// Fetch pending reminders
	const remindersData = useDataFetch(() => apiClient.getActionReminders(10));

	// Expose fetch method for parent component to trigger refresh
	export function refresh() {
		remindersData.fetch();
	}

	// Derived state
	const reminders = $derived<ActionReminderResponse[]>(remindersData.data?.reminders || []);
	const isLoading = $derived(remindersData.isLoading);
	const hasReminders = $derived(reminders.length > 0);

	// Snooze handling
	let snoozingId = $state<string | null>(null);

	async function snoozeReminder(actionId: string, days: number) {
		snoozingId = actionId;
		try {
			await apiClient.snoozeActionReminder(actionId, days);
			// Refresh the list
			await remindersData.fetch();
		} catch (err) {
			console.error('Failed to snooze reminder:', err);
		} finally {
			snoozingId = null;
		}
	}

	function getReminderIcon(type: string): string {
		return type === 'start_overdue' ? 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' : 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z';
	}

	function getReminderLabel(reminder: ActionReminderResponse): string {
		if (reminder.reminder_type === 'start_overdue') {
			if (reminder.days_overdue === 0) return 'Should have started today';
			return `Start overdue by ${reminder.days_overdue} day${reminder.days_overdue !== 1 ? 's' : ''}`;
		} else {
			if (reminder.days_until_deadline === 0) return 'Due today';
			if (reminder.days_until_deadline && reminder.days_until_deadline < 0) {
				return `Overdue by ${Math.abs(reminder.days_until_deadline)} day${Math.abs(reminder.days_until_deadline) !== 1 ? 's' : ''}`;
			}
			return `Due in ${reminder.days_until_deadline} day${reminder.days_until_deadline !== 1 ? 's' : ''}`;
		}
	}
</script>

{#if hasReminders || isLoading}
	<div class="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg">
		<div class="p-4 border-b border-neutral-200 dark:border-neutral-700">
			<div class="flex items-center gap-2">
				<svg class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
				</svg>
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Action Reminders</h2>
				{#if reminders.length > 0}
					<Badge variant="warning" size="sm">{reminders.length}</Badge>
				{/if}
			</div>
		</div>

		{#if isLoading}
			<div class="p-4 space-y-3">
				{#each [1, 2, 3] as _}
					<div class="animate-pulse flex items-center gap-3">
						<div class="w-10 h-10 bg-neutral-200 dark:bg-neutral-700 rounded-full"></div>
						<div class="flex-1">
							<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4 mb-2"></div>
							<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2"></div>
						</div>
					</div>
				{/each}
			</div>
		{:else if reminders.length === 0}
			<div class="p-6 text-center text-neutral-500 dark:text-neutral-400">
				<svg class="w-12 h-12 mx-auto mb-3 text-neutral-300 dark:text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<p class="text-sm">All caught up! No pending reminders.</p>
			</div>
		{:else}
			<div class="divide-y divide-neutral-100 dark:divide-neutral-700/50">
				{#each reminders as reminder (reminder.action_id)}
					<div class="p-4 hover:bg-neutral-50 dark:hover:bg-neutral-700/30 transition-colors">
						<div class="flex items-start gap-3">
							<!-- Icon -->
							<div class="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-full {reminder.reminder_type === 'start_overdue' ? 'bg-amber-100 dark:bg-amber-900/30' : 'bg-red-100 dark:bg-red-900/30'}">
								<svg class="w-5 h-5 {reminder.reminder_type === 'start_overdue' ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getReminderIcon(reminder.reminder_type)} />
								</svg>
							</div>

							<!-- Content -->
							<div class="flex-1 min-w-0">
								<a
									href="/actions/{reminder.action_id}"
									class="text-sm font-medium text-neutral-900 dark:text-white hover:text-brand-600 dark:hover:text-brand-400 transition-colors line-clamp-1"
								>
									{reminder.action_title}
								</a>
								<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
									{getReminderLabel(reminder)}
								</p>
								{#if reminder.problem_statement}
									<p class="text-xs text-neutral-400 dark:text-neutral-500 mt-1 line-clamp-1">
										{reminder.problem_statement}
									</p>
								{/if}
							</div>

							<!-- Actions -->
							<div class="flex-shrink-0 flex items-center gap-2">
								<Button
									size="sm"
									variant="ghost"
									onclick={() => snoozeReminder(reminder.action_id, 1)}
									disabled={snoozingId === reminder.action_id}
									title="Snooze for 1 day"
								>
									{#if snoozingId === reminder.action_id}
										<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
											<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
											<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
										</svg>
									{:else}
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
										</svg>
									{/if}
								</Button>
								<a
									href="/actions/{reminder.action_id}"
									class="inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 rounded hover:bg-brand-100 dark:hover:bg-brand-900/30 transition-colors"
								>
									View
								</a>
							</div>
						</div>
					</div>
				{/each}
			</div>

			{#if reminders.length >= 10}
				<div class="p-3 border-t border-neutral-200 dark:border-neutral-700 text-center">
					<a
						href="/actions?filter=needs_attention"
						class="text-sm text-brand-600 dark:text-brand-400 hover:underline"
					>
						View all actions needing attention
					</a>
				</div>
			{/if}
		{/if}
	</div>
{/if}
