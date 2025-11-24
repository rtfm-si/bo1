<script lang="ts">
	/**
	 * MeetingQualityBar Component - Displays meeting completeness index (M_r)
	 * Shows composite quality metric with color coding and tooltips
	 *
	 * Quality Levels:
	 * - Red (<50%): Low quality, needs more exploration
	 * - Yellow (50-70%): Moderate quality
	 * - Green (>70%): High quality, can end
	 */

	import Tooltip from './Tooltip.svelte';

	// Props
	interface Props {
		completenessIndex: number; // 0-1 (will be shown as percentage)
		explorationScore?: number; // 0-1
		convergenceScore?: number; // 0-1
		focusScore?: number; // 0-1
		noveltyScore?: number; // 0-1
		missingAspects?: string[];
		size?: 'sm' | 'md' | 'lg';
		showBreakdown?: boolean;
	}

	let {
		completenessIndex,
		explorationScore,
		convergenceScore,
		focusScore,
		noveltyScore,
		missingAspects = [],
		size = 'md',
		showBreakdown = true
	}: Props = $props();

	// Convert to percentage
	const percentage = $derived(Math.round(completenessIndex * 100));

	// Determine quality level and color
	const qualityLevel = $derived(
		percentage < 50 ? 'low' : percentage < 70 ? 'moderate' : 'high'
	);

	const colorClasses = $derived({
		low: 'bg-error-600 dark:bg-error-500',
		moderate: 'bg-warning-600 dark:bg-warning-500',
		high: 'bg-success-600 dark:bg-success-500'
	}[qualityLevel]);

	const textColorClasses = $derived({
		low: 'text-error-600 dark:text-error-400',
		moderate: 'text-warning-600 dark:text-warning-400',
		high: 'text-success-600 dark:text-success-400'
	}[qualityLevel]);

	// Size styles
	const sizes = {
		sm: 'h-2',
		md: 'h-3',
		lg: 'h-4'
	};

	// Helper to format score
	function formatScore(score: number | undefined): string {
		return score !== undefined ? `${Math.round(score * 100)}%` : 'N/A';
	}

	// Quality description
	const qualityDescription = $derived(
		qualityLevel === 'low'
			? 'Low quality - needs more exploration'
			: qualityLevel === 'moderate'
				? 'Moderate quality'
				: 'High quality - ready to decide'
	);
</script>

<div class="w-full space-y-2">
	<!-- Quality Label -->
	<div class="flex items-center justify-between">
		<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">
			Meeting Quality
		</span>
		<Tooltip text={qualityDescription}>
			<span class="text-sm font-bold {textColorClasses}">
				{percentage}%
			</span>
		</Tooltip>
	</div>

	<!-- Progress Bar -->
	<div class="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden {sizes[size]}">
		<div
			class="h-full rounded-full transition-all duration-500 ease-smooth {colorClasses}"
			style="width: {percentage}%"
			role="progressbar"
			aria-valuenow={percentage}
			aria-valuemin={0}
			aria-valuemax={100}
			aria-label="Meeting quality: {percentage}%"
		></div>
	</div>

	<!-- Metric Breakdown (optional) -->
	{#if showBreakdown && (explorationScore !== undefined || convergenceScore !== undefined)}
		<div class="grid grid-cols-2 gap-2 text-xs text-neutral-600 dark:text-neutral-400">
			{#if explorationScore !== undefined}
				<Tooltip text="Coverage of 8 critical decision aspects">
					<div class="flex justify-between">
						<span>Exploration:</span>
						<span class="font-medium">{formatScore(explorationScore)}</span>
					</div>
				</Tooltip>
			{/if}
			{#if convergenceScore !== undefined}
				<Tooltip text="Agreement and consensus level">
					<div class="flex justify-between">
						<span>Convergence:</span>
						<span class="font-medium">{formatScore(convergenceScore)}</span>
					</div>
				</Tooltip>
			{/if}
			{#if focusScore !== undefined}
				<Tooltip text="On-topic discussion ratio">
					<div class="flex justify-between">
						<span>Focus:</span>
						<span class="font-medium">{formatScore(focusScore)}</span>
					</div>
				</Tooltip>
			{/if}
			{#if noveltyScore !== undefined}
				<Tooltip text="Uniqueness of recent contributions">
					<div class="flex justify-between">
						<span>Novelty:</span>
						<span class="font-medium">{formatScore(noveltyScore)}</span>
					</div>
				</Tooltip>
			{/if}
		</div>
	{/if}

	<!-- Missing Aspects Warning -->
	{#if missingAspects.length > 0}
		<div class="text-xs text-warning-600 dark:text-warning-400 space-y-1">
			<div class="font-medium">Missing aspects:</div>
			<ul class="list-disc list-inside pl-2">
				{#each missingAspects as aspect}
					<li>{aspect.replace(/_/g, ' ')}</li>
				{/each}
			</ul>
		</div>
	{/if}
</div>
