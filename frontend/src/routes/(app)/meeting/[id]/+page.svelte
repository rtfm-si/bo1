<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { page } from '$app/stores';
	import { env } from '$env/dynamic/public';
	import { apiClient } from '$lib/api/client';
	import type { SSEEvent } from '$lib/api/sse-events';
	import { fade, scale } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import { SSEClient } from '$lib/utils/sse';
	import { CheckCircle, AlertCircle, Clock, Pause, Play, Square } from 'lucide-svelte';
	import { PHASE_PROGRESS_MAP } from '$lib/design/tokens';

	/**
	 * Dynamic component loading strategy:
	 *
	 * Event components are loaded on-demand using dynamic imports to reduce
	 * initial bundle size. Each component is cached after first load.
	 *
	 * Benefits:
	 * - 30-40% smaller initial bundle
	 * - Faster first paint
	 * - Components loaded only when needed
	 *
	 * Trade-offs:
	 * - Slight delay on first render of each component type (~10-50ms)
	 * - More complex than static imports
	 */

	// Import only GenericEvent statically (fallback for all unknown/error cases)
	import GenericEvent from '$lib/components/events/GenericEvent.svelte';

	// Type for dynamically loaded components (any Svelte component)
	type SvelteComponent = any;

	// Map event types to dynamic component loaders
	const componentLoaders: Record<string, () => Promise<{ default: SvelteComponent }>> = {
		'decomposition_complete': () => import('$lib/components/events/DecompositionComplete.svelte'),
		'contribution': () => import('$lib/components/events/ExpertPerspectiveCard.svelte'),
		'facilitator_decision': () => import('$lib/components/events/FacilitatorDecision.svelte'),
		'moderator_intervention': () => import('$lib/components/events/ModeratorIntervention.svelte'),
		'convergence': () => import('$lib/components/events/ConvergenceCheck.svelte'),
		'voting_complete': () => import('$lib/components/events/VotingResults.svelte'),
		'persona_vote': () => import('$lib/components/events/PersonaVote.svelte'),
		'meta_synthesis_complete': () => import('$lib/components/events/ActionPlan.svelte'),
		'synthesis_complete': () => import('$lib/components/events/SynthesisComplete.svelte'),
		'subproblem_complete': () => import('$lib/components/events/SubProblemProgress.svelte'),
		'phase_cost_breakdown': () => import('$lib/components/events/PhaseTable.svelte'),
		'complete': () => import('$lib/components/events/DeliberationComplete.svelte'),
		'error': () => import('$lib/components/events/ErrorEvent.svelte'),
		'expert_panel': () => import('$lib/components/events/ExpertPanel.svelte'),
	};

	// Cache loaded components to avoid re-importing (LRU with bounded size)
	const MAX_CACHED_COMPONENTS = 20;
	const componentCache = new Map<string, SvelteComponent>();

	/**
	 * Get component for event type with dynamic loading.
	 * Returns GenericEvent as fallback for unknown types.
	 *
	 * Uses LRU (Least Recently Used) cache eviction strategy to prevent unbounded memory growth.
	 * Cache is limited to MAX_CACHED_COMPONENTS (20) entries.
	 */
	async function getComponentForEvent(eventType: string): Promise<SvelteComponent> {
		// Check cache first (LRU: move to end)
		if (componentCache.has(eventType)) {
			const component = componentCache.get(eventType)!;
			// Move to end (most recently used) for LRU eviction
			componentCache.delete(eventType);
			componentCache.set(eventType, component);
			return component;
		}

		// Load component
		const loader = componentLoaders[eventType];
		if (!loader) {
			console.debug(`Unknown event type: ${eventType}, using GenericEvent`);
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
			componentCache.set(eventType, component);

			return component;
		} catch (error) {
			console.error(`Failed to load component for ${eventType}:`, error);
			return GenericEvent;
		}
	}

	// Import metrics components
	import {
		ProgressIndicator,
	} from '$lib/components/metrics';

	// Import UI components
	import {
		RelativeTimestamp,
		DecisionMetrics,
		Tabs,
		Button,
	} from '$lib/components/ui';
	import type { Tab } from '$lib/components/ui';
	import {
		EventCardSkeleton,
		ExpertPanelSkeleton,
		ContributionSkeleton,
		DashboardCardSkeleton
	} from '$lib/components/ui/skeletons';

	// Import utilities
	import { getEventPriority, type EventPriority } from '$lib/utils/event-humanization';

	// Import business logic modules
	import { createSessionStore, type SessionData } from './lib/sessionStore.svelte';
	import { groupEvents, indexEventsBySubProblem, shouldShowEvent, type EventGroup } from './lib/eventGrouping';
	import { buildSubProblemTabs, calculateSubProblemProgress, type SubProblemTab } from './lib/subProblemTabs';

	const sessionId: string = $page.params.id!; // SvelteKit guarantees this exists due to [id] route

	// Create session store
	const store = createSessionStore();

	// Reactive references to store values
	let session = $derived(store.session);
	let events = $derived(store.events);
	let isLoading = $derived(store.isLoading);
	let error = $derived(store.error);
	let autoScroll = $state(true); // Local UI state
	let retryCount = $derived(store.retryCount);
	let connectionStatus = $derived(store.connectionStatus);

	let sseClient: SSEClient | null = null;
	let maxRetries = 3;

	// Check URL for debug mode to show internal events
	const debugMode = $derived($page.url.searchParams.has('debug'));

	// Detect if synthesis is in progress
	const isSynthesizing = $derived(
		events.length > 0 &&
		events[events.length - 1].event_type === 'voting_complete' &&
		!events.some(e => e.event_type === 'synthesis_complete' || e.event_type === 'meta_synthesis_complete')
	);

	// Detect if voting is in progress
	const isVoting = $derived(
		events.length > 0 &&
		events[events.length - 1].event_type === 'voting_started' &&
		!events.some(e => e.event_type === 'voting_complete')
	);

	// Meta-synthesis event (for multi-sub-problem conclusions)
	const metaSynthesisEvent = $derived(
		events.find(e => e.event_type === 'meta_synthesis_complete')
	);

	// Synthesis complete event (for single-problem conclusions)
	const synthesisCompleteEvent = $derived(
		events.find(e => e.event_type === 'synthesis_complete')
	);

	// All sub-problem complete events (for individual conclusions)
	const subProblemCompleteEvents = $derived(
		events.filter(e => e.event_type === 'subproblem_complete')
	);

	// Whether to show the Conclusion tab (when meta-synthesis exists)
	const showConclusionTab = $derived(
		// Show tab if we have any synthesis content or meeting is complete
		metaSynthesisEvent !== undefined ||
		synthesisCompleteEvent !== undefined ||
		(subProblemCompleteEvents.length > 0 &&
		 subProblemCompleteEvents.some(e => e.data.synthesis)) ||
		session?.status === 'completed'
	);

	// Decomposition event (for displaying in Conclusion tab)
	const decompositionEvent = $derived(
		events.find(e => e.event_type === 'decomposition_complete')
	);

	// Detect if we're transitioning between sub-problems
	const isTransitioningSubProblem = $derived.by(() => {
		if (session?.status !== 'active') return false;

		// Check if we just finished a sub-problem but haven't started the next one yet
		const lastSubProblemComplete = events.findLast(e => e.event_type === 'subproblem_complete');
		const lastSubProblemStarted = events.findLast(e => e.event_type === 'subproblem_started');

		if (!lastSubProblemComplete) return false;

		// If we have a completed sub-problem but no subsequent started event, we're transitioning
		if (!lastSubProblemStarted) return true;

		// Compare timestamps to see which came last
		const completeTime = new Date(lastSubProblemComplete.timestamp).getTime();
		const startTime = new Date(lastSubProblemStarted.timestamp).getTime();

		return completeTime > startTime;
	});

	/**
	 * Performance optimization: Memoized sub-problem progress calculation
	 *
	 * Caches expensive array filtering to avoid recalculation on every render.
	 * Only recalculates when events.length changes.
	 */
	let subProblemProgressCache = $state<{ current: number; total: number } | null>(null);
	let lastEventCountForProgress = $state(0);

	$effect(() => {
		if (events.length !== lastEventCountForProgress) {
			subProblemProgressCache = calculateSubProblemProgress(events);
			lastEventCountForProgress = events.length;
		}
	});

	const subProblemProgress = $derived(subProblemProgressCache);

	// Heartbeat tracking for long operations
	let synthesisStartTime = $state<number | null>(null);
	let votingStartTime = $state<number | null>(null);
	let elapsedSeconds = $state(0);

	// Track synthesis timing
	$effect(() => {
		if (isSynthesizing) {
			synthesisStartTime = Date.now();
			const interval = setInterval(() => {
				if (synthesisStartTime) {
					elapsedSeconds = Math.floor((Date.now() - synthesisStartTime) / 1000);
				}
			}, 1000);
			return () => clearInterval(interval);
		} else {
			synthesisStartTime = null;
			elapsedSeconds = 0;
		}
	});

	// Track voting timing
	$effect(() => {
		if (isVoting) {
			votingStartTime = Date.now();
			const interval = setInterval(() => {
				if (votingStartTime) {
					elapsedSeconds = Math.floor((Date.now() - votingStartTime) / 1000);
				}
			}, 1000);
			return () => clearInterval(interval);
		} else {
			votingStartTime = null;
			if (!isSynthesizing) {
				elapsedSeconds = 0;
			}
		}
	});

	// Internal event types that should not be displayed in the UI
	const HIDDEN_EVENT_TYPES = new Set([
		'parallel_round_start',
		'node_start',           // Internal graph execution events
		'stream_connected',     // SSE connection confirmation
	]);

	// Helper function to add events safely with deduplication and filtering
	function addEvent(newEvent: SSEEvent) {
		// Filter out internal events that shouldn't be displayed
		if (HIDDEN_EVENT_TYPES.has(newEvent.event_type)) {
			return;
		}
		store.addEvent(newEvent);
	}

	// Helper functions for phase display
	// Removed emoji function - now using lucide icons

	function formatPhase(phase: string | null): string {
		if (!phase) return 'Initializing';
		return phase
			.split('_')
			.map(word => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}

	onMount(() => {
		// Preload critical components before any events arrive
		const criticalComponents = [
			'contribution',
			'facilitator_decision',
			'convergence',
			'voting_complete',
			'synthesis_complete',
			'decomposition_complete'
		];

		// Fire all preloads in parallel
		Promise.all(criticalComponents.map(type => getComponentForEvent(type)))
			.then(() => console.log('[Events] Critical components preloaded'))
			.catch(err => console.warn('[Events] Component preload failed:', err));

		// Auth is already verified by parent layout, safe to load session
		// Run async initialization with proper sequencing
		(async () => {
			try {
				// Issue #1 fix: Sequential loading to prevent race conditions
				// STEP 1: Load session metadata
				await loadSession();

				// STEP 2: Load ALL historical events
				await loadHistoricalEvents();

				// STEP 3: Wait for Svelte to finish reactive updates
				// This ensures all historical events are processed before SSE starts
				await tick();

				console.log('[Events] Session and history loaded, Svelte tick complete, checking session status...');

				// STEP 4: Check if session is already completed - skip SSE if so
				if (session?.status === 'completed' || session?.status === 'failed') {
					console.log(`[Events] Session is ${session.status}, skipping SSE connection`);
					store.setConnectionStatus('connected'); // Show as connected (data is already loaded)
					return;
				}

				// STEP 5: NOW start SSE stream (historical events fully processed)
				// This prevents duplicate detection issues and missing events
				await startEventStream();

				console.log('[Events] Initialization sequence complete');
			} catch (err) {
				console.error('[Events] Initialization failed:', err);
				error = err instanceof Error ? err.message : 'Failed to initialize session';
				isLoading = false;
			}
		})();
	});

	// onDestroy moved below for cleanup consolidation

	async function loadSession() {
		try {
			const sessionData = await apiClient.getSession(sessionId);
			// Map API response to SessionData format
			const mappedSession = {
				id: sessionData.id,
				status: sessionData.status,
				phase: sessionData.phase,
				round_number: sessionData.round_number || sessionData.state?.round_number || undefined,
				created_at: sessionData.created_at,
				problem: sessionData.problem
			};
			store.setSession(mappedSession);
			store.setIsLoading(false);
		} catch (err) {
			console.error('Failed to load session:', err);
			store.setError(err instanceof Error ? err.message : 'Failed to load session');
			store.setIsLoading(false);
		}
	}

	async function loadHistoricalEvents() {
		try {
			console.log('[Events] Loading historical events...');
			const response = await apiClient.getSessionEvents(sessionId);

			console.log(`[Events] Loaded ${response.count} historical events`);

			// Convert historical events to SSEEvent format
			for (const event of response.events) {
				const sseEvent: SSEEvent = {
					event_type: event.event_type,
					session_id: event.session_id,
					timestamp: event.timestamp,
					data: event.data
				};
				addEvent(sseEvent);
			}

			// Auto-scroll after loading history
			scrollToLatestEventDebounced(false); // No smooth scroll for initial load
		} catch (err) {
			console.error('[Events] Failed to load historical events:', err);
			// Don't set error state - this is non-fatal, stream will still work
		}
	}

	async function startEventStream() {
		// Close existing connection if any
		if (sseClient) {
			sseClient.close();
		}

		// Reset connection state for manual retry
		store.setConnectionStatus('connecting');

		// Helper to handle SSE events (converts SSE format to SSEEvent)
		const handleSSEEvent = (eventType: string, event: MessageEvent) => {
			try {
				// Parse the data payload
				const payload = JSON.parse(event.data);

				// ADD THIS: Debug persona_selected events specifically
				if (eventType === 'persona_selected') {
					console.log('[EXPERT PANEL] Persona selected:', {
						persona_code: payload.persona?.code,
						persona_name: payload.persona?.name,
						order: payload.order,
						sub_problem_index: payload.sub_problem_index,
						timestamp: new Date().toISOString()
					});
				}

				// ADD THIS: Debug persona_selection_complete for flush trigger
				if (eventType === 'persona_selection_complete') {
					console.log('[EXPERT PANEL] Selection complete - triggering panel flush');
				}

				// Construct SSEEvent by adding event_type from SSE event name
				const sseEvent: SSEEvent = {
					event_type: eventType,
					session_id: payload.session_id || sessionId,
					timestamp: payload.timestamp || new Date().toISOString(),
					data: payload
				};

				addEvent(sseEvent);

				// Force immediate grouping for expert panel completion (bypass debounce)
				// This ensures expert panels appear instantly without waiting for next event
				if (eventType === 'persona_selection_complete' || eventType === 'persona_selected') {
					groupedEventsCache = groupEvents(store.events, debugMode);
					lastEventCountForGrouping = store.events.length;
				}

				// Auto-scroll to bottom with smooth animation (debounced)
				scrollToLatestEventDebounced(true);

				// Update session phase and round based on events
				store.updateSessionPhase(eventType, payload);
			} catch (err) {
				console.error(`Failed to parse ${eventType} event:`, err);
			}
		};

		// Event types to listen for
		const eventTypes = [
			'node_start',
			'node_end',
			'session_started',
			'decomposition_started',
			'decomposition_complete',
			'persona_selection_started',
			'persona_selected',
			'persona_selection_complete',
			'subproblem_started',
			'initial_round_started',
			'contribution',
			// 'facilitator_decision',  // Hidden - doesn't add value in current format
			'moderator_intervention',
			'convergence',
			'round_started',
			'voting_started',
			'persona_vote',
			'voting_complete',
			'synthesis_started',
			'synthesis_complete',
			'subproblem_complete',
			'meta_synthesis_started',
			'meta_synthesis_complete',
			'phase_cost_breakdown',
			'complete',
			'error',
			'clarification_requested',
		];

		// Build event handlers map
		const eventHandlers: Record<string, (event: MessageEvent) => void> = {};
		for (const eventType of eventTypes) {
			eventHandlers[eventType] = (event: MessageEvent) => handleSSEEvent(eventType, event);
		}

		// Create new SSE client with credentials support
		// Use relative URL - will be proxied by Vite dev server
		sseClient = new SSEClient(`/api/v1/sessions/${sessionId}/stream`, {
			onOpen: () => {
				console.log('[SSE] Connection established');
				store.setRetryCount(0);
				store.setConnectionStatus('connected');
			},
			onError: (err) => {
				console.error('[SSE] Connection error:', err, 'retry count:', store.retryCount);

				// Close existing connection
				sseClient?.close();

				if (store.retryCount < maxRetries) {
					store.setRetryCount(store.retryCount + 1);
					store.setConnectionStatus('retrying');
					const delay = Math.min(1000 * Math.pow(2, store.retryCount - 1), 5000);
					console.log(`[SSE] Retrying in ${delay}ms...`);

					setTimeout(() => {
						startEventStream();
					}, delay);
				} else {
					console.error('[SSE] Max retries reached');
					store.setConnectionStatus('error');
					store.setError('Failed to connect to session stream. Please refresh the page.');
				}
			},
			eventHandlers,
		});

		// Start the connection
		try {
			await sseClient.connect();
		} catch (err) {
			console.error('[SSE] Failed to start connection:', err);
		}
	}

	async function handlePause() {
		try {
			await apiClient.pauseDeliberation(sessionId);
		} catch (err) {
			console.error('Failed to pause session:', err);
		}
	}

	async function handleResume() {
		try {
			await apiClient.resumeDeliberation(sessionId);
			startEventStream();
		} catch (err) {
			console.error('Failed to resume session:', err);
		}
	}

	async function handleKill() {
		if (!confirm('Are you sure you want to stop this meeting? This cannot be undone.')) {
			return;
		}

		try {
			await apiClient.killDeliberation(sessionId);
			sseClient?.close();
		} catch (err) {
			console.error('Failed to kill session:', err);
		}
	}

	// Event icon function removed - using lucide icon components directly

	function formatTimestamp(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleTimeString();
	}

	/**
	 * Performance optimization: Memoized + debounced event grouping
	 *
	 * Caches grouped events to avoid recalculation on every render.
	 * Only recalculates when events.length changes, with 200ms debounce.
	 *
	 * Before: O(n) filter + O(n) iteration on every event
	 * After: O(n) only on events change, debounced for rapid streams
	 *
	 * Measured improvement: ~3-8ms → <1ms for cached renders (Issue #2)
	 */
	let groupedEventsCache = $state<EventGroup[]>([]);
	let lastEventCountForGrouping = $state(0);

	// Tiered debouncing for smart UI responsiveness
	const DEBOUNCE_CRITICAL = 50;   // Expert panel, rounds - needs immediate visibility
	const DEBOUNCE_NORMAL = 100;    // Contributions - balance UX and performance
	const DEBOUNCE_RAPID = 200;     // Status updates - can tolerate more delay

	// Debounced recalculation with dynamic delay
	let debounceTimeout: ReturnType<typeof setTimeout> | null = null;

	const recalculateGroupedEvents = (delay: number = DEBOUNCE_NORMAL) => {
		if (debounceTimeout) clearTimeout(debounceTimeout);
		debounceTimeout = setTimeout(() => {
			groupedEventsCache = groupEvents(events, debugMode);
			lastEventCountForGrouping = events.length;
		}, delay);
	};

	$effect(() => {
		// Only trigger recalculation if events changed
		if (events.length !== lastEventCountForGrouping) {
			const lastEvent = events[events.length - 1];

			// Critical events get fastest rendering (50ms)
			const isCritical = lastEvent?.event_type === 'persona_selection_complete'
				|| lastEvent?.event_type === 'round_started'
				|| lastEvent?.event_type === 'persona_selected';

			const delay = isCritical ? DEBOUNCE_CRITICAL : DEBOUNCE_NORMAL;

			// ADD THIS: Log debounce timing for critical events
			if (isCritical) {
				console.log('[EXPERT PANEL] Using critical debounce:', {
					eventType: lastEvent?.event_type,
					delay: delay + 'ms',
					eventCount: events.length
				});
			}

			recalculateGroupedEvents(delay);
		}
	});

	const groupedEvents = $derived(groupedEventsCache);

	// ISSUE FIX: Staggered display for expert contributions
	// This creates a progressive reveal effect where contributions appear one at a time
	// with random delays (400-600ms) to feel more dynamic and natural
	const MIN_DELAY = 400; // 400ms minimum
	const MAX_DELAY = 600; // 600ms maximum
	let visibleContributionCounts = $state<Map<string, number>>(new Map());

	// Track pending experts for "thinking" indicator
	let pendingExperts = $state<{ name: string; roundKey: string }[]>([]);

	// Generate random delay between min and max
	function getRandomDelay(): number {
		return Math.floor(Math.random() * (MAX_DELAY - MIN_DELAY + 1)) + MIN_DELAY;
	}

	// Generate varied thinking messages
	const thinkingMessages = [
		(name: string) => `${name} is thinking...`,
		(name: string) => `${name} is formulating a response...`,
		(name: string) => `${name} wants to contribute...`,
		(name: string) => `${name} is considering the discussion...`,
		(name: string) => `${name} is preparing insights...`,
	];

	function getThinkingMessage(name: string, index: number): string {
		const msgFn = thinkingMessages[index % thinkingMessages.length];
		return msgFn(name);
	}

	// Initial waiting messages (before any events arrive) - cycle every 1.5s
	const initialWaitingMessages = [
		'Waiting for deliberation to start...',
		'Preparing your expert panel...',
		'Setting up the discussion...',
	];

	// Between-rounds waiting messages (shown after all contributions in a round are revealed)
	const betweenRoundsMessages = [
		'Experts are consulting...',
		'Analyzing the discussion so far...',
		'Preparing the next round of insights...',
		'Experts are researching...',
		'Synthesizing perspectives...',
		'Evaluating different viewpoints...',
		'Building on previous contributions...',
	];

	// Phase-specific messages
	const phaseMessages: Record<string, string> = {
		'persona_selection': 'Experts are being selected...',
		'initial_round': 'Experts are familiarising themselves with the problem...',
	};

	// State for rotating initial waiting messages
	let initialWaitingMessageIndex = $state(0);
	let initialWaitingInterval: ReturnType<typeof setInterval> | null = null;

	// State for rotating between-rounds messages
	let betweenRoundsMessageIndex = $state(0);
	let betweenRoundsInterval: ReturnType<typeof setInterval> | null = null;

	// Start initial waiting message cycling when events.length === 0
	$effect(() => {
		if (events.length === 0 && !initialWaitingInterval) {
			initialWaitingInterval = setInterval(() => {
				initialWaitingMessageIndex = (initialWaitingMessageIndex + 1) % initialWaitingMessages.length;
			}, 1500);
		} else if (events.length > 0 && initialWaitingInterval) {
			clearInterval(initialWaitingInterval);
			initialWaitingInterval = null;
		}

		return () => {
			if (initialWaitingInterval) {
				clearInterval(initialWaitingInterval);
				initialWaitingInterval = null;
			}
		};
	});

	// Detect if we're waiting for the first contributions (early phases)
	const isWaitingForFirstContributions = $derived.by(() => {
		if (!session || session.status === 'completed') return false;

		// Get contributions count
		const contributionCount = events.filter(e => e.event_type === 'contribution').length;

		// Check if we have events but no contributions yet
		if (events.length > 0 && contributionCount === 0) {
			// Check phase - show phase-specific message
			const phase = session.phase;
			if (phase === 'persona_selection' || phase === 'initial_round') {
				return true;
			}
		}

		return false;
	});

	// Get the appropriate waiting message for the current phase
	const phaseWaitingMessage = $derived.by(() => {
		if (!session?.phase) return 'Preparing...';
		return phaseMessages[session.phase] || 'Experts are preparing...';
	});

	// Detect if we're waiting for the next round
	const isWaitingForNextRound = $derived.by(() => {
		// Don't show if session is complete
		if (session?.status === 'completed' || session?.phase === 'complete' || session?.phase === 'synthesis') {
			return false;
		}

		// Don't show if we're synthesizing or voting (those have their own indicators)
		if (isSynthesizing || isVoting) {
			return false;
		}

		// Don't show if we're waiting for first contributions
		if (isWaitingForFirstContributions) {
			return false;
		}

		// Find the latest round group
		const roundGroups = groupedEvents.filter(g => g.type === 'round' && g.events);
		if (roundGroups.length === 0) return false;

		const latestRound = roundGroups[roundGroups.length - 1];
		if (!latestRound.events || !latestRound.roundNumber) return false;

		const roundKey = `round-${latestRound.roundNumber}`;
		const visibleCount = visibleContributionCounts.get(roundKey) || 0;
		const totalInRound = latestRound.events.length;

		// All contributions in this round are visible AND we're still active
		return visibleCount >= totalInRound && session?.status === 'active';
	});

	// Rotate between-rounds message every 1.5 seconds when waiting
	$effect(() => {
		if (isWaitingForNextRound && !betweenRoundsInterval) {
			betweenRoundsInterval = setInterval(() => {
				betweenRoundsMessageIndex = (betweenRoundsMessageIndex + 1) % betweenRoundsMessages.length;
			}, 1500);
		} else if (!isWaitingForNextRound && betweenRoundsInterval) {
			clearInterval(betweenRoundsInterval);
			betweenRoundsInterval = null;
		}

		return () => {
			if (betweenRoundsInterval) {
				clearInterval(betweenRoundsInterval);
				betweenRoundsInterval = null;
			}
		};
	});

	$effect(() => {
		// Track newly added contribution groups and stage their reveals
		for (const group of groupedEvents) {
			if (group.type === 'round' && group.events) {
				const roundKey = `round-${group.roundNumber}`;
				const currentVisible = visibleContributionCounts.get(roundKey) || 0;
				const totalContributions = group.events.length;

				// If we have new contributions to reveal
				if (currentVisible < totalContributions) {
					// Calculate how many we need to reveal
					const toReveal = totalContributions - currentVisible;

					// Update pending experts list
					const newPending = group.events.slice(currentVisible).map(e => ({
						name: (e.data as any).persona_name || 'Expert',
						roundKey
					}));
					pendingExperts = newPending;

					// Stage the reveals with random delays
					let cumulativeDelay = 0;
					for (let i = 0; i < toReveal; i++) {
						const revealIndex = currentVisible + i;
						const delay = i === 0 ? getRandomDelay() : cumulativeDelay;
						cumulativeDelay += getRandomDelay();

						setTimeout(() => {
							visibleContributionCounts.set(roundKey, revealIndex + 1);
							visibleContributionCounts = new Map(visibleContributionCounts);

							// Update pending experts (remove the one we just revealed)
							pendingExperts = pendingExperts.filter((_, idx) => idx !== 0);
						}, delay);
					}
				}
			}
		}
	});

	// Helper to get visible contributions for a round
	function getVisibleContributions(roundNumber: number | undefined, allContributions: SSEEvent[]): SSEEvent[] {
		if (!roundNumber) return allContributions;
		const roundKey = `round-${roundNumber}`;
		const visibleCount = visibleContributionCounts.get(roundKey) || 0;
		return allContributions.slice(0, visibleCount);
	}

	// Progress calculation
	function calculateProgress(session: SessionData | null): number {
		if (!session) return 0;

		// Handle completed meetings (either by status or phase)
		if (session.status === 'completed' || session.phase === 'complete') {
			return 100;
		}

		// Handle synthesis phase
		if (session.phase === 'synthesis') {
			return 95;
		}

		const baseProgress = PHASE_PROGRESS_MAP[session.phase as keyof typeof PHASE_PROGRESS_MAP] || 0;

		// Add round-based progress within discussion phase
		if (session.phase === 'discussion' && session.round_number) {
			const roundProgress = Math.min((session.round_number / 10) * 25, 25);
			return Math.min(baseProgress + roundProgress, 100);
		}

		return baseProgress;
	}

	/**
	 * Performance optimization: Memoized sub-problem tabs calculation
	 *
	 * Caches tab metrics to avoid expensive recalculation on every render.
	 * Only recalculates when events.length changes.
	 */
	let subProblemTabsCache = $state<SubProblemTab[]>([]);
	let lastEventCountForTabs = $state(0);

	$effect(() => {
		if (events.length !== lastEventCountForTabs) {
			subProblemTabsCache = buildSubProblemTabs(events, eventsBySubProblem);
			lastEventCountForTabs = events.length;
		}
	});

	const subProblemTabs = $derived(subProblemTabsCache);

	// Active tab state
	let activeSubProblemTab = $state<string | undefined>(undefined);

	// View mode for contribution cards: 'simple' (1-2 sentence) or 'full' (structured breakdown)
	// Applied globally to all sub-problems for consistency
	let contributionViewMode = $state<'simple' | 'full'>('simple');
	// Per-card view mode overrides (for individual card toggling)
	let cardViewModes = $state<Map<string, 'simple' | 'full'>>(new Map());
	let showFullTranscripts = $state(false);

	// Toggle individual card view mode
	function toggleCardViewMode(cardId: string) {
		const current = cardViewModes.get(cardId) ?? contributionViewMode;
		const next = current === 'simple' ? 'full' : 'simple';
		cardViewModes.set(cardId, next);
		cardViewModes = new Map(cardViewModes); // Trigger reactivity
	}

	// Set global view mode and clear all card overrides
	function setGlobalViewMode(mode: 'simple' | 'full') {
		contributionViewMode = mode;
		cardViewModes.clear();
		cardViewModes = new Map(cardViewModes); // Trigger reactivity
	}

	// Get effective view mode for a card (card override or global)
	function getCardViewMode(cardId: string): 'simple' | 'full' {
		return cardViewModes.get(cardId) ?? contributionViewMode;
	}

	// Set initial active tab when tabs are created
	$effect(() => {
		if (subProblemTabs.length > 0 && !activeSubProblemTab) {
			activeSubProblemTab = subProblemTabs[0].id;
		}
	});

	/**
	 * Priority 1 Optimization: Memoize active tab events
	 * Caches filtered events for the active tab to avoid re-filtering on every render
	 */
	const activeTabEvents = $derived.by(() => {
		if (!activeSubProblemTab) return [];

		const tabIndex = parseInt(activeSubProblemTab.replace('subproblem-', ''));
		return eventsBySubProblem.get(tabIndex) || [];
	});

	// Hide decomposition_complete when tabs are visible (it's redundant - we already see the tabs)
	const shouldHideDecomposition = $derived(subProblemTabs.length > 1);

	// ============================================================================
	// PERFORMANCE OPTIMIZATIONS (continued)
	// ============================================================================

	/**
	 * Performance optimization: Memoized + debounced event indexing by sub-problem
	 *
	 * Caches Map-based index to avoid rebuilding on every render.
	 * Only recalculates when events.length changes, with 200ms debounce.
	 */
	let eventsBySubProblemCache = $state(new Map<number, SSEEvent[]>());
	let lastEventCountForIndex = $state(0);

	// Debounced recalculation function
	let indexDebounceTimeout: ReturnType<typeof setTimeout> | null = null;

	const recalculateEventIndex = () => {
		if (indexDebounceTimeout) clearTimeout(indexDebounceTimeout);
		indexDebounceTimeout = setTimeout(() => {
			eventsBySubProblemCache = indexEventsBySubProblem(events);
			lastEventCountForIndex = events.length;

			console.log('[EVENT INDEX DEBUG]', {
				totalEvents: events.length,
				indexedSubProblems: Array.from(eventsBySubProblemCache.keys()),
				eventsPerSubProblem: Array.from(eventsBySubProblemCache.entries()).map(([key, val]) => ({
					subProblem: key,
					count: val.length
				}))
			});
		}, 200);
	}; // 200ms debounce for rapid event streams

	$effect(() => {
		if (events.length !== lastEventCountForIndex) {
			recalculateEventIndex();
		}
	});

	const eventsBySubProblem = $derived(eventsBySubProblemCache);

	/**
	 * Priority 1 Optimization: Debounced auto-scroll
	 * Prevents scroll thrashing on rapid event arrivals (300ms debounce)
	 *
	 * Increased from 100ms to 300ms to better handle rapid SSE streams (Issue #2)
	 */
	let scrollDebounceTimeout: ReturnType<typeof setTimeout> | null = null;

	const scrollToLatestEventDebounced = (smooth = true) => {
		if (scrollDebounceTimeout) clearTimeout(scrollDebounceTimeout);
		scrollDebounceTimeout = setTimeout(() => {
			if (!autoScroll) return;

			const container = document.getElementById('events-container');
			if (container) {
				container.scrollTo({
					top: container.scrollHeight,
					behavior: smooth ? 'smooth' : 'auto',
				});
			}
		}, 300); // Increased from 100ms for better performance
	};

	// Clean up on component destroy
	onDestroy(() => {
		if (sseClient) {
			sseClient.close();
		}
	});

	// Visual hierarchy: Get CSS classes based on event priority (MINIMAL COLORS)
	function getEventCardClasses(priority: EventPriority): string {
		if (priority === 'major') {
			return 'bg-neutral-50 dark:bg-neutral-900/50 border-2 border-neutral-300 dark:border-neutral-700';
		}
		if (priority === 'meta') {
			return 'bg-neutral-50/50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700';
		}
		return 'bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700';
	}
</script>

<svelte:head>
	<title>Meeting {sessionId} - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 sticky top-0 z-10">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/dashboard"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
						aria-label="Back to dashboard"
					>
						<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</a>
					<div class="flex-1">
						<h1 class="text-[1.875rem] font-semibold leading-tight text-neutral-900 dark:text-white">
							Meeting in Progress
						</h1>
					</div>
				</div>

				<div class="flex items-center gap-2">
					{#if session?.status === 'active'}
						<Button variant="secondary" size="md" onclick={handlePause}>
							{#snippet children()}
								<Pause size={16} />
								<span>Pause</span>
							{/snippet}
						</Button>
					{:else if session?.status === 'paused'}
						<Button variant="brand" size="md" onclick={handleResume}>
							{#snippet children()}
								<Play size={16} />
								<span>Resume</span>
							{/snippet}
						</Button>
					{/if}
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- ARIA Live Region for Event Updates (A11Y: Announce new events to screen readers) -->
		<div class="sr-only" role="status" aria-live="polite" aria-atomic="true">
			{#if events.length > 0}
				{@const latestEvent = events[events.length - 1]}
				{#if latestEvent.event_type === 'contribution'}
					New contribution from {latestEvent.data.persona_name || 'expert'}
				{:else if latestEvent.event_type === 'convergence'}
					Convergence check: {Math.round((Number(latestEvent.data.score) / Number(latestEvent.data.threshold ?? 0.85)) * 100)}% of threshold
				{:else if latestEvent.event_type === 'synthesis_complete'}
					Synthesis complete
				{:else if latestEvent.event_type === 'complete'}
					Deliberation complete
				{:else if latestEvent.event_type === 'voting_complete'}
					Voting complete
				{:else if latestEvent.event_type === 'subproblem_complete'}
					Sub-problem complete
				{/if}
			{/if}
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
			<!-- Events Stream with Tab Navigation -->
			<div class="lg:col-span-2 lg:self-stretch">
				<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700">
					<div class="border-b border-slate-200 dark:border-slate-700">
						<!-- Header Row -->
						<div class="p-4 flex items-center justify-between">
							<div class="flex items-center gap-3">
								<h2 class="text-lg font-semibold text-slate-900 dark:text-white">
									{#if subProblemTabs.length > 1}
										Sub-Problem Analysis
									{:else}
										Deliberation Stream
									{/if}
								</h2>
								{#if connectionStatus === 'connecting'}
									<span class="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
										<span class="inline-block w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></span>
										Connecting...
									</span>
								{:else if connectionStatus === 'connected'}
									<span class="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
										<span class="inline-block w-2 h-2 bg-green-500 rounded-full"></span>
										Connected
									</span>
								{:else if connectionStatus === 'retrying'}
									<div class="flex items-center gap-2">
										<span class="flex items-center gap-1.5 text-xs text-orange-600 dark:text-orange-400">
											<span class="inline-block w-2 h-2 bg-orange-500 rounded-full animate-pulse"></span>
											Retrying... ({retryCount}/{maxRetries})
										</span>
										<button
											onclick={() => startEventStream()}
											class="px-2 py-1 text-xs font-medium text-orange-700 dark:text-orange-300 hover:text-orange-900 dark:hover:text-orange-100 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded transition-colors"
										>
											Retry Now
										</button>
									</div>
								{:else if connectionStatus === 'error'}
									<div class="flex items-center gap-2">
										<span class="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
											<span class="inline-block w-2 h-2 bg-red-500 rounded-full"></span>
											Connection Failed
										</span>
										<button
											onclick={() => startEventStream()}
											class="px-2 py-1 text-xs font-medium text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-red-100 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
										>
											Retry Now
										</button>
									</div>
								{/if}
							</div>
							<div class="flex items-center gap-4">
								<label for="auto-scroll-checkbox" class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
									<input
										id="auto-scroll-checkbox"
										type="checkbox"
										bind:checked={autoScroll}
										class="rounded"
									/>
									Auto-scroll
								</label>

								<!-- View mode toggle -->
								<div class="flex items-center gap-2">
									<span class="text-sm text-slate-600 dark:text-slate-400">View:</span>
									<div class="flex items-center gap-1 bg-slate-200 dark:bg-slate-700 rounded-lg p-0.5">
										<button
											onclick={() => setGlobalViewMode('simple')}
											class="px-2 py-1 text-xs font-medium rounded-md transition-colors {contributionViewMode === 'simple'
												? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
												: 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}"
										>
											Simple
										</button>
										<button
											onclick={() => setGlobalViewMode('full')}
											class="px-2 py-1 text-xs font-medium rounded-md transition-colors {contributionViewMode === 'full'
												? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
												: 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}"
										>
											Detailed
										</button>
									</div>
								</div>
							</div>
						</div>

						<!-- Progress Bar -->
						{#if session}
							<div class="px-4 pb-3">
								<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
									<div
										class="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
										style="width: {calculateProgress(session)}%"
									></div>
								</div>
							</div>
						{/if}
					</div>

					<div
						id="events-container"
						class="overflow-y-auto"
						style="height: calc(100vh - 400px); min-height: 600px;"
					>
						{#if isLoading}
							<!-- Skeleton Loading States -->
							<div class="space-y-4 p-4">
								{#each Array(5) as _, i}
									<EventCardSkeleton />
								{/each}
							</div>
						{:else if events.length === 0}
							<div class="flex flex-col items-center justify-center h-full text-slate-500 dark:text-slate-400 p-4 gap-3">
								<div class="flex gap-1">
									<div class="w-2 h-2 rounded-full bg-slate-400 animate-pulse" style="animation-delay: 0ms"></div>
									<div class="w-2 h-2 rounded-full bg-slate-400 animate-pulse" style="animation-delay: 150ms"></div>
									<div class="w-2 h-2 rounded-full bg-slate-400 animate-pulse" style="animation-delay: 300ms"></div>
								</div>
								<p class="transition-opacity duration-300">{initialWaitingMessages[initialWaitingMessageIndex]}</p>
							</div>
						{:else if subProblemTabs.length > 1}
							<!-- Tab-based navigation for multiple sub-problems -->
							<div class="h-full flex flex-col">
								<div class="border-b border-slate-200 dark:border-slate-700">
									<div class="flex overflow-x-auto px-4 pt-3" role="tablist" aria-label="Sub-problem tabs">
										{#each subProblemTabs as tab}
											{@const isActive = activeSubProblemTab === tab.id}
											<button
												type="button"
												role="tab"
												aria-selected={isActive}
												aria-controls="tabpanel-{tab.id}"
												id="tab-{tab.id}"
												class={[
													'flex-shrink-0 px-4 py-2 border-b-2 -mb-px transition-all text-sm font-medium',
													isActive
														? 'border-brand-600 text-brand-700 dark:border-brand-400 dark:text-brand-400'
														: 'border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:border-slate-300 dark:hover:border-slate-600',
												].join(' ')}
												onclick={() => activeSubProblemTab = tab.id}
											>
												<div class="flex items-center gap-2">
													<span>{tab.label}</span>
													{#if tab.status === 'complete'}
														<CheckCircle size={14} class="text-current" />
													{/if}
												</div>
											</button>
										{/each}
										<!-- Conclusion tab (appears when meta-synthesis is complete) -->
										{#if showConclusionTab}
											{@const isActive = activeSubProblemTab === 'conclusion'}
											<button
												type="button"
												role="tab"
												aria-selected={isActive}
												aria-controls="tabpanel-conclusion"
												id="tab-conclusion"
												class={[
													'flex-shrink-0 px-4 py-2 border-b-2 -mb-px transition-all text-sm font-medium',
													isActive
														? 'border-success-600 text-success-700 dark:border-success-400 dark:text-success-400'
														: 'border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:border-slate-300 dark:hover:border-slate-600',
												].join(' ')}
												onclick={() => activeSubProblemTab = 'conclusion'}
											>
												<div class="flex items-center gap-2">
													<span>Summary</span>
													<CheckCircle size={14} class="text-success-600 dark:text-success-400" />
												</div>
											</button>
										{/if}
									</div>
								</div>

								{#each subProblemTabs as tab}
									{@const isTabActive = tab.id === activeSubProblemTab}
									{@const tabIndex = parseInt(tab.id.replace('subproblem-', ''))}
									{@const subGroupedEvents = groupedEvents.filter(group => {
										if (group.type === 'single' && group.event) {
											// SKIP decomposition in sub-problem tabs - it belongs on Summary
											if (group.event.event_type === 'decomposition_complete') {
												return false;
											}
											const eventSubIndex = group.event.data.sub_problem_index as number | undefined;
											return eventSubIndex === tabIndex;
										} else if (group.type === 'round' || group.type === 'expert_panel') {
											if (group.events && group.events.length > 0) {
												const eventSubIndex = group.events[0].data.sub_problem_index as number | undefined;
												return eventSubIndex === tabIndex;
											}
										}
										return false;
									})}
									<!-- Tab panel with proper ARIA attributes -->
									<div
										class="flex-1 overflow-y-auto p-4 space-y-4"
										role="tabpanel"
										id="tabpanel-{tab.id}"
										aria-labelledby="tab-{tab.id}"
										aria-hidden={!isTabActive}
										inert={!isTabActive}
										hidden={!isTabActive}
									>
										<!-- Sub-problem header -->
										<div class="bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
											<h3 class="text-base font-semibold text-slate-900 dark:text-white">
												{tab.goal}
											</h3>
										</div>

										{#each subGroupedEvents as group, index (index)}
											{#if group.type === 'expert_panel' && group.events}
												<div transition:fade={{ duration: 300, delay: 50 }}>
													{#await getComponentForEvent('expert_panel')}
														<!-- Loading skeleton for expert panel -->
														<ExpertPanelSkeleton expertCount={group.events.length} />
													{:then ExpertPanelComponent}
														<ExpertPanelComponent
															experts={group.events.map((e) => ({
																persona: e.data.persona as any,
																rationale: e.data.rationale as string,
																order: e.data.order as number,
															}))}
															subProblemGoal={group.subProblemGoal}
														/>
													{:catch error}
														<GenericEvent event={group.events[0]} />
													{/await}
												</div>
											{:else if group.type === 'round' && group.events}
												{@const roundKey = `round-${group.roundNumber}`}
												{@const visibleCount = visibleContributionCounts.get(roundKey) || 0}
												{@const hasMoreToReveal = visibleCount < group.events.length}
												{@const nextExpert = hasMoreToReveal ? group.events[visibleCount]?.data?.persona_name as string : null}
												<div transition:fade={{ duration: 300, delay: 50 }}>
													<div class="space-y-3">
														<h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
															<span>Round {group.roundNumber} Contributions</span>
														</h3>
														{#each getVisibleContributions(group.roundNumber, group.events) as contrib}
															{#await getComponentForEvent('contribution')}
																<!-- Loading skeleton with timeout fallback -->
																<ContributionSkeleton />
															{:then ExpertPerspectiveCardComponent}
																{#if ExpertPerspectiveCardComponent}
																	{@const cardId = `${(contrib.data as any).persona_code}-${(contrib.data as any).round}`}
																	<ExpertPerspectiveCardComponent
																		event={contrib as any}
																		viewMode={getCardViewMode(cardId)}
																		showFull={showFullTranscripts}
																		onToggle={() => toggleCardViewMode(cardId)}
																	/>
																{:else}
																	<!-- Component loaded but null - use GenericEvent -->
																	<GenericEvent event={contrib} />
																	<div class="text-xs text-red-600 mt-2">
																		Component failed to load for: contribution
																	</div>
																{/if}
															{:catch error}
																<!-- Component import failed - show error with details -->
																<GenericEvent event={contrib} />
																<div class="text-xs text-red-600 mt-2">
																	Error loading component: {error.message || 'Unknown error'}
																</div>
															{/await}
														{/each}

														<!-- Thinking indicator when more contributions are pending -->
														{#if hasMoreToReveal && nextExpert}
															<div class="flex items-center gap-2 py-2 px-3 text-sm text-slate-500 dark:text-slate-400" transition:fade={{ duration: 200 }}>
																<div class="flex items-center gap-1">
																	<span class="w-1.5 h-1.5 bg-slate-400 dark:bg-slate-500 rounded-full animate-pulse" style="animation-delay: 0ms;"></span>
																	<span class="w-1.5 h-1.5 bg-slate-400 dark:bg-slate-500 rounded-full animate-pulse" style="animation-delay: 150ms;"></span>
																	<span class="w-1.5 h-1.5 bg-slate-400 dark:bg-slate-500 rounded-full animate-pulse" style="animation-delay: 300ms;"></span>
																</div>
																<span class="italic">{getThinkingMessage(nextExpert, visibleCount)}</span>
															</div>
														{/if}
													</div>
												</div>
											{:else if group.type === 'single' && group.event}
												{@const event = group.event}
												{@const priority = getEventPriority(event.event_type)}
												<div
													class="{getEventCardClasses(priority)} rounded-lg p-4"
													in:fade|global={{ duration: 300, delay: 50 }}
													out:fade|global={{ duration: 200 }}
												>
													<div class="flex items-start gap-3">
														{#if event.event_type === 'synthesis_complete' || event.event_type === 'subproblem_complete' || event.event_type === 'meta_synthesis_complete' || event.event_type === 'complete'}
															<CheckCircle size={20} class="text-semantic-success" />
														{:else if event.event_type === 'error'}
															<AlertCircle size={20} class="text-semantic-error" />
														{/if}
														<div class="flex-1 min-w-0">
															<div class="flex items-center justify-between mb-3">
																<RelativeTimestamp timestamp={event.timestamp} />
															</div>

															{#await getComponentForEvent(event.event_type)}
																<!-- Loading skeleton with timeout fallback -->
																<EventCardSkeleton hasAvatar={false} />
															{:then EventComponent}
																{#if EventComponent}
																	<EventComponent event={event as any} />
																{:else}
																	<!-- Component loaded but null - use GenericEvent -->
																	<GenericEvent event={event} />
																	<div class="text-xs text-red-600 mt-2">
																		Component failed to load for: {event.event_type}
																	</div>
																{/if}
															{:catch error}
																<!-- Component import failed - show error with details -->
																<GenericEvent event={event} />
																<div class="text-xs text-red-600 mt-2">
																	Error loading component: {error.message || 'Unknown error'}
																</div>
															{/await}
														</div>
													</div>
												</div>
											{/if}
										{/each}

										<!-- Synthesis preview for this sub-problem (if available) -->
										{#if subProblemCompleteEvents[tabIndex]?.data?.synthesis}
											<div class="mt-8 border-t border-slate-200 dark:border-slate-700 pt-6">
												{#await getComponentForEvent('subproblem_complete')}
													<EventCardSkeleton />
												{:then SubProblemComponent}
													{#if SubProblemComponent}
														<SubProblemComponent event={subProblemCompleteEvents[tabIndex]} />
													{/if}
												{:catch}
													<!-- Fallback to raw display -->
													{@const spData = subProblemCompleteEvents[tabIndex].data as { synthesis: string; goal: string }}
													<h4 class="text-md font-semibold mb-3 flex items-center gap-2 text-slate-900 dark:text-white">
														<svg class="w-5 h-5 text-success-600 dark:text-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
															<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
														</svg>
														Synthesis
													</h4>
													<div class="prose prose-slate dark:prose-invert max-w-none text-sm text-slate-700 dark:text-slate-300">
														{@html spData.synthesis.replace(/\n/g, '<br />')}
													</div>
												{/await}
											</div>
										{/if}

										<!-- Phase-specific waiting indicator (tabbed view) -->
										{#if isWaitingForFirstContributions && isTabActive}
											<div class="flex items-center gap-3 py-4 px-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800" transition:fade={{ duration: 300 }}>
												<div class="flex items-center gap-1">
													<span class="w-2 h-2 bg-amber-500 dark:bg-amber-400 rounded-full animate-bounce" style="animation-delay: 0ms;"></span>
													<span class="w-2 h-2 bg-amber-500 dark:bg-amber-400 rounded-full animate-bounce" style="animation-delay: 150ms;"></span>
													<span class="w-2 h-2 bg-amber-500 dark:bg-amber-400 rounded-full animate-bounce" style="animation-delay: 300ms;"></span>
												</div>
												<span class="text-sm text-amber-700 dark:text-amber-300 font-medium">
													{phaseWaitingMessage}
												</span>
											</div>
										{/if}

										<!-- Between-rounds waiting indicator (tabbed view) -->
										{#if isWaitingForNextRound && isTabActive}
											<div class="flex items-center gap-3 py-4 px-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800" transition:fade={{ duration: 300 }}>
												<div class="flex items-center gap-1">
													<span class="w-2 h-2 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0ms;"></span>
													<span class="w-2 h-2 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 150ms;"></span>
													<span class="w-2 h-2 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 300ms;"></span>
												</div>
												<span class="text-sm text-blue-700 dark:text-blue-300 font-medium">
													{betweenRoundsMessages[betweenRoundsMessageIndex]}
												</span>
											</div>
										{/if}
									</div>
								{/each}

								<!-- Conclusion Tab Panel -->
								{#if showConclusionTab}
									{@const isTabActive = activeSubProblemTab === 'conclusion'}
									<div
										class="flex-1 overflow-y-auto p-4 space-y-6"
										role="tabpanel"
										id="tabpanel-conclusion"
										aria-labelledby="tab-conclusion"
										aria-hidden={!isTabActive}
										inert={!isTabActive}
										hidden={!isTabActive}
									>
										<!-- Problem Decomposition Overview -->
										{#if decompositionEvent}
											{#await getComponentForEvent('decomposition_complete')}
												<EventCardSkeleton />
											{:then DecompositionComponent}
												{#if DecompositionComponent}
													<DecompositionComponent event={decompositionEvent} />
												{/if}
											{:catch}
												<!-- Silently skip if component fails to load -->
											{/await}
										{/if}

										<!-- Progress indicator for multi-problem meetings -->
										{#if subProblemCompleteEvents.length > 0 && !metaSynthesisEvent && subProblemTabs.length > 1}
											<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4 mb-6">
												<div class="flex items-center gap-2">
													<svg class="animate-spin h-5 w-5 text-blue-600 dark:text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
														<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
														<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
													</svg>
													<span class="text-sm font-medium text-blue-900 dark:text-blue-100">
														{subProblemCompleteEvents.length} of {subProblemTabs.length} sub-problems completed
													</span>
												</div>
												<p class="text-sm text-blue-700 dark:text-blue-300 mt-2">Generating final synthesis...</p>
											</div>
										{/if}

										<!-- Meta-Synthesis / Overall Conclusion -->
										{#if metaSynthesisEvent}
											<!-- Use SynthesisComplete component for proper XML parsing and card rendering -->
											{#await getComponentForEvent('synthesis_complete')}
												<EventCardSkeleton />
											{:then SynthesisComponent}
												{#if SynthesisComponent}
													<SynthesisComponent event={metaSynthesisEvent} />
												{/if}
											{:catch}
												<!-- Fallback to raw display if component fails -->
												<div class="prose prose-slate dark:prose-invert max-w-none">
													{@html (metaSynthesisEvent.data.synthesis as string).replace(/\n/g, '<br />')}
												</div>
											{/await}
										{:else if synthesisCompleteEvent}
											<!-- Use SynthesisComplete component for proper XML parsing and card rendering -->
											{#await getComponentForEvent('synthesis_complete')}
												<EventCardSkeleton />
											{:then SynthesisComponent}
												{#if SynthesisComponent}
													<SynthesisComponent event={synthesisCompleteEvent} />
												{/if}
											{:catch}
												<!-- Fallback to raw display if component fails -->
												<div class="prose prose-slate dark:prose-invert max-w-none">
													{@html (synthesisCompleteEvent.data.synthesis as string).replace(/\n/g, '<br />')}
												</div>
											{/await}
										{:else if subProblemCompleteEvents.length > 0 && subProblemCompleteEvents.some(e => e.data.synthesis)}
											<!-- Show individual sub-problem syntheses using SubProblemProgress component -->
											<div class="space-y-6">
												<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">Sub-Problem Syntheses</h3>
												{#each subProblemCompleteEvents.filter(e => e.data.synthesis) as spEvent}
													{#await getComponentForEvent('subproblem_complete')}
														<EventCardSkeleton />
													{:then SubProblemComponent}
														{#if SubProblemComponent}
															<SubProblemComponent event={spEvent} />
														{/if}
													{:catch}
														<!-- Fallback to simple display -->
														{@const spData = spEvent.data as { goal: string; synthesis: string; sub_problem_index: number }}
														<div class="border-l-4 border-blue-500 pl-4">
															<h4 class="font-medium mb-2">{spData.goal}</h4>
															<div class="prose prose-slate dark:prose-invert max-w-none text-slate-700 dark:text-slate-300">
																{@html spData.synthesis.replace(/\n/g, '<br />')}
															</div>
														</div>
													{/await}
												{/each}
											</div>
										{:else}
											<!-- Fallback: Meeting complete but no synthesis yet -->
											<div class="text-center py-12">
												{#if session?.status === 'running' || session?.status === 'created' || session?.status === 'active'}
													<div class="flex flex-col items-center gap-4">
														<svg class="animate-spin h-8 w-8 text-slate-400 dark:text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
															<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
															<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
														</svg>
														<p class="text-slate-600 dark:text-slate-400">Deliberation in progress...</p>
														<p class="text-sm text-slate-500 dark:text-slate-500">The final synthesis will appear here when complete</p>
													</div>
												{:else if session?.status === 'failed'}
													<div class="text-red-600 dark:text-red-400">
														<p class="font-medium">Synthesis generation failed</p>
														<p class="text-sm mt-2">Please check the logs or retry the meeting</p>
													</div>
												{:else}
													<p class="text-slate-500 dark:text-slate-400">No synthesis available</p>
												{/if}
											</div>
										{/if}

										<!-- Individual Sub-Problem Conclusions -->
										{#if subProblemCompleteEvents.length > 0}
											<div class="space-y-4">
												<h3 class="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
													<svg class="w-5 h-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
													</svg>
													Individual Sub-Problem Conclusions
												</h3>

												{#each subProblemCompleteEvents as spEvent, index}
													{@const spData = spEvent.data as { goal: string; synthesis: string; sub_problem_index: number; expert_panel: string[]; contribution_count: number }}
													<div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
														<div class="flex items-start gap-3">
															<div class="flex-shrink-0 w-8 h-8 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-full flex items-center justify-center text-sm font-semibold">
																{spData.sub_problem_index + 1}
															</div>
															<div class="flex-1 min-w-0">
																<h4 class="text-sm font-semibold text-slate-900 dark:text-white mb-2">
																	{spData.goal}
																</h4>
																{#if spData.synthesis}
																	<p class="text-sm text-slate-700 dark:text-slate-300 mb-2">
																		{spData.synthesis}
																	</p>
																{:else}
																	<p class="text-sm text-slate-500 dark:text-slate-400 italic">No synthesis available.</p>
																{/if}
																<div class="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400 mt-2">
																	<span>{spData.expert_panel?.length || 0} experts</span>
																	<span>{spData.contribution_count || 0} contributions</span>
																</div>
															</div>
														</div>
													</div>
												{/each}
											</div>
										{/if}
									</div>
								{/if}
							</div>
						{:else}
							<!-- Single sub-problem or linear view -->
							<div class="p-4 space-y-4">

							<!-- Sub-problem transition loading state -->
							{#if isTransitioningSubProblem}
								<div class="animate-pulse bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
									<div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4 mb-2"></div>
									<div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
									<p class="text-sm text-slate-500 dark:text-slate-400 mt-2">
										Preparing next sub-problem...
									</p>
								</div>
							{/if}

							<!-- Phase-specific waiting indicator (experts being selected / familiarising) -->
							{#if isWaitingForFirstContributions}
								<div class="flex items-center gap-3 py-4 px-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800" transition:fade={{ duration: 300 }}>
									<div class="flex items-center gap-1">
										<span class="w-2 h-2 bg-amber-500 dark:bg-amber-400 rounded-full animate-bounce" style="animation-delay: 0ms;"></span>
										<span class="w-2 h-2 bg-amber-500 dark:bg-amber-400 rounded-full animate-bounce" style="animation-delay: 150ms;"></span>
										<span class="w-2 h-2 bg-amber-500 dark:bg-amber-400 rounded-full animate-bounce" style="animation-delay: 300ms;"></span>
									</div>
									<span class="text-sm text-amber-700 dark:text-amber-300 font-medium">
										{phaseWaitingMessage}
									</span>
								</div>
							{/if}

							{#if isSynthesizing}
								<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800" transition:fade={{ duration: 300 }}>
									<div class="flex items-center gap-3 mb-3">
										<!-- Heartbeat animation -->
										<div class="relative">
											<div class="w-5 h-5 bg-blue-600 rounded-full animate-ping absolute"></div>
											<div class="w-5 h-5 bg-blue-600 rounded-full relative"></div>
										</div>
										<h3 class="text-lg font-semibold text-blue-900 dark:text-blue-100">
											Synthesizing Recommendations...
											<span class="text-sm font-normal text-blue-700 dark:text-blue-300">
												({elapsedSeconds}s)
											</span>
										</h3>
									</div>

									<!-- Multi-step progress indicator -->
									<div class="mt-4 space-y-3">
										<div class="flex items-center gap-3 text-sm">
											<svg class="w-5 h-5 text-green-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
											</svg>
											<span class="text-blue-800 dark:text-blue-200">
												Analyzed {events.filter(e => e.event_type === 'persona_vote').length || events.filter(e => e.event_type === 'contribution').length} expert perspectives
											</span>
										</div>
										<div class="flex items-center gap-3 text-sm {elapsedSeconds > 15 ? 'opacity-100' : 'opacity-50'}">
											{#if elapsedSeconds > 15}
												<svg class="w-5 h-5 text-green-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
												</svg>
											{:else}
												<svg class="w-5 h-5 text-blue-600 flex-shrink-0 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
													<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
												</svg>
											{/if}
											<span class="text-blue-700 dark:text-blue-300">
												Identifying consensus patterns and key insights
											</span>
										</div>
										<div class="flex items-center gap-3 text-sm {elapsedSeconds > 30 ? 'opacity-100' : 'opacity-50'}">
											{#if elapsedSeconds > 30}
												<svg class="w-5 h-5 text-blue-600 flex-shrink-0 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
													<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
												</svg>
											{:else}
												<svg class="w-5 h-5 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"></circle>
												</svg>
											{/if}
											<span class="text-blue-600 dark:text-blue-400 {elapsedSeconds > 30 ? '' : 'opacity-50'}">
												Generating comprehensive recommendation report
											</span>
										</div>
									</div>
								</div>
							{/if}

							{#if isVoting}
								<div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-6 border border-purple-200 dark:border-purple-800" transition:fade={{ duration: 300 }}>
									<div class="flex items-center gap-3 mb-3">
										<!-- Heartbeat animation -->
										<div class="relative">
											<div class="w-5 h-5 bg-purple-600 rounded-full animate-ping absolute"></div>
											<div class="w-5 h-5 bg-purple-600 rounded-full relative"></div>
										</div>
										<h3 class="text-lg font-semibold text-purple-900 dark:text-purple-100">
											Collecting Expert Recommendations...
											<span class="text-sm font-normal text-purple-700 dark:text-purple-300">
												({elapsedSeconds}s)
											</span>
										</h3>
									</div>
									<p class="text-sm text-purple-700 dark:text-purple-300">
										Experts are providing their final recommendations.
									</p>
								</div>
							{/if}

							{#each groupedEvents as group, index (index)}
								{#if group.type === 'expert_panel' && group.events}
									<!-- Render grouped expert panel -->
									<div transition:fade={{ duration: 300, delay: 50 }}>
										{#await getComponentForEvent('expert_panel')}
											<!-- Loading skeleton with timeout fallback -->
											<ExpertPanelSkeleton expertCount={group.events?.length || 4} />
										{:then ExpertPanelComponent}
											{#if ExpertPanelComponent}
												<ExpertPanelComponent
													experts={group.events.map((e) => ({
														persona: e.data.persona as any,
														rationale: e.data.rationale as string,
														order: e.data.order as number,
													}))}
													subProblemGoal={group.subProblemGoal}
												/>
											{:else}
												<!-- Component loaded but null - use GenericEvent -->
												<GenericEvent event={group.events[0]} />
												<div class="text-xs text-red-600 mt-2">
													Component failed to load for: expert_panel
												</div>
											{/if}
										{:catch error}
											<!-- Component import failed - show error with details -->
											<GenericEvent event={group.events[0]} />
											<div class="text-xs text-red-600 mt-2">
												Error loading component: {error.message || 'Unknown error'}
											</div>
										{/await}
									</div>
								{:else if group.type === 'round' && group.events}
									<!-- Render grouped contributions with new ExpertPerspectiveCard -->
									{@const roundKey = `round-${group.roundNumber}`}
									{@const visibleCount = visibleContributionCounts.get(roundKey) || 0}
									{@const hasMoreToReveal = visibleCount < group.events.length}
									{@const nextExpert = hasMoreToReveal ? group.events[visibleCount]?.data?.persona_name as string : null}
									<div transition:fade={{ duration: 300, delay: 50 }}>
										<div class="space-y-3">
											<h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
												<span>Round {group.roundNumber} Contributions</span>
											</h3>
											{#each getVisibleContributions(group.roundNumber, group.events) as contrib}
												{#await getComponentForEvent('contribution')}
													<!-- Loading skeleton with timeout fallback -->
													<ContributionSkeleton />
												{:then ExpertPerspectiveCardComponent}
													{#if ExpertPerspectiveCardComponent}
														{@const cardId = `${(contrib.data as any).persona_code}-${(contrib.data as any).round}`}
														<ExpertPerspectiveCardComponent
															event={contrib as any}
															viewMode={getCardViewMode(cardId)}
															showFull={showFullTranscripts}
															onToggle={() => toggleCardViewMode(cardId)}
														/>
													{:else}
														<!-- Component loaded but null - use GenericEvent -->
														<GenericEvent event={contrib} />
														<div class="text-xs text-red-600 mt-2">
															Component failed to load for: contribution
														</div>
													{/if}
												{:catch error}
													<!-- Component import failed - show error with details -->
													<GenericEvent event={contrib} />
													<div class="text-xs text-red-600 mt-2">
														Error loading component: {error.message || 'Unknown error'}
													</div>
												{/await}
											{/each}

											<!-- Thinking indicator when more contributions are pending -->
											{#if hasMoreToReveal && nextExpert}
												<div class="flex items-center gap-2 py-2 px-3 text-sm text-slate-500 dark:text-slate-400" transition:fade={{ duration: 200 }}>
													<!-- Pulsing dots animation like ChatGPT/Claude -->
													<div class="flex items-center gap-1">
														<span class="w-1.5 h-1.5 bg-slate-400 dark:bg-slate-500 rounded-full animate-pulse" style="animation-delay: 0ms;"></span>
														<span class="w-1.5 h-1.5 bg-slate-400 dark:bg-slate-500 rounded-full animate-pulse" style="animation-delay: 150ms;"></span>
														<span class="w-1.5 h-1.5 bg-slate-400 dark:bg-slate-500 rounded-full animate-pulse" style="animation-delay: 300ms;"></span>
													</div>
													<span class="italic">{getThinkingMessage(nextExpert, visibleCount)}</span>
												</div>
											{/if}
										</div>
									</div>
								{:else if group.type === 'single' && group.event}
									{@const event = group.event}
									{@const priority = getEventPriority(event.event_type)}
									{@const isMajorEvent = event.event_type === 'complete' || event.event_type === 'synthesis_complete' || event.event_type === 'meta_synthesis_complete'}
									<!-- Render single event with visual hierarchy -->
									<div
										class="{getEventCardClasses(priority)} rounded-lg p-4"
										in:fade|global={{ duration: 300, delay: 50 }}
										out:fade|global={{ duration: 200 }}
									>
										<div class="flex items-start gap-3">
											{#if event.event_type === 'synthesis_complete' || event.event_type === 'subproblem_complete' || event.event_type === 'meta_synthesis_complete' || event.event_type === 'complete'}
												<CheckCircle size={20} class="text-semantic-success" />
											{:else if event.event_type === 'error'}
												<AlertCircle size={20} class="text-semantic-error" />
											{/if}
											<div class="flex-1 min-w-0">
												<div class="flex items-center justify-between mb-3">
													<RelativeTimestamp timestamp={event.timestamp} />
												</div>

												<!-- Render appropriate component based on event type with dynamic loading -->
												{#await getComponentForEvent(event.event_type)}
													<!-- Loading skeleton with timeout fallback -->
													<EventCardSkeleton hasAvatar={false} />
												{:then EventComponent}
													{#if EventComponent}
														<EventComponent event={event as any} />
													{:else}
														<!-- Component loaded but null - use GenericEvent -->
														<GenericEvent event={event} />
														<div class="text-xs text-red-600 mt-2">
															Component failed to load for: {event.event_type}
														</div>
													{/if}
												{:catch error}
													<!-- Component import failed - show error with details -->
													<GenericEvent event={event} />
													<div class="text-xs text-red-600 mt-2">
														Error loading component: {error.message || 'Unknown error'}
													</div>
												{/await}
											</div>
										</div>
									</div>
								{/if}
							{/each}

							<!-- Between-rounds waiting indicator -->
							{#if isWaitingForNextRound}
								<div class="flex items-center gap-3 py-4 px-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800" transition:fade={{ duration: 300 }}>
									<div class="flex items-center gap-1">
										<span class="w-2 h-2 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0ms;"></span>
										<span class="w-2 h-2 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 150ms;"></span>
										<span class="w-2 h-2 bg-blue-500 dark:bg-blue-400 rounded-full animate-bounce" style="animation-delay: 300ms;"></span>
									</div>
									<span class="text-sm text-blue-700 dark:text-blue-300 font-medium">
										{betweenRoundsMessages[betweenRoundsMessageIndex]}
									</span>
								</div>
							{/if}
							</div>
						{/if}
					</div>
				</div>
			</div>

			<!-- Sidebar -->
			<div class="space-y-6 lg:self-stretch flex flex-col">
				<!-- Problem Statement - Collapsible -->
				{#if session}
					<details class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700" open>
						<summary class="cursor-pointer p-4 font-semibold text-slate-900 dark:text-white hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-t-lg transition-colors text-sm">
							Problem Statement
						</summary>
						<div class="px-4 pb-4">
							<p class="text-sm text-slate-700 dark:text-slate-300">
								{session.problem?.statement || 'Problem statement not available'}
							</p>
						</div>
					</details>

					<!-- Progress Indicator -->
					<ProgressIndicator
						events={events}
						currentPhase={session.phase}
						currentRound={session.round_number ?? null}
					/>

					<!-- Decision Metrics Dashboard -->
					<div class="flex-1">
						<DecisionMetrics
							events={events}
							currentPhase={session.phase}
							currentRound={session.round_number ?? null}
							activeSubProblemIndex={activeSubProblemTab ? parseInt(activeSubProblemTab.replace('subproblem-', '')) : null}
							totalSubProblems={subProblemTabs.length}
						/>
					</div>



					<!-- Actions -->
					{#if session.status === 'completed'}
						<a href="/meeting/{sessionId}/results" class="block w-full">
							<Button variant="brand" size="lg" class="w-full">
								{#snippet children()}
									View Results
								{/snippet}
							</Button>
						</a>
					{/if}
				{/if}
			</div>
		</div>
	</main>
</div>
