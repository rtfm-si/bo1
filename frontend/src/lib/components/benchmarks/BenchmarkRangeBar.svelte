<script lang="ts">
	/**
	 * BenchmarkRangeBar - Visual comparison of user value vs industry range
	 *
	 * Shows a horizontal bar representing the industry range (P25-P75)
	 * with a marker showing where the user's value falls.
	 */

	interface Props {
		/** Bottom 25% value (P25) */
		rangeMin: number;
		/** Typical/median value (P50) */
		rangeMedian: number;
		/** Top 25% value (P75) */
		rangeMax: number;
		/** User's current value (undefined = not set) */
		userValue?: number | null;
		/** Unit for display (%, $, etc.) */
		unit?: string;
		/** Performance status for color coding */
		status?: 'top_performer' | 'above_average' | 'average' | 'below_average' | 'no_data';
		/** Whether higher values are better (true) or lower values are better (false) */
		higherIsBetter?: boolean;
	}

	let {
		rangeMin,
		rangeMedian,
		rangeMax,
		userValue = null,
		unit = '',
		status = 'no_data',
		higherIsBetter = true
	}: Props = $props();

	// Calculate marker position as percentage (0-100)
	// Extends 10% beyond range on each side to show values outside P25-P75
	const extendedMin = $derived(rangeMin - (rangeMax - rangeMin) * 0.2);
	const extendedMax = $derived(rangeMax + (rangeMax - rangeMin) * 0.2);

	const markerPosition = $derived.by(() => {
		if (userValue === null || userValue === undefined) return null;

		// Map user value to 0-100% position
		const range = extendedMax - extendedMin;
		if (range === 0) return 50;

		const pos = ((userValue - extendedMin) / range) * 100;
		// Clamp to 2-98% so marker stays visible at edges
		return Math.max(2, Math.min(98, pos));
	});

	// Calculate range positions within the extended range
	const rangeStartPos = $derived(((rangeMin - extendedMin) / (extendedMax - extendedMin)) * 100);
	const rangeEndPos = $derived(((rangeMax - extendedMin) / (extendedMax - extendedMin)) * 100);
	const medianPos = $derived(((rangeMedian - extendedMin) / (extendedMax - extendedMin)) * 100);

	// Get marker color based on status
	function getMarkerColor(s: string): string {
		switch (s) {
			case 'top_performer':
				return 'bg-green-500';
			case 'above_average':
				return 'bg-emerald-500';
			case 'average':
				return 'bg-yellow-500';
			case 'below_average':
				return 'bg-red-500';
			default:
				return 'bg-slate-400';
		}
	}

	// Format value with unit
	function formatValue(val: number): string {
		if (unit === '%') return `${val}%`;
		if (unit) return `${val} ${unit}`;
		return String(val);
	}
</script>

<div class="benchmark-range-bar">
	<!-- Range bar container -->
	<div class="relative h-6 bg-slate-100 dark:bg-slate-700 rounded-full overflow-visible">
		<!-- Industry range (P25-P75) highlighted area -->
		<div
			class="absolute top-0 h-full bg-slate-200 dark:bg-slate-600 rounded-full"
			style="left: {rangeStartPos}%; width: {rangeEndPos - rangeStartPos}%;"
		></div>

		<!-- Median marker -->
		<div
			class="absolute top-0 h-full w-0.5 bg-slate-400 dark:bg-slate-500"
			style="left: {medianPos}%;"
			title="Typical: {formatValue(rangeMedian)}"
		></div>

		<!-- User value marker -->
		{#if markerPosition !== null}
			<div
				class="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 border-white dark:border-slate-800 shadow-md transition-all duration-300 {getMarkerColor(status)}"
				style="left: calc({markerPosition}% - 8px);"
				title="Your value: {formatValue(userValue!)}"
			>
				<!-- Pulse animation for emphasis -->
				<span class="absolute inset-0 rounded-full {getMarkerColor(status)} opacity-30 animate-ping"></span>
			</div>
		{/if}
	</div>

	<!-- Labels -->
	<div class="flex justify-between mt-1.5 text-xs text-slate-500 dark:text-slate-400">
		<div class="flex flex-col items-start">
			<span>Bottom 25%</span>
			<span class="font-medium text-slate-600 dark:text-slate-300">{formatValue(rangeMin)}</span>
		</div>
		<div class="flex flex-col items-center">
			<span>Typical</span>
			<span class="font-medium text-slate-600 dark:text-slate-300">{formatValue(rangeMedian)}</span>
		</div>
		<div class="flex flex-col items-end">
			<span>Top 25%</span>
			<span class="font-medium text-slate-600 dark:text-slate-300">{formatValue(rangeMax)}</span>
		</div>
	</div>

	<!-- User value callout (if set) -->
	{#if userValue !== null && userValue !== undefined}
		<div class="mt-2 flex items-center justify-center gap-2">
			<span class="w-3 h-3 rounded-full {getMarkerColor(status)}"></span>
			<span class="text-sm font-medium text-slate-700 dark:text-slate-200">
				Your value: {formatValue(userValue)}
			</span>
		</div>
	{/if}
</div>

<style>
	.benchmark-range-bar {
		min-width: 200px;
	}
</style>
