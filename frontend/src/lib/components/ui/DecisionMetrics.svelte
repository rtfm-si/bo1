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

	// Convergence metrics (from convergence events)
	const convergenceEvents = $derived(
		events.filter(e => e.event_type === 'convergence')
	);
	const latestConvergence = $derived(
		convergenceEvents.length > 0 ? convergenceEvents[convergenceEvents.length - 1] : null
	);
	const convergenceScore = $derived.by(() => {
		if (!latestConvergence) return null;
		const data = latestConvergence.data as any;
		// Convergence event has 'score' field (not consensus_score)
		return typeof data.score === 'number' ? data.score : null;
	});
	const noveltyScore = $derived.by(() => {
		if (!latestConvergence) return null;
		const data = latestConvergence.data as any;
		return typeof data.novelty_score === 'number' ? data.novelty_score : null;
	});
	const conflictScore = $derived.by(() => {
		if (!latestConvergence) return null;
		const data = latestConvergence.data as any;
		return typeof data.conflict_score === 'number' ? data.conflict_score : null;
	});

	// Expert contributions
	const contributions = $derived(
		events.filter(e => e.event_type === 'contribution')
	);
	const contributionsByExpert = $derived.by(() => {
		const byExpert = new Map<string, number>();
		contributions.forEach(c => {
			const data = c.data as any;
			const name = data.persona_name || data.persona_code || 'Unknown';
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
			.map(v => {
				const data = v.data as any;
				return {
					expert: data.persona_name || data.persona_code || 'Unknown',
					confidence: typeof data.confidence === 'number' ? data.confidence : 0,
				};
			})
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

	function getConvergenceLabel(score: number): string {
		if (score >= 0.90) return 'Strongly Converged';
		if (score >= 0.85) return 'Converged';
		if (score >= 0.70) return 'Moderate Agreement';
		if (score >= 0.50) return 'Exploring';
		return 'Divergent';
	}

	function getConvergenceColor(score: number): string {
		if (score >= 0.85) return 'text-green-600 dark:text-green-400';
		if (score >= 0.70) return 'text-blue-600 dark:text-blue-400';
		if (score >= 0.50) return 'text-yellow-600 dark:text-yellow-400';
		return 'text-red-600 dark:text-red-400';
	}
</script>

<div class="space-y-4">
	<!-- Convergence Metrics (moved from timeline to sidebar) -->
	{#if convergenceScore !== null}
		{@const score = convergenceScore}
		<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-4" transition:fade>
			<h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
				</svg>
				Convergence
			</h3>
			<div class="space-y-3">
				<div>
					<div class="flex items-center justify-between mb-1">
						<span class="text-xs text-slate-600 dark:text-slate-400">Agreement</span>
						<span class="text-xs font-medium {getConvergenceColor(score)}">
							{getConvergenceLabel(score)}
						</span>
					</div>
					<div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
						<div
							class="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full transition-all duration-500"
							style="width: {score * 100}%"
						></div>
					</div>
					<p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
						{(score * 100).toFixed(0)}% similarity between expert opinions
					</p>
				</div>
				{#if noveltyScore !== null}
					{@const nScore = noveltyScore}
					<div>
						<div class="flex items-center justify-between mb-1">
							<span class="text-xs text-slate-600 dark:text-slate-400">New Ideas</span>
							<span class="text-xs font-medium text-purple-600 dark:text-purple-400">
								{nScore < 0.3 ? 'Converging' : 'Exploring'}
							</span>
						</div>
						<div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
							<div
								class="bg-gradient-to-r from-purple-500 to-purple-600 h-2 rounded-full transition-all duration-500"
								style="width: {nScore * 100}%"
							></div>
						</div>
						<p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
							{nScore < 0.3 ? 'Experts aligning on solution' : 'Still exploring new ideas'}
						</p>
					</div>
				{/if}
				{#if conflictScore !== null && conflictScore > 0.1}
					{@const cScore = conflictScore}
					<div>
						<div class="flex items-center justify-between mb-1">
							<span class="text-xs text-slate-600 dark:text-slate-400">Conflict</span>
							<span class="text-xs font-medium text-orange-600 dark:text-orange-400">
								{(cScore * 100).toFixed(0)}%
							</span>
						</div>
						<div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
							<div
								class="bg-gradient-to-r from-orange-500 to-orange-600 h-2 rounded-full transition-all duration-500"
								style="width: {cScore * 100}%"
							></div>
						</div>
						<p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
							Experts have differing viewpoints
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

</div>
