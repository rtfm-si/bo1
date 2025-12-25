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

	// Static imports for critical components (fallback if dynamic import fails)
	// These ensure essential components are bundled in the main chunk
	import DecompositionComplete from './DecompositionComplete.svelte';
	import SynthesisComplete from './SynthesisComplete.svelte';
	import ErrorEvent from './ErrorEvent.svelte';
	import MeetingFailedEvent from './MeetingFailedEvent.svelte';
	import ExpertPanel from './ExpertPanel.svelte';
	import ExpertPerspectiveCard from './ExpertPerspectiveCard.svelte';
	import PersonaSelection from './PersonaSelection.svelte';
	import ConvergenceCheck from './ConvergenceCheck.svelte';
	import FacilitatorDecision from './FacilitatorDecision.svelte';
	import ModeratorIntervention from './ModeratorIntervention.svelte';
	import RecommendationResults from './RecommendationResults.svelte';
	import PersonaRecommendation from './PersonaRecommendation.svelte';
	import ActionPlan from './ActionPlan.svelte';
	import SubProblemProgress from './SubProblemProgress.svelte';
	import DeliberationComplete from './DeliberationComplete.svelte';

	// Map of static fallback components for critical event types
	// All critical meeting event types are statically imported to avoid dynamic loading issues
	const staticFallbacks: Record<string, any> = {
		decomposition_complete: DecompositionComplete,
		synthesis_complete: SynthesisComplete,
		error: ErrorEvent,
		meeting_failed: MeetingFailedEvent,
		expert_panel: ExpertPanel,
		contribution: ExpertPerspectiveCard,
		persona_selected: PersonaSelection,
		convergence: ConvergenceCheck,
		facilitator_decision: FacilitatorDecision,
		moderator_intervention: ModeratorIntervention,
		voting_complete: RecommendationResults,
		persona_vote: PersonaRecommendation,
		meta_synthesis_complete: ActionPlan,
		subproblem_complete: SubProblemProgress,
		complete: DeliberationComplete
	};

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
		'subproblem_waiting': () => import('./SubProblemWaiting.svelte'),
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
	 * Priority:
	 * 1. Cache (already loaded)
	 * 2. Static fallbacks (bundled, instant, reliable)
	 * 3. Dynamic import (lazy-loaded)
	 * 4. GenericEvent (ultimate fallback)
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

		// For critical event types, prefer static fallbacks first (more reliable)
		// This avoids dynamic import failures in E2E/SSR/bundler edge cases
		const staticComponent = staticFallbacks[type];
		if (staticComponent) {
			componentCache.set(type, staticComponent);
			return staticComponent;
		}

		// Try dynamic import for non-critical components
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

	// Load the component - reactive to eventType changes
	const componentPromise = $derived(getComponentForEvent(eventType));
</script>

<!-- Static fallbacks render synchronously without async issues -->
{#if staticFallbacks[eventType]}
	{@const StaticComponent = staticFallbacks[eventType]}
	<StaticComponent {event} {...componentProps} />
{:else}
	<!-- Dynamic loading only for non-critical event types -->
	{#await componentPromise}
		<EventCardSkeleton {...skeletonProps} />
	{:then Component}
		{#if Component}
			<Component {event} {...componentProps} />
		{:else}
			<GenericEvent {event} />
		{/if}
	{:catch}
		<!-- Silent fallback - no error banner for unknown types -->
		<GenericEvent {event} />
	{/await}
{/if}
