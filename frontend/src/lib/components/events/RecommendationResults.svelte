<script lang="ts">
	import { eventTokens } from '$lib/design/tokens';
	import type { SSEEvent } from '$lib/api/sse-events';

	interface VoteData {
		persona_code: string;
		persona_name: string;
		recommendation: string;
		confidence: number;
		reasoning: string;
		conditions: string[];
	}

	interface Props {
		event: SSEEvent & {
			data: {
				votes: VoteData[];
				votes_count: number;
				consensus_level: 'strong' | 'moderate' | 'weak' | 'unknown';
				avg_confidence: number;
			};
		};
	}

	let { event }: Props = $props();

	// Track which vote details are expanded
	let expandedVotes = $state<Set<string>>(new Set());

	function toggleVote(personaCode: string) {
		const newExpanded = new Set(expandedVotes);
		if (newExpanded.has(personaCode)) {
			newExpanded.delete(personaCode);
		} else {
			newExpanded.add(personaCode);
		}
		expandedVotes = newExpanded;
	}

	const consensusInfo = $derived(eventTokens.consensus[event.data.consensus_level]);
</script>

<div class="bg-neutral-50 dark:bg-neutral-900/50 rounded-lg p-5 border-2 border-neutral-300 dark:border-neutral-700">
	<!-- Header -->
	<div class="flex items-center justify-between mb-4">
		<div class="flex items-center gap-3">
			<h3 class="text-[1.5rem] font-semibold leading-tight text-neutral-900 dark:text-white">
				Expert Recommendations
			</h3>
		</div>

		<!-- Consensus Indicator -->
		<div class="flex items-center gap-2">
			<span class="text-[0.75rem] text-neutral-600 dark:text-neutral-400">Consensus:</span>
			<span
				class="px-2.5 py-1 {consensusInfo.bg} {consensusInfo.text} text-[0.75rem] font-semibold rounded-full"
			>
				{consensusInfo.label}
			</span>
			<span class="text-[0.75rem] text-neutral-600 dark:text-neutral-400 font-medium">
				({Math.round(event.data.avg_confidence * 100)}%)
			</span>
		</div>
	</div>

	<!-- Votes Grid -->
	<div class="space-y-2.5">
		{#each event.data.votes as vote}
			{@const isExpanded = expandedVotes.has(vote.persona_code)}
			<div class="bg-white dark:bg-neutral-800 rounded-md p-3 border border-neutral-200 dark:border-neutral-700">
				<div class="flex items-start justify-between gap-3">
					<div class="flex-1 min-w-0">
						<!-- Expert name and recommendation -->
						<div class="flex items-center gap-2 mb-1.5">
							<div class="w-7 h-7 bg-neutral-600 dark:bg-neutral-500 rounded-full flex items-center justify-center text-white font-semibold text-xs flex-shrink-0">
								{vote.persona_name.charAt(0)}
							</div>
							<h4 class="text-[1.25rem] font-medium leading-snug text-neutral-800 dark:text-neutral-100">
								{vote.persona_name}
							</h4>
						</div>

						<!-- Recommendation text -->
						<p class="text-[0.875rem] font-medium text-neutral-800 dark:text-neutral-200 mb-1.5 ml-9">
							{vote.recommendation}
						</p>

						<!-- Reasoning toggle button -->
						<button
							onclick={() => toggleVote(vote.persona_code)}
							class="text-[0.75rem] text-brand-600 dark:text-brand-400 hover:underline font-medium ml-9"
						>
							{isExpanded ? 'Hide reasoning' : 'View reasoning'}
						</button>

						<!-- Expandable Reasoning -->
						{#if isExpanded}
							<div class="mt-2 ml-9 pl-3 border-l-2 border-neutral-300 dark:border-neutral-600">
								<p class="text-[0.875rem] text-neutral-600 dark:text-neutral-400 leading-relaxed">
									{vote.reasoning}
								</p>

								<!-- Conditions (if any) -->
								{#if vote.conditions && vote.conditions.length > 0}
									<div class="mt-2 text-[0.75rem]">
										<span class="font-semibold text-neutral-700 dark:text-neutral-300">Conditions:</span>
										<ul class="list-disc list-inside ml-2 mt-0.5 text-neutral-600 dark:text-neutral-400">
											{#each vote.conditions as condition}
												<li>{condition}</li>
											{/each}
										</ul>
									</div>
								{/if}
							</div>
						{/if}
					</div>

					<!-- Confidence Badge -->
					<div class="flex-shrink-0">
						<span class="px-2 py-1 bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 text-[0.75rem] font-semibold rounded">
							{Math.round(vote.confidence * 100)}%
						</span>
					</div>
				</div>
			</div>
		{/each}
	</div>

	<!-- Summary footer -->
	<div class="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700">
		<p class="text-[0.75rem] text-neutral-600 dark:text-neutral-400 text-center">
			{event.data.votes_count} expert{event.data.votes_count !== 1 ? 's' : ''} provided recommendation{event.data.votes_count !== 1 ? 's' : ''}
		</p>
	</div>
</div>
