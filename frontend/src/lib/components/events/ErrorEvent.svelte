<script lang="ts">
	/**
	 * ErrorEvent Component
	 * Displays friendly, in-universe error messages to users
	 * (Technical details only visible to admins)
	 */
	import type { ErrorEvent } from '$lib/api/sse-events';
	import { ChevronDown, ChevronUp } from 'lucide-svelte';
	import { user } from '$lib/stores/auth';

	interface Props {
		event: ErrorEvent;
	}

	let { event }: Props = $props();
	let showTechnicalDetails = $state(false);
	const isAdmin = $derived($user?.is_admin ?? false);

	// Friendly, in-universe error messages that fit the "Board of One" theme
	const friendlyMessages = [
		{
			title: 'Meeting Room Evacuation',
			message:
				"There was a fire drill in the building and the expert panel had to evacuate. The deliberation couldn't be completed.",
			icon: '🚨'
		},
		{
			title: 'Expert Panel Disconnected',
			message:
				'The video conference system experienced technical difficulties and several experts were disconnected. The deliberation was interrupted.',
			icon: '📞'
		},
		{
			title: 'Scheduling Conflict',
			message:
				'One of the key experts had an urgent emergency and had to leave the deliberation early. The meeting cannot continue without their critical input.',
			icon: '⏰'
		},
		{
			title: 'Conference Room Unavailable',
			message:
				'The meeting room became unexpectedly unavailable due to a facilities issue. The deliberation had to be postponed.',
			icon: '🚪'
		},
		{
			title: 'Expert Panel Overbooked',
			message:
				'The expert panel is currently overbooked and cannot complete this deliberation at this time. Please try again shortly.',
			icon: '📅'
		}
	];

	// Select a consistent message based on session_id (same session = same message)
	const messageIndex =
		event.data.session_id?.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) %
			friendlyMessages.length || 0;
	const friendlyError = friendlyMessages[messageIndex];
</script>

<div class="space-y-3">
	<div class="border-l-4 border-amber-500 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4">
		<div class="flex items-start gap-3">
			<div
				class="flex-shrink-0 w-10 h-10 bg-amber-500 dark:bg-amber-600 text-white rounded-full flex items-center justify-center text-lg"
			>
				{friendlyError.icon}
			</div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-2">
					<h3 class="text-base font-semibold text-amber-900 dark:text-amber-100">
						{friendlyError.title}
					</h3>
				</div>

				<p class="text-sm text-amber-800 dark:text-amber-200 mb-3">
					{friendlyError.message}
				</p>

				<div
					class="mt-3 p-3 bg-amber-100 dark:bg-amber-900/30 rounded-md border border-amber-200 dark:border-amber-800"
				>
					<p class="text-xs text-amber-900 dark:text-amber-100 font-medium mb-1">
						What happens next?
					</p>
					<p class="text-xs text-amber-800 dark:text-amber-200">
						You won't be charged for this incomplete deliberation. Please try starting a new
						meeting, or contact support if this issue persists.
					</p>
				</div>

				<!-- Technical Details (admin-only) -->
				{#if isAdmin}
					<button
						onclick={() => (showTechnicalDetails = !showTechnicalDetails)}
						class="mt-3 flex items-center gap-1 text-xs text-amber-700 dark:text-amber-300 hover:text-amber-900 dark:hover:text-amber-100 transition-colors"
					>
						{#if showTechnicalDetails}
							<ChevronUp size={14} />
						{:else}
							<ChevronDown size={14} />
						{/if}
						{showTechnicalDetails ? 'Hide' : 'Show'} technical details
					</button>

					{#if showTechnicalDetails}
						<div
							class="mt-2 p-3 bg-neutral-100 dark:bg-neutral-800 rounded border border-neutral-200 dark:border-neutral-700 text-xs font-mono"
						>
							<div class="mb-2">
								<span class="text-neutral-600 dark:text-neutral-400">Error Type:</span>
								<span class="text-neutral-900 dark:text-neutral-100 ml-2"
									>{event.data.error_type}</span
								>
							</div>
							<div class="mb-2">
								<span class="text-neutral-600 dark:text-neutral-400">Message:</span>
								<div class="text-neutral-900 dark:text-neutral-100 mt-1 whitespace-pre-wrap">
									{event.data.error}
								</div>
							</div>
							{#if event.data.node}
								<div>
									<span class="text-neutral-600 dark:text-neutral-400">Node:</span>
									<span class="text-neutral-900 dark:text-neutral-100 ml-2">{event.data.node}</span
									>
								</div>
							{/if}
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
</div>
