<script lang="ts">
	/**
	 * GoalBanner - Displays north star goal and strategic objectives with progress
	 * Shows prominent goal at dashboard top with edit link
	 * Optionally shows staleness prompt when goal unchanged >30 days
	 * Supports per-objective progress tracking with edit capability
	 */
	import type { ObjectiveProgress } from '$lib/api/types';

	interface Props {
		northStarGoal: string | null | undefined;
		strategicObjectives: string[] | null | undefined;
		/** Progress data keyed by objective index (as string) */
		objectivesProgress?: Record<string, ObjectiveProgress>;
		daysSinceChange?: number | null;
		shouldPromptReview?: boolean;
		/** Callback when user clicks to edit progress for an objective */
		onEditProgress?: (index: number, objective: string, progress: ObjectiveProgress | null) => void;
	}

	let {
		northStarGoal,
		strategicObjectives = [],
		objectivesProgress = {},
		daysSinceChange = null,
		shouldPromptReview = false,
		onEditProgress
	}: Props = $props();

	// Limit display to first 3 objectives
	const displayObjectives = $derived((strategicObjectives ?? []).slice(0, 3));
	const remainingCount = $derived(Math.max(0, (strategicObjectives?.length ?? 0) - 3));
	const hasGoal = $derived(!!northStarGoal);

	// Format days text
	const daysText = $derived(() => {
		if (daysSinceChange === null || daysSinceChange === undefined) return '';
		if (daysSinceChange === 0) return 'Updated today';
		if (daysSinceChange === 1) return 'Updated yesterday';
		return `Updated ${daysSinceChange} days ago`;
	});

	// Get progress for an objective by index
	function getProgress(index: number): ObjectiveProgress | null {
		return objectivesProgress[String(index)] || null;
	}

	// Format progress display
	function formatProgress(progress: ObjectiveProgress): string {
		const unit = progress.unit ? ` ${progress.unit}` : '';
		return `${progress.current}${unit} → ${progress.target}${unit}`;
	}

	// Handle progress click
	function handleProgressClick(index: number, objective: string) {
		if (onEditProgress) {
			onEditProgress(index, objective, getProgress(index));
		}
	}
</script>

{#if hasGoal}
	<!-- Goal Banner with content -->
	<div class="mb-6 bg-gradient-to-r from-brand-50 to-brand-100/50 dark:from-brand-900/20 dark:to-brand-800/10 border border-brand-200 dark:border-brand-800 rounded-lg p-4 sm:p-5">
		<div class="flex items-start gap-3">
			<!-- Target icon -->
			<div class="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-full bg-brand-100 dark:bg-brand-800/50">
				<svg class="w-5 h-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
				</svg>
			</div>

			<div class="flex-1 min-w-0">
				<!-- North star goal -->
				<div class="flex items-start justify-between gap-4">
					<div>
						<span class="text-xs font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wider">North Star Goal</span>
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mt-0.5">
							{northStarGoal}
						</h2>
						{#if daysText()}
							<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
								{daysText()}
								{#if shouldPromptReview}
									<span class="text-amber-600 dark:text-amber-400 ml-1">
										— <a href="/context/strategic" class="hover:underline">Review your goal?</a>
									</span>
								{/if}
							</p>
						{/if}
					</div>
					<a
						href="/context/overview"
						class="flex-shrink-0 text-xs text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 hover:underline transition-colors"
					>
						Edit goal
					</a>
				</div>

				<!-- Strategic objectives -->
				{#if displayObjectives.length > 0}
					<div class="mt-3 pt-3 border-t border-brand-200/50 dark:border-brand-700/50">
						<span class="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1.5 block">Strategic Objectives</span>
						<ul class="space-y-2">
							{#each displayObjectives as objective, idx (idx)}
								{@const progress = getProgress(idx)}
								<li class="flex items-start gap-2 text-sm text-neutral-700 dark:text-neutral-300">
									<svg class="w-4 h-4 text-brand-500 dark:text-brand-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
									</svg>
									<div class="flex-1 min-w-0">
										<span>{objective}</span>
										<!-- Progress indicator -->
										{#if progress}
											<button
												type="button"
												onclick={() => handleProgressClick(idx, objective)}
												class="ml-2 inline-flex items-center gap-1 text-xs text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 bg-brand-50 dark:bg-brand-900/30 px-2 py-0.5 rounded-full transition-colors"
											>
												<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
												</svg>
												{formatProgress(progress)}
											</button>
										{:else if onEditProgress}
											<button
												type="button"
												onclick={() => handleProgressClick(idx, objective)}
												class="ml-2 inline-flex items-center gap-1 text-xs text-neutral-400 dark:text-neutral-500 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
											>
												<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
												</svg>
												Track progress
											</button>
										{/if}
									</div>
								</li>
							{/each}
						</ul>
						{#if remainingCount > 0}
							<a
								href="/context/overview"
								class="text-xs text-brand-600 dark:text-brand-400 hover:underline mt-2 inline-block"
							>
								and {remainingCount} more...
							</a>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>
{:else}
	<!-- Empty state - prompt to set goal -->
	<div class="mb-6 bg-neutral-50 dark:bg-neutral-800/50 border border-dashed border-neutral-300 dark:border-neutral-600 rounded-lg p-5">
		<div class="flex items-center gap-4">
			<div class="flex-shrink-0 w-12 h-12 flex items-center justify-center rounded-full bg-neutral-100 dark:bg-neutral-700">
				<svg class="w-6 h-6 text-neutral-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
				</svg>
			</div>
			<div class="flex-1 min-w-0">
				<h3 class="text-sm font-semibold text-neutral-900 dark:text-white">Set your company goal</h3>
				<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
					Define your north star to align meetings and actions with your strategic direction.
				</p>
			</div>
			<a
				href="/context/overview"
				class="flex-shrink-0 inline-flex items-center px-3 py-1.5 text-sm font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 rounded-lg hover:bg-brand-100 dark:hover:bg-brand-900/30 transition-colors"
			>
				<svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
				</svg>
				Set goal
			</a>
		</div>
	</div>
{/if}
