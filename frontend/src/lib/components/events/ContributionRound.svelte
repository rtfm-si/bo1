<script lang="ts">
	import { fade } from 'svelte/transition';
	import DynamicEventComponent from './DynamicEventComponent.svelte';
	import { LoadingDots } from '$lib/components/ui/loading';
	import type { SSEEvent, ContributionEvent } from '$lib/api/sse-events';

	interface Props {
		roundNumber: number;
		events: SSEEvent[];
		visibleCount: number;
		viewMode?: 'simple' | 'full';
		showFullTranscripts?: boolean;
		cardViewModes?: Map<string, 'simple' | 'full'>;
		onToggleCardViewMode?: (cardId: string) => void;
		thinkingMessages?: ((name: string) => string)[];
	}

	let {
		roundNumber,
		events,
		visibleCount,
		viewMode = 'simple',
		showFullTranscripts = false,
		cardViewModes = new Map(),
		onToggleCardViewMode,
		thinkingMessages = [
			(name: string) => `${name} is thinking...`,
			(name: string) => `${name} is formulating a response...`,
			(name: string) => `${name} wants to contribute...`,
			(name: string) => `${name} is considering the discussion...`,
			(name: string) => `${name} is preparing insights...`,
		]
	}: Props = $props();

	// Calculate visible contributions
	const visibleContributions = $derived(events.slice(0, visibleCount));

	// Check if there are more contributions to reveal
	const hasMoreToReveal = $derived(visibleCount < events.length);

	// Get the next expert's name for thinking indicator
	const nextExpert = $derived.by(() => {
		if (!hasMoreToReveal) return null;
		const nextContrib = events[visibleCount] as ContributionEvent | undefined;
		return nextContrib?.data?.persona_name || null;
	});

	// Get effective view mode for a card (card override or global)
	function getCardViewMode(cardId: string): 'simple' | 'full' {
		return cardViewModes.get(cardId) ?? viewMode;
	}

	// Get thinking message based on index
	function getThinkingMessage(name: string, index: number): string {
		const msgFn = thinkingMessages[index % thinkingMessages.length];
		return msgFn(name);
	}
</script>

<div class="space-y-3" transition:fade={{ duration: 300, delay: 50 }}>
	<h3 class="text-sm font-semibold text-neutral-700 dark:text-neutral-300 flex items-center gap-2">
		<span>Round {roundNumber} Contributions</span>
	</h3>

	{#each visibleContributions as contrib, index (index)}
		{@const contribEvent = contrib as ContributionEvent}
		{@const cardId = `${contribEvent.data.persona_code}-${contribEvent.data.round}`}
		<DynamicEventComponent
			event={contribEvent}
			eventType="contribution"
			skeletonProps={{ hasAvatar: true }}
			componentProps={{
				viewMode: getCardViewMode(cardId),
				showFull: showFullTranscripts,
				onToggle: onToggleCardViewMode ? () => onToggleCardViewMode(cardId) : undefined
			}}
		/>
	{/each}

	<!-- Thinking indicator when more contributions are pending -->
	{#if hasMoreToReveal && nextExpert}
		<div class="flex items-center gap-2 py-2 px-3" transition:fade={{ duration: 200 }}>
			<LoadingDots size="sm" variant="thinking" />
			<span class="text-sm text-neutral-500 dark:text-neutral-400 italic">
				{getThinkingMessage(nextExpert, visibleCount)}
			</span>
		</div>
	{/if}
</div>
