<script lang="ts">
	/**
	 * DeadlockResolution - Post-synthesis UI when experts are split.
	 * Extends in-deliberation deadlock detection to give structured resolution tools.
	 */
	import { goto } from '$app/navigation';
	import { AlertCircle, ArrowRight } from 'lucide-svelte';
	import type { OptionCard } from '$lib/api/sse-events';

	interface Props {
		options: OptionCard[];
		sessionId: string;
		problemStatement: string;
	}

	let { options, sessionId, problemStatement }: Props = $props();

	// Show top-2 options for side-by-side comparison
	const topOptions = $derived(options.slice(0, 2));

	// Ephemeral textarea values per option
	let optionReflections = $state<Record<string, string>>({});

	function startFollowup() {
		const topic = `Follow-up: Resolve split between "${topOptions.map((o) => o.label).join('" and "')}"`;
		const params = new URLSearchParams({
			followup: sessionId,
			q: `${problemStatement}\n\n[Follow-up from previous meeting: experts were split. Focus on resolving: ${topic}]`
		});
		goto(`/meeting/new?${params.toString()}`);
	}
</script>

<div class="border-l-4 border-error-400 bg-error-50 dark:bg-error-900/20 rounded-r-lg p-4 space-y-4">
	<div class="flex items-start gap-3">
		<AlertCircle class="w-5 h-5 text-error-500 dark:text-error-400 flex-shrink-0 mt-0.5" />
		<div>
			<h3 class="text-sm font-semibold text-error-900 dark:text-error-100">
				Low Consensus
			</h3>
			<p class="text-sm text-error-800 dark:text-error-300 mt-1">
				Experts are split on this decision. Compare the top options below before choosing.
			</p>
		</div>
	</div>

	{#if topOptions.length >= 2}
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			{#each topOptions as option (option.id)}
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 space-y-3">
					<h4 class="font-medium text-sm text-neutral-900 dark:text-white">{option.label}</h4>

					{#if option.conditions.length > 0}
						<div>
							<p class="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">Conditions for success</p>
							<ul class="text-xs text-neutral-700 dark:text-neutral-300 space-y-0.5">
								{#each option.conditions.slice(0, 3) as condition, ci (ci)}
									<li class="flex items-start gap-1">
										<span class="text-success-500 mt-0.5">+</span>
										{condition}
									</li>
								{/each}
							</ul>
						</div>
					{/if}

					{#if option.tradeoffs.length > 0}
						<div>
							<p class="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">Tradeoffs</p>
							<ul class="text-xs text-neutral-700 dark:text-neutral-300 space-y-0.5">
								{#each option.tradeoffs.slice(0, 3) as tradeoff, ti (ti)}
									<li class="flex items-start gap-1">
										<span class="text-warning-500 mt-0.5">~</span>
										{tradeoff}
									</li>
								{/each}
							</ul>
						</div>
					{/if}

					<div>
						<label for={`reflection-${option.id}`} class="text-xs font-medium text-neutral-500 dark:text-neutral-400 block mb-1">
							What would need to be true for "{option.label}" to be right?
						</label>
						<textarea
							id={`reflection-${option.id}`}
							bind:value={optionReflections[option.id]}
							placeholder="Think about the conditions..."
							rows="2"
							class="w-full px-2 py-1.5 text-xs bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded focus:outline-none focus:border-info-500"
						></textarea>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	<div class="flex justify-end">
		<button
			onclick={startFollowup}
			class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-info-600 hover:bg-info-700 rounded-lg transition-colors"
		>
			Start focused follow-up
			<ArrowRight class="w-4 h-4" />
		</button>
	</div>
</div>
