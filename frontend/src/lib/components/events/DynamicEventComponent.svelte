<script lang="ts">
	/**
	 * DynamicEventComponent - Reusable wrapper for dynamic event component loading
	 *
	 * Handles the repeated pattern of:
	 * {#await getComponentForEvent(...)}
	 *   <EventCardSkeleton />
	 * {:then Component}
	 *   {#if Component}
	 *     <Component {event} />
	 *   {:else}
	 *     <GenericEvent {event} />
	 *   {/if}
	 * {:catch}
	 *   <GenericEvent {event} />
	 * {/await}
	 *
	 * Usage:
	 * <DynamicEventComponent {event} />
	 * <DynamicEventComponent {event} eventType="custom_type" />
	 * <DynamicEventComponent {event} skeletonProps={{ lines: 5, hasAvatar: false }} />
	 */
	import type { SSEEvent } from '$lib/api/sse-events';
	import GenericEvent from './GenericEvent.svelte';
	import EventCardSkeleton from '$lib/components/ui/skeletons/EventCardSkeleton.svelte';
	import { SvelteMap } from 'svelte/reactivity';

	interface Props {
		/** The SSE event to render */
		event: SSEEvent;
		/** Optional override for event type (defaults to event.event_type) */
		eventType?: string;
		/** Optional props to pass to EventCardSkeleton during loading */
		skeletonProps?: {
			hasAvatar?: boolean;
			hasTitle?: boolean;
			hasContent?: boolean;
			lines?: number;
		};
		/** Optional additional props to pass to the loaded component */
		componentProps?: Record<string, any>;
	}

	let {
		event,
		eventType = event.event_type,
		skeletonProps = {},
		componentProps = {}
	}: Props = $props();

	// Type for dynamically loaded components
	type SvelteComponent = any;

	// Map event types to dynamic component loaders
	const componentLoaders: Record<string, () => Promise<{ default: SvelteComponent }>> = {
		'decomposition_complete': () => import('./DecompositionComplete.svelte'),
		'contribution': () => import('./ExpertPerspectiveCard.svelte'),
		'facilitator_decision': () => import('./FacilitatorDecision.svelte'),
		'moderator_intervention': () => import('./ModeratorIntervention.svelte'),
		'convergence': () => import('./ConvergenceCheck.svelte'),
		'voting_complete': () => import('./RecommendationResults.svelte'),
		'persona_vote': () => import('./PersonaRecommendation.svelte'),
		'meta_synthesis_complete': () => import('./ActionPlan.svelte'),
		'synthesis_complete': () => import('./SynthesisComplete.svelte'),
		'subproblem_complete': () => import('./SubProblemProgress.svelte'),
		'phase_cost_breakdown': () => import('./PhaseTable.svelte'),
		'complete': () => import('./DeliberationComplete.svelte'),
		'error': () => import('./ErrorEvent.svelte'),
		'meeting_failed': () => import('./MeetingFailedEvent.svelte'),
		'expert_panel': () => import('./ExpertPanel.svelte'),
	};

	// Cache loaded components to avoid re-importing (LRU with bounded size)
	const MAX_CACHED_COMPONENTS = 20;
	const componentCache = new SvelteMap<string, SvelteComponent>();

	/**
	 * Get component for event type with dynamic loading.
	 * Returns GenericEvent as fallback for unknown types.
	 *
	 * Uses LRU (Least Recently Used) cache eviction strategy.
	 */
	async function getComponentForEvent(type: string): Promise<SvelteComponent> {
		// Check cache first (LRU: move to end)
		if (componentCache.has(type)) {
			const component = componentCache.get(type)!;
			// Move to end (most recently used) for LRU eviction
			componentCache.delete(type);
			componentCache.set(type, component);
			return component;
		}

		// Load component
		const loader = componentLoaders[type];
		if (!loader) {
			console.debug(`Unknown event type: ${type}, using GenericEvent`);
			return GenericEvent;
		}

		try {
			const module = await loader();
			const component = module.default;

			// Enforce max size (evict oldest/least recently used)
			if (componentCache.size >= MAX_CACHED_COMPONENTS) {
				const firstKey = componentCache.keys().next().value;
				if (firstKey) {
					componentCache.delete(firstKey);
					console.debug(`LRU cache eviction: removed ${firstKey} component`);
				}
			}

			// Cache for future use
			componentCache.set(type, component);

			return component;
		} catch (error) {
			console.error(`Failed to load component for ${type}:`, error);
			return GenericEvent;
		}
	}

	// Load the component
	const componentPromise = getComponentForEvent(eventType);
</script>

{#await componentPromise}
	<!-- Loading state: show skeleton -->
	<EventCardSkeleton {...skeletonProps} />
{:then Component}
	<!-- Success: render the component -->
	{#if Component}
		<Component {event} {...componentProps} />
	{:else}
		<!-- Fallback if component is null/undefined -->
		<GenericEvent {event} />
	{/if}
{:catch error}
	<!-- Error state: show error message + fallback -->
	<div class="bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-700 rounded-lg p-4 mb-2">
		<p class="text-sm text-warning-800 dark:text-warning-200">
			Failed to load component for event type: <code>{eventType}</code>
		</p>
	</div>
	<GenericEvent {event} />
{/await}
