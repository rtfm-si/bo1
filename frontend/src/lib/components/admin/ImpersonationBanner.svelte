<script lang="ts">
	/**
	 * ImpersonationBanner - Fixed banner shown when admin is impersonating a user
	 *
	 * Features:
	 * - Shows target user email and remaining time
	 * - Different colors for read-only (blue) vs write mode (amber)
	 * - End Session button
	 * - Auto-refreshes remaining time every second
	 */

	import { onMount, onDestroy } from 'svelte';
	import { adminApi, type ImpersonationSessionResponse } from '$lib/api/admin';
	import BoButton from '$lib/components/ui/BoButton.svelte';

	// Props
	interface Props {
		session: ImpersonationSessionResponse;
		onEnd?: () => void;
	}

	let { session, onEnd }: Props = $props();

	// State
	let remainingSeconds = $state(0);
	let isEnding = $state(false);

	// Sync remaining seconds when session prop changes
	// Use setTimeout(0) to defer mutation outside reactive cycle (queueMicrotask is not enough)
	$effect(() => {
		const newValue = session.remaining_seconds;
		setTimeout(() => { remainingSeconds = newValue; }, 0);
	});
	let intervalId: ReturnType<typeof setInterval> | null = null;

	// Computed
	const formattedTime = $derived(() => {
		const minutes = Math.floor(remainingSeconds / 60);
		const seconds = remainingSeconds % 60;
		return `${minutes}:${seconds.toString().padStart(2, '0')}`;
	});

	const isWriteMode = $derived(session.is_write_mode);
	const targetEmail = $derived(session.target_email || session.target_user_id);

	// Update countdown
	onMount(() => {
		intervalId = setInterval(() => {
			if (remainingSeconds > 0) {
				remainingSeconds--;
			} else {
				// Session expired, trigger end
				onEnd?.();
			}
		}, 1000);
	});

	onDestroy(() => {
		if (intervalId) {
			clearInterval(intervalId);
		}
	});

	async function handleEndSession() {
		isEnding = true;
		try {
			await adminApi.endImpersonation();
			onEnd?.();
		} catch (error) {
			console.error('Failed to end impersonation:', error);
		} finally {
			isEnding = false;
		}
	}
</script>

<div
	class="fixed top-0 left-0 right-0 z-50 px-4 py-2 shadow-md {isWriteMode
		? 'bg-warning-500 text-warning-50'
		: 'bg-info-500 text-info-50'}"
	role="alert"
	aria-live="polite"
>
	<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 flex items-center justify-between gap-4">
		<!-- Left: Icon and message -->
		<div class="flex items-center gap-3">
			<!-- Eye icon -->
			<svg
				class="w-5 h-5 flex-shrink-0"
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
				/>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
				/>
			</svg>

			<!-- Message -->
			<span class="text-sm font-medium">
				Viewing as
				<span class="font-bold">{targetEmail}</span>
				{#if isWriteMode}
					<span class="px-1.5 py-0.5 ml-1 text-xs font-semibold rounded bg-white/20">
						Write Mode
					</span>
				{:else}
					<span class="px-1.5 py-0.5 ml-1 text-xs font-semibold rounded bg-white/20">
						Read Only
					</span>
				{/if}
			</span>
		</div>

		<!-- Right: Timer and end button -->
		<div class="flex items-center gap-3">
			<!-- Timer -->
			<span class="text-sm tabular-nums">
				{formattedTime()}
			</span>

			<!-- End Session button -->
			<BoButton
				variant="outline"
				size="sm"
				onclick={handleEndSession}
				loading={isEnding}
				class="!bg-white/20 !border-white/40 !text-white hover:!bg-white/30"
			>
				End Session
			</BoButton>
		</div>
	</div>
</div>

<!-- Spacer to prevent content from being hidden behind fixed banner -->
<div class="h-11"></div>
