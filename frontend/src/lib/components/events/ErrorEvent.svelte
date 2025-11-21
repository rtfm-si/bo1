<script lang="ts">
	/**
	 * ErrorEvent Component
	 * Displays error information with recovery status
	 */
	import type { ErrorEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: ErrorEvent;
	}

	let { event }: Props = $props();
</script>

<div class="space-y-3">
	<div
		class="border-l-4 border-error-500 bg-error-50 dark:bg-error-900/20 rounded-lg p-4"
	>
		<div class="flex items-start gap-3">
			<div
				class="flex-shrink-0 w-10 h-10 bg-error-500 dark:bg-error-600 text-white rounded-full flex items-center justify-center"
			>
				<svg
					class="w-5 h-5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
			</div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-2">
					<h3 class="text-base font-semibold text-error-900 dark:text-error-100">
						Error Occurred
					</h3>
					<Badge variant={event.data.recoverable ? 'warning' : 'error'} size="sm">
						{event.data.recoverable ? 'Recoverable' : 'Fatal'}
					</Badge>
					<Badge variant="neutral" size="sm">{event.data.error_type}</Badge>
				</div>

				<p class="text-sm text-error-800 dark:text-error-200 mb-2">
					{event.data.error}
				</p>

				{#if event.data.node}
					<p class="text-xs text-error-700 dark:text-error-300">
						<span class="font-semibold">Node:</span>
						{event.data.node}
					</p>
				{/if}

				{#if event.data.recoverable}
					<div class="mt-3 text-xs text-neutral-600 dark:text-neutral-400">
						The system will attempt to recover from this error automatically.
					</div>
				{:else}
					<div class="mt-3 text-xs text-error-700 dark:text-error-300 font-medium">
						This error cannot be recovered. Please check logs and restart the session.
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
