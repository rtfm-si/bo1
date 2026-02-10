<script lang="ts">
	/**
	 * GroupthinkWarning - Post-synthesis warning when all experts agree too strongly.
	 * Extends the in-deliberation contrarian moderator to decision-time UI.
	 */
	import { AlertCircle, ChevronDown, ChevronUp, X } from 'lucide-svelte';

	interface Props {
		avgConfidence: number;
		onpremortem?: (text: string) => void;
	}

	let { avgConfidence, onpremortem }: Props = $props();

	let dismissed = $state(false);
	let expanded = $state(false);
	let premortemText = $state('');

	$effect(() => {
		onpremortem?.(premortemText);
	});
</script>

{#if !dismissed}
	<div class="border-l-4 border-warning-500 bg-warning-50 dark:bg-warning-900/20 rounded-r-lg p-4">
		<div class="flex items-start gap-3">
			<AlertCircle class="w-5 h-5 text-warning-600 dark:text-warning-400 flex-shrink-0 mt-0.5" />
			<div class="flex-1 min-w-0">
				<div class="flex items-start justify-between gap-2">
					<div>
						<h3 class="text-sm font-semibold text-warning-900 dark:text-warning-100">
							Possible Groupthink
						</h3>
						<p class="text-sm text-warning-800 dark:text-warning-300 mt-1">
							All experts agree with {Math.round(avgConfidence * 100)}% confidence and no dissenting views.
							Consider what they might be missing.
						</p>
					</div>
					<button
						onclick={() => (dismissed = true)}
						class="flex-shrink-0 p-1 text-warning-500 hover:text-warning-700 dark:hover:text-warning-300 rounded"
						aria-label="Dismiss warning"
					>
						<X class="w-4 h-4" />
					</button>
				</div>

				<button
					onclick={() => (expanded = !expanded)}
					class="mt-2 inline-flex items-center gap-1 text-xs font-medium text-warning-700 dark:text-warning-300 hover:text-warning-900 dark:hover:text-warning-100"
				>
					{#if expanded}
						<ChevronUp class="w-3.5 h-3.5" />
						Hide pre-mortem exercise
					{:else}
						<ChevronDown class="w-3.5 h-3.5" />
						Try a pre-mortem exercise
					{/if}
				</button>

				{#if expanded}
					<div class="mt-3 space-y-2">
						<p class="text-xs text-warning-700 dark:text-warning-400">
							Imagine this decision failed in 6 months. What went wrong?
						</p>
						<textarea
							bind:value={premortemText}
							placeholder="List possible failure modes..."
							rows="3"
							class="w-full px-3 py-2 text-sm bg-white dark:bg-neutral-800 border border-warning-300 dark:border-warning-700 rounded-lg focus:outline-none focus:border-warning-500"
						></textarea>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
