<script lang="ts">
	/**
	 * DeliberationComplete Event Component
	 * Displays completion summary with metrics
	 */
	import { fade } from 'svelte/transition';
	import type { CompleteEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: CompleteEvent;
	}

	let { event }: Props = $props();

	let showConfetti = $state(true);

	// Auto-hide confetti after 3 seconds
	$effect(() => {
		const timer = setTimeout(() => {
			showConfetti = false;
		}, 3000);
		return () => clearTimeout(timer);
	});

	const formatDuration = (seconds: number | undefined): string => {
		if (seconds === undefined || isNaN(seconds)) {
			return 'N/A';
		}
		const minutes = Math.floor(seconds / 60);
		const remainingSeconds = Math.round(seconds % 60);
		if (minutes >= 60) {
			const hours = Math.floor(minutes / 60);
			const remainingMinutes = minutes % 60;
			return `${hours}h ${remainingMinutes}m`;
		}
		return `${minutes}m ${remainingSeconds}s`;
	};

	const formatCost = (cost: number): string => {
		return `$${cost.toFixed(4)}`;
	};

	const formatTokens = (tokens: number | undefined): string => {
		if (!tokens) return '0';
		if (tokens >= 1000000) {
			return `${(tokens / 1000000).toFixed(2)}M`;
		}
		if (tokens >= 1000) {
			return `${(tokens / 1000).toFixed(1)}K`;
		}
		return tokens.toString();
	};

	const stopReasonLabels: Record<string, string> = {
		consensus: 'Consensus Reached',
		max_rounds: 'Maximum Rounds',
		user_killed: 'Stopped by User',
		timeout: 'Timeout',
		error: 'Error Occurred',
	};
</script>

<div class="space-y-4">
	<div
		class="bg-gradient-to-br from-success-50 via-brand-50 to-accent-50 dark:from-success-900/20 dark:via-brand-900/20 dark:to-accent-900/20 border-2 border-success-300 dark:border-success-600 rounded-xl p-6 relative overflow-hidden"
	>
		<!-- Confetti Animation -->
		{#if showConfetti}
			<div
				class="absolute inset-0 pointer-events-none overflow-hidden"
				transition:fade={{ duration: 500 }}
			>
				<div class="confetti">🎉</div>
				<div class="confetti" style="animation-delay: 0.2s">🎊</div>
				<div class="confetti" style="animation-delay: 0.4s">✨</div>
				<div class="confetti" style="animation-delay: 0.1s; left: 35%">🎉</div>
				<div class="confetti" style="animation-delay: 0.3s; left: 65%">✨</div>
			</div>
		{/if}

		<!-- Header -->
		<div class="flex items-center justify-between mb-4">
			<div class="flex items-center gap-3">
				<div
					class="flex-shrink-0 w-14 h-14 bg-success-500 dark:bg-success-600 text-white rounded-full flex items-center justify-center"
				>
					<svg
						class="w-8 h-8"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
				</div>
				<div>
					<h2 class="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
						Deliberation Complete
					</h2>
					<p class="text-sm text-neutral-600 dark:text-neutral-400">
						{stopReasonLabels[event.data.stop_reason] || event.data.stop_reason}
					</p>
				</div>
			</div>
		</div>

		<!-- Metrics Grid -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
			<!-- Total Cost -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="text-xs text-neutral-600 dark:text-neutral-400 uppercase mb-1">
					Total Cost
				</div>
				<div class="text-xl font-bold text-brand-600 dark:text-brand-400">
					{formatCost(event.data.total_cost)}
				</div>
			</div>

			<!-- Duration -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="text-xs text-neutral-600 dark:text-neutral-400 uppercase mb-1">
					Duration
				</div>
				<div class="text-xl font-bold text-neutral-900 dark:text-neutral-100">
					{formatDuration(event.data.duration_seconds)}
				</div>
			</div>

			<!-- Rounds -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="text-xs text-neutral-600 dark:text-neutral-400 uppercase mb-1">
					Rounds
				</div>
				<div class="text-xl font-bold text-neutral-900 dark:text-neutral-100">
					{event.data.total_rounds}
				</div>
			</div>

			<!-- Contributions -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="text-xs text-neutral-600 dark:text-neutral-400 uppercase mb-1">
					Contributions
				</div>
				<div class="text-xl font-bold text-neutral-900 dark:text-neutral-100">
					{event.data.total_contributions}
				</div>
			</div>
		</div>

		<!-- Additional Info -->
		<div class="mt-4 flex items-center justify-between text-sm">
			<Badge variant="info">
				{formatTokens(event.data.total_tokens)} tokens
			</Badge>
			<span class="text-neutral-600 dark:text-neutral-400 font-mono">
				Session: {event.data.session_id}
			</span>
		</div>
	</div>
</div>

<style>
	.confetti {
		position: absolute;
		top: -50px;
		font-size: 2rem;
		animation: fall 3s ease-out forwards;
	}

	.confetti:nth-child(1) {
		left: 20%;
	}
	.confetti:nth-child(2) {
		left: 50%;
	}
	.confetti:nth-child(3) {
		left: 80%;
	}
	.confetti:nth-child(4) {
		left: 35%;
	}
	.confetti:nth-child(5) {
		left: 65%;
	}

	@keyframes fall {
		to {
			transform: translateY(600px) rotate(360deg);
			opacity: 0;
		}
	}
</style>
