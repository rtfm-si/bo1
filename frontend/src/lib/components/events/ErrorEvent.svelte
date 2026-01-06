<script lang="ts">
	/**
	 * ErrorEvent Component
	 * Displays friendly, in-universe error messages to users
	 * (Technical details only visible to admins)
	 *
	 * Now uses centralized error messages from apiErrorMessages.ts for
	 * specific error codes, with fallback to playful in-universe messages.
	 */
	import type { ErrorEvent } from '$lib/api/sse-events';
	import { ChevronDown, ChevronUp, RefreshCw, AlertCircle } from 'lucide-svelte';
	import { user } from '$lib/stores/auth';
	import {
		getErrorMessage,
		formatRecoveryTime,
		type ErrorMessage
	} from '$lib/utils/apiErrorMessages';

	interface Props {
		event: ErrorEvent;
	}

	let { event }: Props = $props();
	let showTechnicalDetails = $state(false);

	// Pre-read store to ensure subscription happens outside reactive context
	$user;
	const isAdmin = $derived($user?.is_admin ?? false);

	// Get specific error info if we have an error_code from backend
	const specificErrorInfo = $derived.by((): ErrorMessage | null => {
		const errorCode = (event.data as { error_code?: string }).error_code;
		if (errorCode) {
			return getErrorMessage(errorCode);
		}
		return null;
	});

	// Recovery time text for transient errors
	const recoveryTimeText = $derived(
		specificErrorInfo?.recoveryTimeSeconds
			? formatRecoveryTime(specificErrorInfo.recoveryTimeSeconds)
			: ''
	);

	// Friendly, in-universe error messages that fit the "Board of One" theme
	// Used as fallback when no specific error_code is provided
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
	const messageIndex = $derived(
		(event.session_id?.split('').reduce((acc: number, char: string) => acc + char.charCodeAt(0), 0) ?? 0) %
			friendlyMessages.length || 0
	);
	const friendlyError = $derived(friendlyMessages[messageIndex]);

	// Use specific error info if available, otherwise fall back to friendly message
	const displayError = $derived.by(() => {
		if (specificErrorInfo) {
			return {
				title: specificErrorInfo.title,
				message: specificErrorInfo.description,
				icon: specificErrorInfo.isTransient ? '🔄' : '⚠️',
				hasAction: !!specificErrorInfo.action,
				action: specificErrorInfo.action,
				isTransient: specificErrorInfo.isTransient
			};
		}
		return {
			title: friendlyError.title,
			message: friendlyError.message,
			icon: friendlyError.icon,
			hasAction: false,
			action: '',
			isTransient: true
		};
	});
</script>

<div class="space-y-3">
	<div class="border-l-4 {displayError.isTransient ? 'border-info-500' : 'border-amber-500'} {displayError.isTransient ? 'bg-info-50 dark:bg-info-900/20' : 'bg-amber-50 dark:bg-amber-900/20'} rounded-lg p-4">
		<div class="flex items-start gap-3">
			<div
				class="flex-shrink-0 w-10 h-10 {displayError.isTransient ? 'bg-info-500 dark:bg-info-600' : 'bg-amber-500 dark:bg-amber-600'} text-white rounded-full flex items-center justify-center text-lg"
			>
				{displayError.icon}
			</div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-2">
					<h3 class="text-base font-semibold {displayError.isTransient ? 'text-info-900 dark:text-info-100' : 'text-amber-900 dark:text-amber-100'}">
						{displayError.title}
					</h3>
					{#if displayError.isTransient && recoveryTimeText}
						<span class="text-xs px-2 py-0.5 rounded-full bg-info-100 dark:bg-info-800 text-info-700 dark:text-info-300">
							{recoveryTimeText}
						</span>
					{/if}
				</div>

				<p class="text-sm {displayError.isTransient ? 'text-info-800 dark:text-info-200' : 'text-amber-800 dark:text-amber-200'} mb-3">
					{displayError.message}
				</p>

				<!-- Actionable guidance for specific errors -->
				{#if displayError.hasAction && displayError.action}
					<p class="text-sm font-medium {displayError.isTransient ? 'text-info-700 dark:text-info-300' : 'text-amber-700 dark:text-amber-300'} mb-3">
						{displayError.action}
					</p>
				{/if}

				<div
					class="mt-3 p-3 {displayError.isTransient ? 'bg-info-100 dark:bg-info-900/30 border-info-200 dark:border-info-800' : 'bg-amber-100 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800'} rounded-md border"
				>
					<p class="text-xs {displayError.isTransient ? 'text-info-900 dark:text-info-100' : 'text-amber-900 dark:text-amber-100'} font-medium mb-1">
						What happens next?
					</p>
					<p class="text-xs {displayError.isTransient ? 'text-info-800 dark:text-info-200' : 'text-amber-800 dark:text-amber-200'}">
						{#if displayError.isTransient}
							We're working on resolving this automatically. Your meeting will resume shortly.
						{:else}
							You won't be charged for this incomplete deliberation. Please try starting a new
							meeting, or contact support if this issue persists.
						{/if}
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
							{#if (event.data as { event_type_attempted?: string }).event_type_attempted}
								<div>
									<span class="text-neutral-600 dark:text-neutral-400">Event Type:</span>
									<span class="text-neutral-900 dark:text-neutral-100 ml-2">{(event.data as { event_type_attempted?: string }).event_type_attempted}</span
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
