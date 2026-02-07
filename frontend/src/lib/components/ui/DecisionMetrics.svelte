<script lang="ts">
	/**
	 * DecisionMetrics Component
	 * Shows valuable decision-making metrics during deliberation
	 * Updated with natural language labels (P0 UX Metrics Refactor)
	 */
	import type { SSEEvent } from '$lib/api/sse-events';
	import { fade } from 'svelte/transition';
	import {
		getOverallQuality,
		getConvergenceMetaphor,
		getConflictLabel,
		type QualityLabel
	} from '$lib/utils/quality-labels';
	import {
		filterEventsByType,
		filterEventsBySubProblem,
		getLatestEvent
	} from '$lib/utils/event-filters';
	import { getConfidenceColor } from '$lib/utils/colors';
	import {
		Lightbulb,
		Search,
		ShieldCheck,
		MessageSquare,
		GitBranch
	} from 'lucide-svelte';

	interface Props {
		events: SSEEvent[];
		currentPhase: string | null;
		currentRound: number | null;
		activeSubProblemIndex?: number | null;  // NEW
		totalSubProblems?: number;               // NEW
	}

	let {
		events,
		currentPhase,
		currentRound,
		activeSubProblemIndex = null,
		totalSubProblems = 1
	}: Props = $props();

	// Filter events by active sub-problem using utility
	const filteredEvents = $derived(
		filterEventsBySubProblem(events, activeSubProblemIndex, totalSubProblems)
	);

	// Discussion quality status events using utility
	const statusEvents = $derived(
		filterEventsByType(events, 'discussion_quality_status', activeSubProblemIndex, totalSubProblems)
	);
	const latestStatus = $derived(
		statusEvents.length > 0 ? statusEvents[statusEvents.length - 1] : null
	);

	// Convergence metrics using utility
	const convergenceEvents = $derived(
		filterEventsByType(events, 'convergence', activeSubProblemIndex, totalSubProblems)
	);
	const latestConvergence = $derived(
		convergenceEvents.length > 0 ? convergenceEvents[convergenceEvents.length - 1] : null
	);
	// Extract all metrics from convergence events
	const metrics = $derived.by(() => {
		if (!latestConvergence) {
			console.log('[DecisionMetrics] No convergence events yet, count:', convergenceEvents.length);
			return null;
		}
		const data = latestConvergence.data as any;

		// DEBUG: Log what we're receiving
		console.log('[DecisionMetrics] Latest convergence data:', {
			exploration_score: data.exploration_score,
			score: data.score,
			focus_score: data.focus_score,
			novelty_score: data.novelty_score,
			conflict_score: data.conflict_score,
			meeting_completeness_index: data.meeting_completeness_index,
			round: data.round,
			max_rounds: data.max_rounds,
			phase: data.phase,
			timestamp: latestConvergence.timestamp
		});

		const result = {
			exploration_score: typeof data.exploration_score === 'number' ? data.exploration_score : null,
			convergence_score: typeof data.score === 'number' ? data.score : null, // Note: 'score' field = convergence
			focus_score: typeof data.focus_score === 'number' ? data.focus_score : null,
			novelty_score: typeof data.novelty_score === 'number' ? data.novelty_score : null,
			conflict_score: typeof data.conflict_score === 'number' ? data.conflict_score : null,
			meeting_completeness_index: typeof data.meeting_completeness_index === 'number' ? data.meeting_completeness_index : null,
			round: typeof data.round === 'number' ? data.round : (currentRound ?? 1),
			max_rounds: typeof data.max_rounds === 'number' ? data.max_rounds : 6,
			phase: data.phase as string | undefined
		};

		console.log('[DecisionMetrics] Extracted metrics:', result);
		return result;
	});

	// Check if meeting is complete
	const isMeetingComplete = $derived(
		currentPhase === 'complete' ||
		currentPhase === 'synthesis' ||
		events.some(e => e.event_type === 'synthesis_complete' || e.event_type === 'meta_synthesis_complete')
	);

	// Translate metrics to user-friendly labels
	// Phase-aware: pass currentPhase to show completion status
	const overallQuality = $derived.by((): QualityLabel | null => {
		if (metrics) {
			const quality = getOverallQuality(metrics, currentPhase);
			// Override label when meeting is complete to avoid contradictory states
			if (isMeetingComplete && quality) {
				return {
					...quality,
					label: 'Discussion Complete',
					description: 'Experts have concluded their deliberation and reached recommendations.',
					color: 'green',
				};
			}
			return quality;
		}

		// Fallback: meeting complete but no metrics yet
		if (isMeetingComplete) {
			return {
				label: 'Discussion Complete',
				description: 'Experts have concluded their deliberation and reached recommendations.',
				color: 'green',
				icon: 'check-circle'
			};
		}

		return null;
	});

	const convergenceMetaphor = $derived.by(() => {
		if (!metrics || metrics.convergence_score === null) return null;

		// Pass phase/status for phase-aware labels
		const phase = metrics.phase || currentPhase;

		return getConvergenceMetaphor(
			metrics.convergence_score,
			metrics.novelty_score,
			metrics.round ?? 1,
			phase
		);
	});

	const conflictLabel = $derived.by(() => {
		if (!metrics || metrics.conflict_score === null) return null;
		return getConflictLabel(
			metrics.conflict_score,
			metrics.round ?? 1,
			metrics.max_rounds ?? 6
		);
	});

	// Expert contributions
	const contributions = $derived(
		filteredEvents.filter(e => e.event_type === 'contribution')
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
		filteredEvents.filter(e => e.event_type === 'persona_vote')
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

	// Moderator interventions using utility
	const interventions = $derived(
		filterEventsByType(filteredEvents, 'moderator_intervention', activeSubProblemIndex, totalSubProblems).length
	);

	// ============================================================================
	// Deliberation Progress Counters (TODO.md Tier 1)
	// Uses multiple fallback sources since not all events are always emitted
	// ============================================================================

	// Topics explored = sub-problems from decomposition_complete OR unique sub_problem_index from contributions
	const topicsExplored = $derived.by(() => {
		// Try decomposition_complete first (most reliable)
		const decompositionEvent = events.find(e => e.event_type === 'decomposition_complete');
		if (decompositionEvent) {
			const count = (decompositionEvent.data as any).count ||
				(decompositionEvent.data as any).sub_problems?.length || 0;
			if (count > 0) return count;
		}

		// Fallback: count unique sub_problem_index from contributions
		const subProblemIndexes = new Set(
			contributions.map((c: any) => c.data.sub_problem_index ?? 0)
		);
		return Math.max(subProblemIndexes.size, 1); // At least 1 topic
	});

	// Research performed = facilitator decisions to research
	const researchPerformed = $derived(
		events.filter(e =>
			e.event_type === 'facilitator_decision' &&
			(e.data as any).action === 'research'
		).length
	);

	// Risks mitigated = contributions mentioning risk keywords
	const risksMitigated = $derived.by(() => {
		const riskKeywords = ['risk', 'caution', 'concern', 'warning', 'threat', 'downside', 'danger'];
		const riskContributions = contributions.filter(c => {
			const content = ((c.data as any).content || '').toLowerCase();
			return riskKeywords.some(keyword => content.includes(keyword));
		}).length;

		return Math.min(riskContributions, 99); // Cap display
	});

	// Rounds completed = max round number from contributions or convergence events
	const roundsCompleted = $derived.by(() => {
		const roundsFromContributions = contributions.map((c: any) => c.data.round || 0);
		const roundsFromConvergence = convergenceEvents.map((c: any) => c.data.round || 0);
		const allRounds = [...roundsFromContributions, ...roundsFromConvergence];
		return allRounds.length > 0 ? Math.max(...allRounds) : 0;
	});

	// Total contributions count
	const totalContributions = $derived(contributions.length);

	// Counter data structure for UI
	const progressCounters = $derived([
		{
			icon: Lightbulb,
			count: topicsExplored,
			label: 'Focus Areas',
			title: 'Focus Areas Analyzed',
			color: 'text-warning-500'
		},
		{
			icon: GitBranch,
			count: roundsCompleted,
			label: 'Rounds',
			title: 'Discussion Rounds',
			color: 'text-info-500'
		},
		{
			icon: ShieldCheck,
			count: risksMitigated,
			label: 'Risks',
			title: 'Risks Identified',
			color: 'text-error-500'
		},
		{
			icon: Search,
			count: researchPerformed,
			label: 'Research',
			title: 'Research Triggered',
			color: 'text-success-500'
		},
		{
			icon: MessageSquare,
			count: totalContributions,
			label: 'Contributions',
			title: 'Expert Contributions',
			color: 'text-purple-500'
		}
	]);
</script>

<div class="space-y-4">
	<!-- Deliberation Progress Counters (TODO.md Tier 1) -->
	{#if progressCounters.some(c => c.count > 0)}
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-4" transition:fade>
			<h3 class="text-sm font-semibold text-neutral-900 dark:text-white mb-3">
				Deliberation Progress
			</h3>
			<div class="grid grid-cols-5 gap-2">
				{#each progressCounters as counter (counter.label)}
					<div
						class="flex flex-col items-center p-2 rounded-lg bg-neutral-50 dark:bg-neutral-900/50 hover:bg-neutral-100 dark:hover:bg-neutral-900 transition-colors cursor-default"
						title={counter.title}
					>
						<div class={counter.color}>
							<counter.icon size={18} />
						</div>
						<span class="text-lg font-bold text-neutral-900 dark:text-white mt-1">
							{counter.count}
						</span>
						<span class="text-xs text-neutral-500 dark:text-neutral-400 truncate">
							{counter.label}
						</span>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Context indicator for multi-sub-problem scenarios -->
	{#if totalSubProblems > 1}
		<div class="bg-info-50 dark:bg-info-900/20 rounded-lg border border-info-200 dark:border-info-800 p-3 mb-4">
			<p class="text-xs text-info-800 dark:text-info-200">
				{#if activeSubProblemIndex !== null}
					Showing metrics for <strong>Sub-Problem {activeSubProblemIndex + 1}</strong>
				{:else}
					Showing overall metrics across all sub-problems
				{/if}
			</p>
		</div>
	{/if}

	<!-- Discussion Quality (Natural Language - P0 UX Refactor) -->
	<!-- Show status message if no quality metrics yet, otherwise show quality -->
	{#if !overallQuality && latestStatus}
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-4" transition:fade>
			<h3 class="text-sm font-semibold text-neutral-900 dark:text-white mb-3 flex items-center gap-2">
				<svg class="w-4 h-4 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				Discussion Quality
			</h3>
			<div class="flex items-center gap-2 p-3 bg-info-50 dark:bg-info-900/20 rounded">
				<svg class="w-5 h-5 text-info-600 dark:text-info-400 animate-spin" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<span class="text-sm text-neutral-700 dark:text-neutral-300">
					{(latestStatus.data as { message: string }).message}
				</span>
			</div>
		</div>
	{:else if overallQuality}
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-4" transition:fade>
			<h3 class="text-sm font-semibold text-neutral-900 dark:text-white mb-3 flex items-center gap-2">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				Discussion Quality
			</h3>

			<div class="flex items-center justify-between mb-2">
				<span class="text-lg font-semibold text-neutral-900 dark:text-white">
					{overallQuality.label}
				</span>
				<span class="px-2 py-1 rounded-full text-xs font-medium {
					overallQuality.color === 'green' ? 'bg-success-100 text-success-800 dark:bg-success-900/20 dark:text-success-400' :
					overallQuality.color === 'amber' ? 'bg-warning-100 text-warning-800 dark:bg-warning-900/20 dark:text-warning-400' :
					'bg-info-100 text-info-800 dark:bg-info-900/20 dark:text-info-400'
				}">
					{#if isMeetingComplete}
						✓ Complete
					{:else}
						{overallQuality.color === 'green' ? 'Excellent' : overallQuality.color === 'amber' ? 'Good' : 'Early'}
					{/if}
				</span>
			</div>

			<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
				{overallQuality.description}
			</p>

			<!-- Optional: Show phase-specific insight (hidden when meeting complete - redundant) -->
			{#if convergenceMetaphor && !isMeetingComplete}
				<div class="flex items-start gap-2 p-2 bg-neutral-50 dark:bg-neutral-900 rounded">
					<svg class="w-4 h-4 mt-0.5 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
					</svg>
					<div class="flex-1">
						<p class="text-xs font-medium text-neutral-700 dark:text-neutral-300">
							{convergenceMetaphor.status}
						</p>
						<p class="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5">
							{convergenceMetaphor.description}
						</p>
					</div>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Expert Confidence -->
	{#if avgConfidence !== null && confidenceLevels.length > 0}
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-4" transition:fade>
			<h3 class="text-sm font-semibold text-neutral-900 dark:text-white mb-3 flex items-center gap-2">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				Confidence
			</h3>
			<div class="mb-3">
				<div class="flex items-center justify-between mb-1">
					<span class="text-xs text-neutral-600 dark:text-neutral-400">Average</span>
					<span class="text-sm font-bold {getConfidenceColor(avgConfidence)}">
						{(avgConfidence * 100).toFixed(0)}%
					</span>
				</div>
				<div class="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
					<div
						class="bg-gradient-to-r from-success-500 to-success-600 h-2 rounded-full transition-all duration-500"
						style="width: {avgConfidence * 100}%"
					></div>
				</div>
			</div>
			<div class="space-y-2">
				{#each confidenceLevels.slice(0, 5) as { expert, confidence }}
					<div class="flex items-center justify-between text-xs">
						<span class="text-neutral-700 dark:text-neutral-300 truncate flex-1">{expert}</span>
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
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-4" transition:fade>
			<h3 class="text-sm font-semibold text-neutral-900 dark:text-white mb-3 flex items-center gap-2">
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
								<span class="text-xs text-neutral-700 dark:text-neutral-300 truncate">{name}</span>
								<span class="text-xs font-medium text-neutral-600 dark:text-neutral-400">{count}</span>
							</div>
							<div class="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-1.5">
								<div
									class="bg-info-500 h-1.5 rounded-full transition-all duration-300"
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
