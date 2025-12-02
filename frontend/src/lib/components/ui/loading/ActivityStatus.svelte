<script lang="ts">
	/**
	 * ActivityStatus - Unified Loading Status Component
	 *
	 * Shows contextual loading status with optional:
	 * - Elapsed time counter (for 10+ second operations)
	 * - Phase indicator ("Round 2 of 4")
	 * - Three visual variants: inline, banner, card
	 *
	 * Based on UX research: users need to know WHAT is happening, not just THAT loading.
	 */
	import { onMount, onDestroy } from 'svelte';
	import Spinner from '../Spinner.svelte';
	import LoadingDots from './LoadingDots.svelte';

	interface Props {
		message: string;
		phase?: string | null;
		showElapsedTime?: boolean;
		variant?: 'inline' | 'banner' | 'card';
		startTime?: Date | null;
		showDots?: boolean;
		class?: string;
	}

	let {
		message,
		phase = null,
		showElapsedTime = false,
		variant = 'inline',
		startTime = null,
		showDots = false,
		class: className = ''
	}: Props = $props();

	let mountTime = $state<number>(Date.now());
	let elapsedSeconds = $state<number>(0);
	let timer: ReturnType<typeof setInterval> | null = null;

	onMount(() => {
		mountTime = startTime ? startTime.getTime() : Date.now();
		if (showElapsedTime) {
			timer = setInterval(() => {
				elapsedSeconds = Math.floor((Date.now() - mountTime) / 1000);
			}, 1000);
		}
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

	const variantClasses = {
		inline: 'inline-flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400',
		banner: 'sticky top-4 z-50 bg-gradient-to-r from-brand-600 to-accent-600 text-white px-6 py-4 rounded-lg shadow-lg mx-4 mb-4 animate-fade-in',
		card: 'flex flex-col items-center justify-center gap-4 p-8 text-center',
	};
</script>

{#if variant === 'inline'}
	<div
		class="{variantClasses.inline} {className}"
		role="status"
		aria-live="polite"
	>
		{#if showDots}
			<LoadingDots size="sm" variant="thinking" />
		{:else}
			<Spinner size="sm" variant="brand" ariaLabel={message} />
		{/if}
		<span>{message}</span>
		{#if phase}
			<span class="text-neutral-400 dark:text-neutral-500">({phase})</span>
		{/if}
		{#if showElapsedTime && elapsedSeconds > 0}
			<span class="text-neutral-400 dark:text-neutral-500">{formatDuration(elapsedSeconds)}</span>
		{/if}
	</div>

{:else if variant === 'banner'}
	<div
		class="{variantClasses.banner} {className}"
		role="status"
		aria-live="polite"
	>
		<div class="flex items-center gap-3">
			<div class="flex-shrink-0">
				<div class="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></div>
			</div>
			<div class="flex-1 min-w-0">
				<div class="font-semibold text-lg truncate">{message}</div>
				{#if phase || showElapsedTime}
					<div class="text-sm opacity-90 flex items-center gap-2">
						{#if showElapsedTime}
							<span>{formatDuration(elapsedSeconds)}</span>
						{/if}
						{#if phase}
							<span class="text-xs opacity-75">{phase}</span>
						{/if}
					</div>
				{/if}
			</div>
			<div class="flex-shrink-0">
				<div class="text-xs opacity-75 bg-white/20 px-3 py-1 rounded-full font-medium">
					Working...
				</div>
			</div>
		</div>
	</div>

{:else if variant === 'card'}
	<div
		class="{variantClasses.card} {className}"
		role="status"
		aria-live="polite"
	>
		{#if showDots}
			<LoadingDots size="lg" variant="thinking" />
		{:else}
			<Spinner size="xl" variant="brand" ariaLabel={message} />
		{/if}
		<div class="space-y-1">
			<p class="text-lg font-medium text-neutral-900 dark:text-neutral-100">{message}</p>
			{#if phase}
				<p class="text-sm text-neutral-500 dark:text-neutral-400">{phase}</p>
			{/if}
			{#if showElapsedTime && elapsedSeconds > 0}
				<p class="text-sm text-neutral-400 dark:text-neutral-500">
					{formatDuration(elapsedSeconds)}
				</p>
			{/if}
		</div>
	</div>
{/if}

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

	@media (prefers-reduced-motion: reduce) {
		.animate-fade-in {
			animation: none;
		}
	}
</style>
