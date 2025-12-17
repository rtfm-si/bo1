<script lang="ts">
	/**
	 * Failed Meeting Alert - Dashboard banner for recent failed meetings
	 *
	 * Shows a dismissible amber/warning alert when user has failed meetings
	 * in the last 24 hours. Provides reassurance and retry options.
	 */

	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { apiClient } from '$lib/api/client';
	import type { FailedMeeting } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';

	// Props
	interface Props {
		class?: string;
	}
	let { class: className = '' }: Props = $props();

	// State
	let failedMeetings = $state<FailedMeeting[]>([]);
	let isLoading = $state(true);
	let isDismissed = $state(false);

	// LocalStorage key for dismiss state (per-user, 24h expiry)
	const DISMISS_KEY = 'bo1_failed_meeting_alert_dismissed';

	onMount(async () => {
		// Check if recently dismissed
		if (browser) {
			const dismissedData = localStorage.getItem(DISMISS_KEY);
			if (dismissedData) {
				try {
					const { timestamp, sessionIds } = JSON.parse(dismissedData);
					// Expire after 24 hours
					if (Date.now() - timestamp < 24 * 60 * 60 * 1000) {
						isDismissed = true;
						// Keep track of which sessions were dismissed
						dismissedSessionIds = new Set(sessionIds || []);
					} else {
						localStorage.removeItem(DISMISS_KEY);
					}
				} catch {
					localStorage.removeItem(DISMISS_KEY);
				}
			}
		}

		// Fetch recent failures
		try {
			const response = await apiClient.getRecentFailures();
			// Filter out already-dismissed sessions
			failedMeetings = response.failures.filter(f => !dismissedSessionIds.has(f.session_id));
		} catch (error) {
			console.error('Failed to check recent failures:', error);
		} finally {
			isLoading = false;
		}
	});

	let dismissedSessionIds = $state<Set<string>>(new Set());

	function handleDismiss() {
		isDismissed = true;
		// Store dismiss with current failed session IDs
		if (browser) {
			localStorage.setItem(DISMISS_KEY, JSON.stringify({
				timestamp: Date.now(),
				sessionIds: failedMeetings.map(f => f.session_id)
			}));
		}
	}

	function handleRetry() {
		goto('/meeting/new');
	}

	// Show alert if there are failed meetings and not dismissed
	const showAlert = $derived(!isLoading && !isDismissed && failedMeetings.length > 0);
</script>

{#if showAlert}
	<div
		class="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-900/20 {className}"
		role="alert"
	>
		<div class="flex items-start gap-3">
			<!-- Warning Icon -->
			<div class="flex-shrink-0 mt-0.5">
				<svg
					class="h-5 w-5 text-amber-600 dark:text-amber-400"
					fill="currentColor"
					viewBox="0 0 20 20"
					aria-hidden="true"
				>
					<path
						fill-rule="evenodd"
						d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>

			<!-- Content -->
			<div class="flex-1 min-w-0">
				<h3 class="text-sm font-medium text-amber-800 dark:text-amber-200">
					{failedMeetings.length === 1
						? 'A meeting didn\'t complete'
						: `${failedMeetings.length} meetings didn't complete`}
				</h3>
				<p class="mt-1 text-sm text-amber-700 dark:text-amber-300">
					This doesn't count toward your usage. Try again, or contact support if the issue persists.
				</p>

				<!-- Actions -->
				<div class="mt-3 flex flex-wrap gap-2">
					<Button
						variant="brand"
						size="sm"
						onclick={handleRetry}
					>
						Start New Meeting
					</Button>
					<Button
						variant="ghost"
						size="sm"
						onclick={handleDismiss}
					>
						Dismiss
					</Button>
				</div>
			</div>

			<!-- Close button -->
			<button
				type="button"
				class="flex-shrink-0 rounded-md p-1.5 text-amber-600 hover:bg-amber-100 dark:text-amber-400 dark:hover:bg-amber-800/50 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2"
				onclick={handleDismiss}
				aria-label="Dismiss alert"
			>
				<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>
	</div>
{/if}
