<script lang="ts">
	/**
	 * GenericEvent Component
	 * Fallback component for events without specific handlers
	 * Uses humanized event names and descriptions
	 */
	import type { SSEEvent } from '$lib/api/sse-events';
	import { getEventTitle, getEventDescription } from '$lib/utils/event-humanization';

	interface Props {
		event: SSEEvent;
	}

	let { event }: Props = $props();

	const title = $derived(getEventTitle(event.event_type));
	const description = $derived(getEventDescription(event.event_type, event.data));
</script>

<div class="space-y-3">
	<div
		class="bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg p-4"
	>
		<div class="flex items-start gap-3">
			<div
				class="flex-shrink-0 w-10 h-10 bg-info-100 dark:bg-info-900 text-info-800 dark:text-info-200 rounded-full flex items-center justify-center"
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
						d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
			</div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-2">
					<h3 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
						{title}
					</h3>
				</div>

				{#if description}
					<p class="text-sm text-neutral-600 dark:text-neutral-400">
						{description}
					</p>
				{/if}
			</div>
		</div>
	</div>
</div>
