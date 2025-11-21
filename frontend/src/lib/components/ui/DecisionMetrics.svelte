<script lang="ts">
	/**
	 * DecisionMetrics Component
	 * Shows valuable decision-making metrics during deliberation
	 */
	import type { SSEEvent } from '$lib/api/sse-events';
	import { fade } from 'svelte/transition';

	interface Props {
		events: SSEEvent[];
		currentPhase: string | null;
		currentRound: number | null;
	}

	let { events, currentPhase, currentRound }: Props = $props();

	// Consensus metrics
	const convergenceEvents = $derived(
		events.filter(e => e.event_type === 'convergence')
	);
	const latestConvergence = $derived(
		convergenceEvents.length > 0 ? convergenceEvents[convergenceEvents.length - 1] : null
	);
	const consensusScore = $derived(
		latestConvergence?.data?.consensus_score ?? null
	);
	const noveltyScore = $derived(
		latestConvergence?.data?.novelty_score ?? null
	);

	// Expert contributions
	const contributions = $derived(
		events.filter(e => e.event_type === 'contribution')
	);
	const contributionsByExpert = $derived.by(() => {
		const byExpert = new Map<string, number>();
		contributions.forEach(c => {
			const name = c.data.persona_name || c.data.persona_code || 'Unknown';
			byExpert.set(name, (byExpert.get(name) || 0) + 1);
		});
		return Array.from(byExpert.entries())
			.map(([name, count]) => ({ name, count }))
			.sort((a, b) => b.count - a.count);
	});

	// Votes/Recommendations
	const votes = $derived(
		events.filter(e => e.event_type === 'persona_vote')
	);
	const confidenceLevels = $derived.by(() => {
		return votes
			.map(v => ({
				expert: v.data.persona_name || v.data.persona_code || 'Unknown',
				confidence: v.data.confidence || 0,
			}))
			.sort((a, b) => b.confidence - a.confidence);
	});
	const avgConfidence = $derived(
		confidenceLevels.length > 0
			? confidenceLevels.reduce((sum, v) => sum + v.confidence, 0) / confidenceLevels.length
			: null
	);

	// Moderator interventions
	const interventions = $derived(
		events.filter(e => e.event_type === 'moderator_intervention').length
	);

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.8) return 'text-green-600 dark:text-green-400';
		if (confidence >= 0.6) return 'text-yellow-600 dark:text-yellow-400';
		return 'text-red-600 dark:text-red-400';
	}

	function getConsensusLabel(score: number): string {
		if (score >= 0.85) return 'High Consensus';
		if (score >= 0.70) return 'Moderate Consensus';
		if (score >= 0.50) return 'Low Consensus';
		return 'No Consensus';
	}

	function getConsensusColor(score: number): string {
		if (score >= 0.85) return 'text-green-600 dark:text-green-400';
		if (score >= 0.70) return 'text-blue-600 dark:text-blue-400';
		if (score >= 0.50) return 'text-yellow-600 dark:text-yellow-400';
		return 'text-red-600 dark:text-red-400';
	}
</script>

<div class="space-y-4">
	<!-- Consensus Metrics -->
	{#if consensusScore !== null}
		<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-4" transition:fade>
			<h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
				</svg>
				Consensus
			</h3>
			<div class="space-y-3">
				<div>
					<div class="flex items-center justify-between mb-1">
						<span class="text-xs text-slate-600 dark:text-slate-400">Agreement</span>
						<span class="text-xs font-medium {getConsensusColor(consensusScore)}">
							{getConsensusLabel(consensusScore)}
						</span>
					</div>
					<div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
						<div
							class="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full transition-all duration-500"
							style="width: {consensusScore * 100}%"
						></div>
					</div>
					<p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
						{(consensusScore * 100).toFixed(0)}% alignment
					</p>
				</div>
				{#if noveltyScore !== null}
					<div>
						<div class="flex items-center justify-between mb-1">
							<span class="text-xs text-slate-600 dark:text-slate-400">New Ideas</span>
							<span class="text-xs font-medium text-purple-600 dark:text-purple-400">
								{noveltyScore < 0.3 ? 'Converging' : 'Exploring'}
							</span>
						</div>
						<div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
							<div
								class="bg-gradient-to-r from-purple-500 to-purple-600 h-2 rounded-full transition-all duration-500"
								style="width: {noveltyScore * 100}%"
							></div>
						</div>
						<p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
							{noveltyScore < 0.3 ? 'Experts aligning on solution' : 'Still exploring new ideas'}
						</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Expert Confidence -->
	{#if avgConfidence !== null && confidenceLevels.length > 0}
		<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-4" transition:fade>
			<h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				Confidence
			</h3>
			<div class="mb-3">
				<div class="flex items-center justify-between mb-1">
					<span class="text-xs text-slate-600 dark:text-slate-400">Average</span>
					<span class="text-sm font-bold {getConfidenceColor(avgConfidence)}">
						{(avgConfidence * 100).toFixed(0)}%
					</span>
				</div>
				<div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
					<div
						class="bg-gradient-to-r from-green-500 to-green-600 h-2 rounded-full transition-all duration-500"
						style="width: {avgConfidence * 100}%"
					></div>
				</div>
			</div>
			<div class="space-y-2">
				{#each confidenceLevels.slice(0, 5) as { expert, confidence }}
					<div class="flex items-center justify-between text-xs">
						<span class="text-slate-700 dark:text-slate-300 truncate flex-1">{expert}</span>
						<span class="font-medium {getConfidenceColor(confidence)} ml-2">
							{(confidence * 100).toFixed(0)}%
						</span>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Contribution Stats -->
	{#if contributionsByExpert.length > 0}
		<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-4" transition:fade>
			<h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z" />
				</svg>
				Contributions
			</h3>
			<div class="space-y-2">
				{#each contributionsByExpert as { name, count }}
					{@const maxCount = Math.max(...contributionsByExpert.map(c => c.count))}
					<div class="flex items-center gap-2">
						<div class="flex-1">
							<div class="flex items-center justify-between mb-1">
								<span class="text-xs text-slate-700 dark:text-slate-300 truncate">{name}</span>
								<span class="text-xs font-medium text-slate-600 dark:text-slate-400">{count}</span>
							</div>
							<div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5">
								<div
									class="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
									style="width: {(count / maxCount) * 100}%"
								></div>
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Decision Quality Indicators -->
	<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-4">
		<h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
			</svg>
			Activity
		</h3>
		<dl class="space-y-2 text-xs">
			{#if currentRound}
				<div class="flex items-center justify-between">
					<dt class="text-slate-600 dark:text-slate-400">Rounds</dt>
					<dd class="font-medium text-slate-900 dark:text-white">{currentRound}</dd>
				</div>
			{/if}
			<div class="flex items-center justify-between">
				<dt class="text-slate-600 dark:text-slate-400">Contributions</dt>
				<dd class="font-medium text-slate-900 dark:text-white">{contributions.length}</dd>
			</div>
			{#if interventions > 0}
				<div class="flex items-center justify-between">
					<dt class="text-slate-600 dark:text-slate-400">Interventions</dt>
					<dd class="font-medium text-orange-600 dark:text-orange-400">{interventions}</dd>
				</div>
			{/if}
			{#if votes.length > 0}
				<div class="flex items-center justify-between">
					<dt class="text-slate-600 dark:text-slate-400">Recommendations</dt>
					<dd class="font-medium text-slate-900 dark:text-white">{votes.length}</dd>
				</div>
			{/if}
		</dl>
	</div>
</div>
