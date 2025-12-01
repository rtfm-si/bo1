<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	interface Props {
		currentPhase: string;
		elapsedSeconds?: number;
		estimatedDuration?: string;
	}

	let { currentPhase, elapsedSeconds = 0, estimatedDuration }: Props = $props();

	let startTime = $state(Date.now());
	let currentElapsed = $state(elapsedSeconds);
	let timer: ReturnType<typeof setInterval> | null = null;

	onMount(() => {
		startTime = Date.now();
		// Update elapsed time every second
		timer = setInterval(() => {
			currentElapsed = Math.floor((Date.now() - startTime) / 1000) + elapsedSeconds;
		}, 1000);
	});

	onDestroy(() => {
		if (timer) {
			clearInterval(timer);
		}
	});

	function formatDuration(seconds: number): string {
		if (seconds < 60) return `${seconds}s`;
		const minutes = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${minutes}m ${secs}s`;
	}
</script>

<div
	class="sticky top-4 z-50 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-4 rounded-lg shadow-lg mx-4 mb-4 animate-fade-in"
>
	<div class="flex items-center gap-3">
		<!-- Spinner -->
		<div class="flex-shrink-0">
			<div
				class="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"
			></div>
		</div>

		<!-- Phase and Duration -->
		<div class="flex-1 min-w-0">
			<div class="font-semibold text-lg truncate">{currentPhase}</div>
			<div class="text-sm opacity-90 flex items-center gap-2">
				<span>{formatDuration(currentElapsed)}</span>
				{#if estimatedDuration}
					<span class="text-xs opacity-75">• Est. {estimatedDuration}</span>
				{/if}
			</div>
		</div>

		<!-- Working Badge -->
		<div class="flex-shrink-0">
			<div class="text-xs opacity-75 bg-white/20 px-3 py-1 rounded-full font-medium">
				Working...
			</div>
		</div>
	</div>
</div>

<style>
	@keyframes fade-in {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.animate-fade-in {
		animation: fade-in 0.3s ease-out;
	}
</style>
