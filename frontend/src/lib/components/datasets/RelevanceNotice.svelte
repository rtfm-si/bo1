<script lang="ts">
	/**
	 * RelevanceNotice - Non-blocking relevance info display
	 *
	 * Shows how well the dataset aligns with user objectives.
	 * High: Badge showing alignment percentage
	 * Medium: Partial match notice with suggestions
	 * Low: Open exploration notice
	 */
	import type { ObjectiveRelevanceAssessment, ObjectiveMatch } from '$lib/api/types';

	interface Props {
		relevanceScore: number;
		relevanceAssessment?: ObjectiveRelevanceAssessment | null;
		onContinue?: () => void;
		compact?: boolean;
	}

	let { relevanceScore, relevanceAssessment = null, onContinue, compact = false }: Props = $props();

	let expanded = $state(false);

	// Relevance level derived from score
	const relevanceLevel = $derived.by(() => {
		if (relevanceScore >= 70) return 'high';
		if (relevanceScore >= 40) return 'medium';
		return 'low';
	});

	function getScoreColor(score: number): string {
		if (score >= 70) return 'text-success-600 dark:text-success-400';
		if (score >= 40) return 'text-warning-600 dark:text-warning-400';
		return 'text-neutral-500 dark:text-neutral-400';
	}

	function getScoreBg(score: number): string {
		if (score >= 70) return 'bg-success-100 dark:bg-success-900/30 border-success-200 dark:border-success-800';
		if (score >= 40) return 'bg-warning-100 dark:bg-warning-900/30 border-warning-200 dark:border-warning-800';
		return 'bg-neutral-100 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700';
	}

	function getMatchIcon(relevance: string): string {
		switch (relevance) {
			case 'high':
				return 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z';
			case 'medium':
				return 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
			case 'low':
			case 'none':
				return 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z';
			default:
				return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
		}
	}

	function getMatchColor(relevance: string): string {
		switch (relevance) {
			case 'high':
				return 'text-success-600 dark:text-success-400';
			case 'medium':
				return 'text-warning-600 dark:text-warning-400';
			default:
				return 'text-neutral-400 dark:text-neutral-500';
		}
	}

	const highMatches = $derived(
		relevanceAssessment?.objective_matches?.filter((m) => m.relevance === 'high') ?? []
	);
	const mediumMatches = $derived(
		relevanceAssessment?.objective_matches?.filter((m) => m.relevance === 'medium') ?? []
	);
	const lowMatches = $derived(
		relevanceAssessment?.objective_matches?.filter(
			(m) => m.relevance === 'low' || m.relevance === 'none'
		) ?? []
	);
</script>

{#if compact}
	<!-- Compact badge version -->
	<span
		class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium {getScoreBg(relevanceScore)} {getScoreColor(relevanceScore)}"
	>
		{#if relevanceLevel === 'high'}
			<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
			</svg>
		{:else if relevanceLevel === 'medium'}
			<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
			</svg>
		{/if}
		{relevanceScore}% aligned
	</span>
{:else}
	<!-- Full notice version -->
	<div class="rounded-lg border {getScoreBg(relevanceScore)} overflow-hidden">
		<!-- Header -->
		<button
			onclick={() => (expanded = !expanded)}
			class="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/50 dark:hover:bg-black/10 transition-colors"
		>
			<div class="flex items-center gap-3">
				{#if relevanceLevel === 'high'}
					<svg class="w-5 h-5 text-success-600 dark:text-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<span class="text-sm font-medium text-success-700 dark:text-success-300">
						{relevanceScore}% aligned with your objectives
					</span>
				{:else if relevanceLevel === 'medium'}
					<svg class="w-5 h-5 text-warning-600 dark:text-warning-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<span class="text-sm font-medium text-warning-700 dark:text-warning-300">
						{relevanceScore}% aligned with your objectives
					</span>
				{:else}
					<svg class="w-5 h-5 text-neutral-500 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">
						About this analysis
					</span>
				{/if}
			</div>
			{#if relevanceAssessment}
				<svg
					class="w-5 h-5 text-neutral-400 transition-transform {expanded ? 'rotate-180' : ''}"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
			{/if}
		</button>

		<!-- Expanded details -->
		{#if expanded && relevanceAssessment}
			<div class="px-4 pb-4 pt-1 border-t border-inherit">
				<!-- Summary -->
				{#if relevanceAssessment.assessment_summary}
					<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
						{relevanceAssessment.assessment_summary}
					</p>
				{/if}

				<!-- Objective matches -->
				{#if relevanceAssessment.objective_matches && relevanceAssessment.objective_matches.length > 0}
					<div class="mb-3">
						<p class="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-2">Objective alignment:</p>
						<div class="space-y-1.5">
							{#if highMatches.length > 0}
								{#each highMatches as match}
									<div class="flex items-center gap-2 text-sm">
										<svg class="w-4 h-4 {getMatchColor('high')}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getMatchIcon('high')} />
										</svg>
										<span class="text-neutral-700 dark:text-neutral-300">{match.objective_name}</span>
										<span class="text-xs text-success-600 dark:text-success-400">- strong match</span>
									</div>
								{/each}
							{/if}
							{#if mediumMatches.length > 0}
								{#each mediumMatches as match}
									<div class="flex items-center gap-2 text-sm">
										<svg class="w-4 h-4 {getMatchColor('medium')}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getMatchIcon('medium')} />
										</svg>
										<span class="text-neutral-700 dark:text-neutral-300">{match.objective_name}</span>
										<span class="text-xs text-warning-600 dark:text-warning-400">- partial match</span>
									</div>
								{/each}
							{/if}
							{#if lowMatches.length > 0}
								{#each lowMatches as match}
									<div class="flex items-center gap-2 text-sm">
										<svg class="w-4 h-4 {getMatchColor('low')}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getMatchIcon('low')} />
										</svg>
										<span class="text-neutral-700 dark:text-neutral-300">{match.objective_name}</span>
										<span class="text-xs text-neutral-500 dark:text-neutral-400">- limited data</span>
									</div>
								{/each}
							{/if}
						</div>
					</div>
				{/if}

				<!-- Missing data suggestions -->
				{#if relevanceAssessment.missing_data && relevanceAssessment.missing_data.length > 0}
					<div class="mb-3">
						<p class="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-2">To strengthen analysis, add:</p>
						<ul class="list-disc list-inside text-sm text-neutral-600 dark:text-neutral-400 space-y-1">
							{#each relevanceAssessment.missing_data.slice(0, 3) as missing}
								<li>{missing.data_needed}</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Continue button -->
				{#if onContinue && relevanceLevel !== 'high'}
					<button
						onclick={onContinue}
						class="inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 transition-colors"
					>
						{#if relevanceLevel === 'medium'}
							Continue with analysis
						{:else}
							Continue with open exploration
						{/if}
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
						</svg>
					</button>
				{/if}
			</div>
		{/if}
	</div>
{/if}
