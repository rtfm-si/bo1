<script lang="ts">
	/**
	 * ConvergenceCheck Event Component
	 * Displays convergence status and progress towards consensus with color-coding
	 */
	import type { ConvergenceEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { fade } from 'svelte/transition';

	interface Props {
		event: ConvergenceEvent;
	}

	let { event }: Props = $props();

	// Default threshold to 0.85 if not provided
	const threshold = $derived(event.data.threshold ?? 0.85);
	const score = $derived(event.data.score);
	const percentage = $derived(Math.round((score / threshold) * 100));
	const progressWidth = $derived(Math.min(percentage, 100));

	// Color coding based on score
	function getProgressColor(score: number, threshold: number): string {
		const ratio = score / threshold;
		if (ratio >= 0.9) return 'bg-green-500 dark:bg-green-600';
		if (ratio >= 0.7) return 'bg-yellow-500 dark:bg-yellow-600';
		if (ratio >= 0.4) return 'bg-orange-500 dark:bg-orange-600';
		return 'bg-red-500 dark:bg-red-600';
	}

	function getProgressTextColor(score: number, threshold: number): string {
		const ratio = score / threshold;
		if (ratio >= 0.9) return 'text-green-700 dark:text-green-300';
		if (ratio >= 0.7) return 'text-yellow-700 dark:text-yellow-300';
		if (ratio >= 0.4) return 'text-orange-700 dark:text-orange-300';
		return 'text-red-700 dark:text-red-300';
	}

	function getStatusMessage(score: number, threshold: number): string {
		const ratio = score / threshold;
		if (ratio >= 1.0) return 'Strong consensus achieved';
		if (ratio >= 0.9) return 'Nearly converged';
		if (ratio >= 0.7) return 'Good progress';
		if (ratio >= 0.4) return 'Building consensus';
		return 'Early discussion';
	}

	const progressColor = $derived(getProgressColor(score, threshold));
	const textColor = $derived(getProgressTextColor(score, threshold));
	const statusMessage = $derived(getStatusMessage(score, threshold));
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

	<!-- Progress Bar with Color Coding -->
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
		<div class="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-3 overflow-hidden">
			<div
				class="{progressColor} h-full transition-all duration-700 ease-out rounded-full"
				style="width: {progressWidth}%"
				transition:fade
			></div>
		</div>
		<div class="flex items-center justify-between text-xs">
			<span class="{textColor} font-medium">
				{percentage}% of threshold
			</span>
			{#if event.data.converged}
				<span class="text-green-600 dark:text-green-400 font-semibold flex items-center gap-1">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					Converged
				</span>
			{/if}
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
