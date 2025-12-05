<script lang="ts">
	/**
	 * MeetingFailedEvent Component
	 * Displays when sub-problem validation fails before meta-synthesis
	 */
	import type { MeetingFailedEvent } from '$lib/api/sse-events';
	import { ChevronDown, ChevronUp, AlertTriangle } from 'lucide-svelte';
	import { user } from '$lib/stores/auth';

	interface Props {
		event: MeetingFailedEvent;
	}

	let { event }: Props = $props();
	let showDetails = $state(false);
	const isAdmin = $derived($user?.is_admin ?? false);

	const { failed_count, failed_goals, completed_count, total_count, reason } = event.data;
</script>

<div class="space-y-3">
	<div class="border-l-4 border-red-500 bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
		<div class="flex items-start gap-3">
			<div
				class="flex-shrink-0 w-10 h-10 bg-red-500 dark:bg-red-600 text-white rounded-full flex items-center justify-center"
			>
				<AlertTriangle size={20} />
			</div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-2">
					<h3 class="text-base font-semibold text-red-900 dark:text-red-100">
						Meeting Could Not Complete
					</h3>
				</div>

				<p class="text-sm text-red-800 dark:text-red-200 mb-3">
					{failed_count} of {total_count} focus area{total_count > 1 ? 's' : ''} could not be analyzed.
					The expert panel was unable to complete their deliberation on these topics.
				</p>

				<!-- Failed focus areas list -->
				{#if failed_goals.length > 0}
					<div class="mb-3">
						<p class="text-xs font-medium text-red-900 dark:text-red-100 mb-1">
							Affected focus areas:
						</p>
						<ul class="list-disc list-inside text-xs text-red-800 dark:text-red-200 space-y-1">
							{#each failed_goals as goal, i (i)}
								<li>{goal}</li>
							{/each}
						</ul>
					</div>
				{/if}

				{#if completed_count > 0}
					<p class="text-xs text-red-700 dark:text-red-300 mb-3">
						{completed_count} focus area{completed_count > 1 ? 's were' : ' was'} completed successfully,
						but a complete recommendation requires all areas to be analyzed.
					</p>
				{/if}

				<div
					class="mt-3 p-3 bg-red-100 dark:bg-red-900/30 rounded-md border border-red-200 dark:border-red-800"
				>
					<p class="text-xs text-red-900 dark:text-red-100 font-medium mb-1">
						What happens next?
					</p>
					<p class="text-xs text-red-800 dark:text-red-200">
						You won't be charged for this incomplete meeting. Please try starting a new
						meeting, or contact support if this issue persists.
					</p>
				</div>

				<!-- Technical Details (admin-only) -->
				{#if isAdmin}
					<button
						onclick={() => (showDetails = !showDetails)}
						class="mt-3 flex items-center gap-1 text-xs text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-red-100 transition-colors"
					>
						{#if showDetails}
							<ChevronUp size={14} />
						{:else}
							<ChevronDown size={14} />
						{/if}
						{showDetails ? 'Hide' : 'Show'} technical details
					</button>

					{#if showDetails}
						<div
							class="mt-2 p-3 bg-neutral-100 dark:bg-neutral-800 rounded border border-neutral-200 dark:border-neutral-700 text-xs font-mono"
						>
							<div class="mb-2">
								<span class="text-neutral-600 dark:text-neutral-400">Reason:</span>
								<span class="text-neutral-900 dark:text-neutral-100 ml-2">{reason}</span>
							</div>
							<div class="mb-2">
								<span class="text-neutral-600 dark:text-neutral-400">Failed:</span>
								<span class="text-neutral-900 dark:text-neutral-100 ml-2"
									>{failed_count} / {total_count}</span
								>
							</div>
							{#if event.data.failed_ids?.length > 0}
								<div>
									<span class="text-neutral-600 dark:text-neutral-400">Failed IDs:</span>
									<div class="text-neutral-900 dark:text-neutral-100 mt-1">
										{event.data.failed_ids.join(', ')}
									</div>
								</div>
							{/if}
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
</div>
