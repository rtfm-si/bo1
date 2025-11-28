<script lang="ts">
	/**
	 * ConvergenceCheck Event Component
	 * Displays convergence status and progress towards consensus with color-coding
	 */
	import type { ConvergenceEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { fade } from 'svelte/transition';
	import {
		getProgressColor,
		getProgressTextColor,
		getProgressStatusMessage,
		getNoveltyColor,
		getConflictColor,
		getDriftColor
	} from '$lib/utils/color-helpers';

	interface Props {
		event: ConvergenceEvent;
	}

	let { event }: Props = $props();

	// Default threshold to 0.85 if not provided
	const threshold = $derived(event.data.threshold ?? 0.85);
	const score = $derived(event.data.score);

	// Calculate ratio once - used by multiple derived values
	const ratio = $derived(score / threshold);
	const percentage = $derived(Math.round(ratio * 100));
	const progressWidth = $derived(Math.min(percentage, 100));

	// Debug convergence rendering
	$effect(() => {
		console.log('[CONVERGENCE RENDER]', {
			score,
			threshold,
			percentage,
			novelty_score: event.data.novelty_score,
			conflict_score: event.data.conflict_score,
			drift_events: event.data.drift_events,
			eventData: event.data,
			round: event.data.round
		});
	});

	// Color coding based on pre-computed ratio
	const progressColor = $derived(getProgressColor(ratio));
	const textColor = $derived(getProgressTextColor(ratio));
	const statusMessage = $derived(getProgressStatusMessage(ratio));

	// Quality metrics helper functions
	function formatScore(score: number | null): string {
		return score !== null && score !== undefined ? Math.round(score * 100) + '%' : 'N/A';
	}

	function getNoveltyLabel(score: number | null): string {
		if (score === null || score === undefined) return 'Not calculated';
		if (score >= 0.7) return 'Fresh ideas';
		if (score >= 0.4) return 'Some novelty';
		return 'Repetitive';
	}

	function getConflictLabel(score: number | null): string {
		if (score === null || score === undefined) return 'Not calculated';
		if (score >= 0.7) return 'High debate';
		if (score >= 0.4) return 'Moderate';
		return 'Low conflict';
	}

	function getDriftLabel(events: number): string {
		if (events === 0) return 'On track';
		if (events <= 2) return 'Minor drift';
		return 'Needs focus';
	}
</script>

<div class="space-y-3">
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-2">
			<h3 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
				Convergence Check
			</h3>
			<Badge variant={event.data.converged ? 'success' : 'info'}>
				{event.data.converged ? 'Converged' : 'In Progress'}
			</Badge>
		</div>
		<div class="text-sm text-neutral-600 dark:text-neutral-400">
			Round {event.data.round}{event.data.max_rounds ? ` / ${event.data.max_rounds}` : ''}
		</div>
	</div>

	<!-- Progress Bar with Color Coding and Text Labels -->
	<div class="space-y-2">
		<div class="flex items-center justify-between text-sm">
			<div class="flex items-center gap-2">
				<span class="text-neutral-600 dark:text-neutral-400">Consensus Score</span>
				<span class="text-xs {textColor} font-medium">
					{statusMessage}
				</span>
			</div>
			<span class="font-semibold text-neutral-900 dark:text-neutral-100">
				{score.toFixed(2)} / {threshold.toFixed(2)}
			</span>
		</div>
		<div class="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-3 overflow-hidden" role="progressbar" aria-valuenow={percentage} aria-valuemin={0} aria-valuemax={100} aria-label="Consensus progress: {statusMessage}">
			<div
				class="{progressColor} h-full transition-all duration-700 ease-out rounded-full"
				style="width: {progressWidth}%"
				transition:fade
			></div>
		</div>
		<div class="flex items-center justify-between text-xs">
			<span class="{textColor} font-medium">
				{percentage}% of threshold - {statusMessage}
			</span>
			{#if event.data.converged}
				<span class="text-green-600 dark:text-green-400 font-semibold flex items-center gap-1">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					Converged
				</span>
			{/if}
		</div>
	</div>

	<!-- NEW: Quality Metrics Grid -->
	<div class="grid grid-cols-3 gap-4 mt-4">
		<!-- Novelty Card -->
		<div class="bg-slate-50 dark:bg-slate-900 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
			<div class="text-xs text-neutral-500 dark:text-neutral-400 mb-1">Novelty</div>
			<div class="text-lg font-bold {getNoveltyColor(event.data.novelty_score)}">
				{formatScore(event.data.novelty_score)}
			</div>
			<div class="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
				{getNoveltyLabel(event.data.novelty_score)}
			</div>
		</div>

		<!-- Conflict Card -->
		<div class="bg-slate-50 dark:bg-slate-900 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
			<div class="text-xs text-neutral-500 dark:text-neutral-400 mb-1">Conflict</div>
			<div class="text-lg font-bold {getConflictColor(event.data.conflict_score)}">
				{formatScore(event.data.conflict_score)}
			</div>
			<div class="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
				{getConflictLabel(event.data.conflict_score)}
			</div>
		</div>

		<!-- Drift Card -->
		<div class="bg-slate-50 dark:bg-slate-900 rounded-lg p-3 border border-slate-200 dark:border-slate-700">
			<div class="text-xs text-neutral-500 dark:text-neutral-400 mb-1">Drift Events</div>
			<div class="text-lg font-bold {getDriftColor(event.data.drift_events)}">
				{event.data.drift_events}
			</div>
			<div class="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
				{getDriftLabel(event.data.drift_events)}
			</div>
		</div>
	</div>

	{#if event.data.should_stop && event.data.stop_reason}
		<div
			class="bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-700 rounded-lg p-3"
		>
			<p class="text-sm text-success-800 dark:text-success-200">
				<span class="font-semibold">Ready to proceed:</span>
				{event.data.stop_reason}
			</p>
		</div>
	{/if}
</div>
