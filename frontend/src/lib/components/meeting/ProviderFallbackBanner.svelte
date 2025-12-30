<script lang="ts">
	/**
	 * ProviderFallbackBanner Component
	 * Shows a reassuring message when the system is automatically switching providers
	 * or recovering from transient errors.
	 */
	import { RefreshCw, CheckCircle } from 'lucide-svelte';
	import { PROVIDER_FALLBACK_MESSAGE, RETRY_IN_PROGRESS_MESSAGE } from '$lib/utils/apiErrorMessages';

	type FallbackReason = 'provider_switch' | 'retry' | 'reconnecting';

	interface Props {
		/** What type of fallback is happening */
		reason: FallbackReason;
		/** Whether the fallback has resolved */
		resolved?: boolean;
		/** Optional custom message */
		customMessage?: string;
	}

	let { reason, resolved = false, customMessage }: Props = $props();

	const messages: Record<FallbackReason, { title: string; description: string; icon: string; estimatedTime: string }> = {
		provider_switch: PROVIDER_FALLBACK_MESSAGE,
		retry: RETRY_IN_PROGRESS_MESSAGE,
		reconnecting: {
			title: 'Reconnecting',
			description: 'Restoring connection to the meeting stream...',
			icon: '🔌',
			estimatedTime: '~5 seconds'
		}
	};

	const message = $derived(messages[reason] || messages.retry);
</script>

{#if !resolved}
	<div
		class="bg-info-50 dark:bg-info-900/30 border border-info-200 dark:border-info-800 rounded-lg p-4 animate-pulse"
		role="status"
		aria-live="polite"
	>
		<div class="flex items-center gap-3">
			<div class="flex-shrink-0">
				<RefreshCw size={20} class="text-info-600 dark:text-info-400 animate-spin" />
			</div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2">
					<h4 class="text-sm font-medium text-info-900 dark:text-info-100">
						{customMessage || message.title}
					</h4>
					<span class="text-xs px-2 py-0.5 rounded-full bg-info-100 dark:bg-info-800 text-info-700 dark:text-info-300">
						{message.estimatedTime}
					</span>
				</div>
				<p class="text-sm text-info-700 dark:text-info-300 mt-1">
					{message.description}
				</p>
			</div>
		</div>
	</div>
{:else}
	<div
		class="bg-success-50 dark:bg-success-900/30 border border-success-200 dark:border-success-800 rounded-lg p-4"
		role="status"
		aria-live="polite"
	>
		<div class="flex items-center gap-3">
			<div class="flex-shrink-0">
				<CheckCircle size={20} class="text-success-600 dark:text-success-400" />
			</div>
			<div class="flex-1 min-w-0">
				<p class="text-sm font-medium text-success-900 dark:text-success-100">
					Connection restored - continuing meeting
				</p>
			</div>
		</div>
	</div>
{/if}
