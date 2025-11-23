<script lang="ts">
	import { eventTokens } from '$lib/design/tokens';
	import type { SSEEvent, ConvergenceEvent } from '$lib/api/sse-events';

	interface Props {
		events: SSEEvent[];
	}

	let { events }: Props = $props();

	// Extract convergence data from events
	const convergenceData = $derived.by(() => {
		const convergenceEvents = events.filter(
			(e) => e.event_type === 'convergence'
		) as ConvergenceEvent[];

		if (convergenceEvents.length === 0) {
			return null;
		}

		const dataPoints = convergenceEvents
			.map((event, index) => ({
				id: `${event.timestamp}-${index}`, // Unique ID for keying
				round: event.data.round,
				score: event.data.score,
				converged: event.data.converged,
				threshold: event.data.threshold,
			}))
			.sort((a, b) => a.round - b.round); // Sort by round number ascending

		const maxScore = Math.max(...dataPoints.map((d) => d.score), 1.0);
		const convergenceAchieved = dataPoints.some((d) => d.converged);
		const convergenceRound = dataPoints.find((d) => d.converged)?.round;

		return {
			dataPoints,
			maxScore,
			convergenceAchieved,
			convergenceRound,
			threshold: dataPoints[0]?.threshold || 0.85,
		};
	});

	// Calculate SVG path for line chart
	const chartPath = $derived.by(() => {
		if (!convergenceData || convergenceData.dataPoints.length === 0) {
			return '';
		}

		const width = 300;
		const height = 150;
		const padding = 20;

		const dataPoints = convergenceData.dataPoints;
		const maxRound = Math.max(...dataPoints.map((d) => d.round));

		const points = dataPoints.map((point) => {
			const x = padding + ((point.round - 1) / (maxRound - 1 || 1)) * (width - 2 * padding);
			const y = height - padding - (point.score / convergenceData.maxScore) * (height - 2 * padding);
			return `${x},${y}`;
		});

		return `M ${points.join(' L ')}`;
	});

	// Calculate threshold line Y position
	const thresholdY = $derived.by(() => {
		if (!convergenceData) return 0;
		const height = 150;
		const padding = 20;
		return height - padding - (convergenceData.threshold / convergenceData.maxScore) * (height - 2 * padding);
	});
</script>

{#if convergenceData}
	<div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
		<!-- Header -->
		<div class="mb-4">
			<h3 class="text-sm font-semibold text-slate-900 dark:text-white">
				Convergence Tracking
			</h3>
			{#if convergenceData.convergenceAchieved}
				<p class="text-xs text-green-600 dark:text-green-400 mt-1">
					✓ Convergence achieved at round {convergenceData.convergenceRound}
				</p>
			{:else}
				<p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
					Tracking expert consensus formation
				</p>
			{/if}
		</div>

		<!-- Chart -->
		<div class="relative">
			<svg viewBox="0 0 300 150" class="w-full h-auto" role="img" aria-label="Convergence chart showing expert consensus over rounds">
				<!-- Background -->
				<rect x="0" y="0" width="300" height="150" fill="transparent" />

				<!-- Grid lines (light) -->
				<line x1="20" y1="20" x2="280" y2="20" stroke="currentColor" stroke-width="0.5" class="text-slate-200 dark:text-slate-700" />
				<line x1="20" y1="85" x2="280" y2="85" stroke="currentColor" stroke-width="0.5" class="text-slate-200 dark:text-slate-700" />
				<line x1="20" y1="130" x2="280" y2="130" stroke="currentColor" stroke-width="0.5" class="text-slate-200 dark:text-slate-700" />

				<!-- Threshold line (dashed) -->
				<line
					x1="20"
					y1={thresholdY}
					x2="280"
					y2={thresholdY}
					stroke={eventTokens.charts.convergence.threshold}
					stroke-width="2"
					stroke-dasharray="4 4"
					opacity="0.7"
				/>

				<!-- Area under curve -->
				{#if chartPath}
					<path
						d="{chartPath} L 280,130 L 20,130 Z"
						fill={eventTokens.charts.convergence.area}
						opacity="0.3"
					/>
				{/if}

				<!-- Main line -->
				{#if chartPath}
					<path
						d={chartPath}
						fill="none"
						stroke={eventTokens.charts.convergence.line}
						stroke-width="3"
						stroke-linecap="round"
						stroke-linejoin="round"
					/>
				{/if}

				<!-- Data points -->
				{#each convergenceData.dataPoints as point (point.id)}
					{@const maxRound = Math.max(...convergenceData.dataPoints.map((d) => d.round))}
					{@const x = 20 + ((point.round - 1) / (maxRound - 1 || 1)) * 260}
					{@const y = 150 - 20 - (point.score / convergenceData.maxScore) * 110}
					<circle
						cx={x}
						cy={y}
						r="4"
						fill={point.converged ? eventTokens.charts.progress.complete : eventTokens.charts.convergence.line}
						stroke="white"
						stroke-width="2"
					>
						<title>Round {point.round}: {(point.score * 100).toFixed(1)}%</title>
					</circle>
				{/each}

				<!-- Axes -->
				<line x1="20" y1="20" x2="20" y2="130" stroke="currentColor" stroke-width="1" class="text-slate-400 dark:text-slate-600" />
				<line x1="20" y1="130" x2="280" y2="130" stroke="currentColor" stroke-width="1" class="text-slate-400 dark:text-slate-600" />

				<!-- Y-axis labels -->
				<text x="15" y="25" text-anchor="end" font-size="10" class="fill-slate-500 dark:fill-slate-400">1.0</text>
				<text x="15" y="90" text-anchor="end" font-size="10" class="fill-slate-500 dark:fill-slate-400">0.5</text>
				<text x="15" y="135" text-anchor="end" font-size="10" class="fill-slate-500 dark:fill-slate-400">0.0</text>

				<!-- X-axis label -->
				<text x="150" y="148" text-anchor="middle" font-size="10" class="fill-slate-500 dark:fill-slate-400">Rounds</text>
			</svg>
		</div>

		<!-- Legend -->
		<div class="mt-3 flex items-center justify-center gap-4 text-xs">
			<div class="flex items-center gap-1.5">
				<div class="w-3 h-0.5" style="background-color: {eventTokens.charts.convergence.line}"></div>
				<span class="text-slate-600 dark:text-slate-400">Convergence Score</span>
			</div>
			<div class="flex items-center gap-1.5">
				<div class="w-3 h-0.5 border-t-2 border-dashed" style="border-color: {eventTokens.charts.convergence.threshold}"></div>
				<span class="text-slate-600 dark:text-slate-400">Threshold ({(convergenceData.threshold * 100).toFixed(0)}%)</span>
			</div>
		</div>
	</div>
{:else}
	<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
		<p class="text-xs text-slate-500 dark:text-slate-400 text-center">
			Convergence tracking will appear during deliberation
		</p>
	</div>
{/if}
