<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { page } from '$app/stores';
	import { env } from '$env/dynamic/public';
	import { apiClient } from '$lib/api/client';
	import type { SSEEvent, ContributionEvent, ExpertInfo } from '$lib/api/sse-events';
	import { fade } from 'svelte/transition';
	import { SSEClient } from '$lib/utils/sse';
	import { CheckCircle, AlertCircle, Download } from 'lucide-svelte';
	import { user } from '$lib/stores/auth';
	import { generateReportHTML } from '$lib/utils/pdf-report-generator';

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

	// Import DynamicEventComponent (reusable wrapper for dynamic event component loading)
	import DynamicEventComponent from '$lib/components/events/DynamicEventComponent.svelte';
	import ContributionRound from '$lib/components/events/ContributionRound.svelte';


	// Import UI components
	import {
		RelativeTimestamp,
		DecisionMetrics,
		Button,
	} from '$lib/components/ui';
	import AiDisclaimer from '$lib/components/ui/AiDisclaimer.svelte';
	import {
		EventCardSkeleton,
	} from '$lib/components/ui/skeletons';
	import { ActivityStatus } from '$lib/components/ui/loading';

	// Import meeting components
	import MeetingHeader from '$lib/components/meeting/MeetingHeader.svelte';
	import WorkingStatusBanner from '$lib/components/meeting/WorkingStatusBanner.svelte';
	import MeetingProgress from '$lib/components/meeting/MeetingProgress.svelte';
	import SubProblemTabs from '$lib/components/meeting/SubProblemTabs.svelte';
	import EventStream from '$lib/components/meeting/EventStream.svelte';

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

	// AUDIT FIX (Issue #4): Working status tracking for prominent UI feedback
	let currentWorkingPhase = $state<string | null>(null);
	let workingStatusStartTime = $state<number | null>(null);
	let workingElapsedSeconds = $state(0);
	let estimatedDuration = $state<string | undefined>(undefined);

	// Track working status updates
	$effect(() => {
		if (currentWorkingPhase) {
			workingStatusStartTime = Date.now();
			const interval = setInterval(() => {
				if (workingStatusStartTime) {
					workingElapsedSeconds = Math.floor((Date.now() - workingStatusStartTime) / 1000);
				}
			}, 1000);
			return () => clearInterval(interval);
		} else {
			workingStatusStartTime = null;
			workingElapsedSeconds = 0;
		}
	});

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

	// CLIENT-SIDE STALENESS DETECTION
	// Shows a "Still working..." banner when UI hasn't updated for a while
	// This catches gaps between backend working_status events
	const STALENESS_THRESHOLD_MS = 8000; // Show banner after 8s of no events
	let lastEventReceivedTime = $state<number>(Date.now());
	let staleSinceSeconds = $state<number>(0);
	let isStale = $state<boolean>(false);

	// Update staleness every second
	$effect(() => {
		// Only track staleness for active sessions
		if (session?.status !== 'active') {
			isStale = false;
			staleSinceSeconds = 0;
			return;
		}

		const interval = setInterval(() => {
			const timeSince = Date.now() - lastEventReceivedTime;
			if (timeSince >= STALENESS_THRESHOLD_MS) {
				isStale = true;
				staleSinceSeconds = Math.floor(timeSince / 1000);
			} else {
				isStale = false;
				staleSinceSeconds = 0;
			}
		}, 1000);

		return () => clearInterval(interval);
	});

	// Reset staleness when new events arrive (handled in addEvent below)
	function resetStaleness() {
		lastEventReceivedTime = Date.now();
		isStale = false;
		staleSinceSeconds = 0;
	}

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
		// Filter out cost events for non-admin users
		if (newEvent.event_type === 'phase_cost_breakdown' && !$user?.is_admin) {
			return;
		}

		// Only reset staleness for VISIBLE events (events the user will actually see)
		// This ensures "Still working..." banner shows when backend is busy
		// but not producing user-visible updates
		resetStaleness();

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
			for (const event of response.events as SSEEvent[]) {
				const sseEvent: SSEEvent = {
					event_type: event.event_type,
					session_id: event.session_id,
					timestamp: event.timestamp,
					data: event.data
				};
				addEvent(sseEvent);
			}

			// For completed meetings, scroll to top (show beginning)
			// For active meetings, scroll to bottom (latest events)
			if (session?.status === 'completed' || session?.status === 'failed') {
				// Don't auto-scroll for completed meetings - let user read from start
				const container = document.getElementById('events-container');
				if (container) {
					container.scrollTop = 0;
				}
			} else {
				// Auto-scroll after loading history for active meetings
				scrollToLatestEventDebounced(false); // No smooth scroll for initial load
			}
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

				// AUDIT FIX (Issue #4): Handle working_status events
				if (eventType === 'working_status') {
					currentWorkingPhase = payload.phase || null;
					estimatedDuration = payload.estimated_duration || undefined;
					workingElapsedSeconds = 0; // Reset elapsed time for new phase
					console.log('[WORKING STATUS]', payload.phase, estimatedDuration);
					return; // Don't add to event stream, just update UI state
				}

				// Clear working status when other significant events arrive
				if (['contribution', 'convergence', 'voting_complete', 'synthesis_complete', 'meta_synthesis_complete', 'subproblem_complete'].includes(eventType)) {
					currentWorkingPhase = null;
				}

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

				// Force immediate grouping for critical events (bypass debounce)
				// This ensures expert panels and round markers appear instantly without waiting for next event
				if (eventType === 'persona_selection_complete' || eventType === 'persona_selected' || eventType === 'round_started') {
					// Cancel any pending debounced recalculation to prevent race condition
					if (debounceTimeout) clearTimeout(debounceTimeout);
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
			'working_status', // AUDIT FIX (Issue #4): Add working status events
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
			// For completed meetings, process immediately (no debounce)
			const isCompleted = session?.status === 'completed' || session?.status === 'failed';
			if (isCompleted) {
				groupedEventsCache = groupEvents(events, debugMode);
				lastEventCountForGrouping = events.length;
				return;
			}

			const lastEvent = events[events.length - 1];

			// Critical events get fastest rendering (50ms)
			const isCritical = lastEvent?.event_type === 'persona_selection_complete'
				|| lastEvent?.event_type === 'round_started'
				|| lastEvent?.event_type === 'persona_selected';

			const delay = isCritical ? DEBOUNCE_CRITICAL : DEBOUNCE_NORMAL;

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

	// Generate varied thinking messages (passed to ContributionRound component)
	const thinkingMessages = [
		(name: string) => `${name} is thinking...`,
		(name: string) => `${name} is formulating a response...`,
		(name: string) => `${name} wants to contribute...`,
		(name: string) => `${name} is considering the discussion...`,
		(name: string) => `${name} is preparing insights...`,
	];

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
		// For completed meetings, show all contributions immediately (no animation)
		const isCompleted = session?.status === 'completed' || session?.status === 'failed';

		for (const group of groupedEvents) {
			if (group.type === 'round' && group.events) {
				const roundKey = `round-${group.roundNumber}`;
				const currentVisible = visibleContributionCounts.get(roundKey) || 0;
				const totalContributions = group.events.length;

				// If we have new contributions to reveal
				if (currentVisible < totalContributions) {
					// For completed meetings, reveal all immediately
					if (isCompleted) {
						visibleContributionCounts.set(roundKey, totalContributions);
						visibleContributionCounts = new Map(visibleContributionCounts);
						continue;
					}

					// Calculate how many we need to reveal
					const toReveal = totalContributions - currentVisible;

					// Update pending experts list
					const newPending = group.events.slice(currentVisible).map(e => {
						const contribEvent = e as ContributionEvent;
						return {
							name: contribEvent.data.persona_name || 'Expert',
							roundKey
						};
					});
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
			// For completed meetings, process immediately (no debounce)
			const isCompleted = session?.status === 'completed' || session?.status === 'failed';
			if (isCompleted) {
				eventsBySubProblemCache = indexEventsBySubProblem(events);
				lastEventCountForIndex = events.length;
				return;
			}
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
	// Used in tabbed sub-problem view
	function getEventCardClasses(priority: EventPriority): string {
		if (priority === 'major') {
			return 'bg-neutral-50 dark:bg-neutral-900/50 border-2 border-neutral-300 dark:border-neutral-700';
		}
		if (priority === 'meta') {
			return 'bg-neutral-50/50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700';
		}
		return 'bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700';
	}

	// Auto-switch to Summary tab when meeting completes
	$effect(() => {
		if (session?.status === 'completed' && showConclusionTab && activeSubProblemTab !== 'conclusion') {
			activeSubProblemTab = 'conclusion';
		}
	});

	// PDF Export functionality
	let isExporting = $state(false);

	async function exportPDF() {
		isExporting = true;
		try {
			// Open print-friendly report in new window
			const reportWindow = window.open('', '_blank', 'width=800,height=600');
			if (!reportWindow) {
				alert('Please allow popups to export the report');
				return;
			}

			if (!session) {
				alert('Session data not loaded');
				return;
			}

			const reportHTML = generateReportHTML({
				session,
				events,
				sessionId
			});
			reportWindow.document.write(reportHTML);
			reportWindow.document.close();

			// Trigger print dialog after a brief delay for styles to load
			setTimeout(() => {
				reportWindow.print();
			}, 500);
		} finally {
			isExporting = false;
		}
	}

	// PDF report generation has been extracted to $lib/utils/pdf-report-generator.ts
</script>

<svelte:head>
	<title>Meeting {sessionId} - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<MeetingHeader
		{sessionId}
		sessionStatus={session?.status}
		onPause={handlePause}
		onResume={handleResume}
	/>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Working Status Banner -->
		<WorkingStatusBanner
			{currentWorkingPhase}
			{workingElapsedSeconds}
			{estimatedDuration}
			{isStale}
			staleSinceSeconds={staleSinceSeconds}
			sessionStatus={session?.status}
		/>

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
					Meeting complete
				{:else if latestEvent.event_type === 'voting_complete'}
					Voting complete
				{:else if latestEvent.event_type === 'subproblem_complete'}
					Focus area complete
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
										Focus Area Analysis
									{:else}
										Activity
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
						<MeetingProgress {session} />
					</div>

					<div
						id="events-container"
						class="overflow-y-auto"
						style="height: calc(100vh - 400px); min-height: 600px; overflow-anchor: none;"
					>
						{#if isLoading}
							<!-- Skeleton Loading States -->
							<div class="space-y-4 p-4">
								{#each Array(5) as _, i}
									<EventCardSkeleton />
								{/each}
							</div>
						{:else if events.length === 0}
							<div class="flex flex-col items-center justify-center h-full text-slate-500 dark:text-slate-400 p-4">
								<ActivityStatus
									variant="card"
									message={initialWaitingMessages[initialWaitingMessageIndex]}
									showDots
								/>
							</div>
						{:else if subProblemTabs.length > 1}
							<!-- Tab-based navigation for multiple sub-problems -->
							<div class="h-full flex flex-col">
								<SubProblemTabs
									{subProblemTabs}
									{showConclusionTab}
									{activeSubProblemTab}
									onTabChange={(tabId) => activeSubProblemTab = tabId}
								/>

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
													<DynamicEventComponent
														event={group.events[0]}
														eventType="expert_panel"
														skeletonProps={{ hasAvatar: false }}
														componentProps={{
															experts: group.events.map((e): ExpertInfo => ({
																persona: e.data.persona as {
																	code: string;
																	name: string;
																	display_name: string;
																	archetype: string;
																	domain_expertise: string[];
																},
																rationale: e.data.rationale as string,
																order: e.data.order as number,
															})),
															subProblemGoal: group.subProblemGoal
														}}
													/>
												</div>
											{:else if group.type === 'round' && group.events}
												{@const roundKey = `round-${group.roundNumber}`}
												{@const visibleCount = visibleContributionCounts.get(roundKey) || 0}
												<ContributionRound
													roundNumber={group.roundNumber || 0}
													events={group.events}
													visibleCount={visibleCount}
													viewMode={contributionViewMode}
													showFullTranscripts={showFullTranscripts}
													cardViewModes={cardViewModes}
													onToggleCardViewMode={toggleCardViewMode}
													thinkingMessages={thinkingMessages}
												/>
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

															<DynamicEventComponent
																{event}
																skeletonProps={{ hasAvatar: false }}
															/>
														</div>
													</div>
												</div>
											{/if}
										{/each}

										<!-- Synthesis preview for this sub-problem (if available) -->
										{#if subProblemCompleteEvents[tabIndex]?.data?.synthesis}
											<div class="mt-8 border-t border-slate-200 dark:border-slate-700 pt-6">
												<DynamicEventComponent
													event={subProblemCompleteEvents[tabIndex]}
													eventType="subproblem_complete"
												/>
											</div>
										{/if}

										<!-- Phase-specific waiting indicator (tabbed view) -->
										{#if isWaitingForFirstContributions && isTabActive}
											<div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800 py-4 px-4" transition:fade={{ duration: 300 }}>
												<ActivityStatus
													variant="inline"
													message={phaseWaitingMessage}
													class="text-amber-700 dark:text-amber-300 font-medium"
												/>
											</div>
										{/if}

										<!-- Between-rounds waiting indicator (tabbed view) -->
										{#if isWaitingForNextRound && isTabActive}
											<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 py-4 px-4" transition:fade={{ duration: 300 }}>
												<ActivityStatus
													variant="inline"
													message={betweenRoundsMessages[betweenRoundsMessageIndex]}
													class="text-blue-700 dark:text-blue-300 font-medium"
												/>
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
											<DynamicEventComponent
												event={decompositionEvent}
												eventType="decomposition_complete"
											/>
										{/if}

										<!-- Progress indicator for multi-problem meetings -->
										{#if subProblemCompleteEvents.length > 0 && !metaSynthesisEvent && subProblemTabs.length > 1}
											<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4 mb-6">
												<ActivityStatus
													variant="inline"
													message="Generating final synthesis..."
													phase="{subProblemCompleteEvents.length} of {subProblemTabs.length} focus areas completed"
													class="text-blue-900 dark:text-blue-100"
												/>
											</div>
										{/if}

										<!-- Meta-Synthesis / Overall Conclusion -->
										{#if metaSynthesisEvent}
											<!-- Use SynthesisComplete component for proper XML parsing and card rendering -->
											<DynamicEventComponent
												event={metaSynthesisEvent}
												eventType="synthesis_complete"
											/>
										{:else if synthesisCompleteEvent}
											<!-- Use SynthesisComplete component for proper XML parsing and card rendering -->
											<DynamicEventComponent
												event={synthesisCompleteEvent}
												eventType="synthesis_complete"
											/>
										{:else if subProblemCompleteEvents.length > 0 && subProblemCompleteEvents.some(e => e.data.synthesis)}
											<!-- Show individual sub-problem syntheses using SubProblemProgress component -->
											<div class="space-y-6">
												<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">Sub-Problem Syntheses</h3>
												{#each subProblemCompleteEvents.filter(e => e.data.synthesis) as spEvent}
													<DynamicEventComponent
														event={spEvent}
														eventType="subproblem_complete"
													/>
												{/each}
											</div>
										{:else}
											<!-- Fallback: Meeting complete but no synthesis yet -->
											<div class="text-center py-12">
												{#if session?.status === 'running' || session?.status === 'created' || session?.status === 'active'}
													<ActivityStatus
														variant="card"
														message="Experts deliberating..."
														phase="The final synthesis will appear here when complete"
													/>
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
									</div>
								{/if}
							</div>
						{:else}
							<!-- Single sub-problem or linear view -->
							<EventStream
								{events}
								{groupedEvents}
								{session}
								{isLoading}
								{visibleContributionCounts}
								{contributionViewMode}
								{showFullTranscripts}
								{cardViewModes}
								{thinkingMessages}
								{isWaitingForFirstContributions}
								{phaseWaitingMessage}
								{isWaitingForNextRound}
								{betweenRoundsMessages}
								{betweenRoundsMessageIndex}
								{initialWaitingMessages}
								{initialWaitingMessageIndex}
								{isSynthesizing}
								{isVoting}
								{elapsedSeconds}
								{votingStartTime}
								{isTransitioningSubProblem}
								onToggleCardViewMode={toggleCardViewMode}
							/>
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
						<Button variant="brand" size="lg" class="w-full" onclick={exportPDF} disabled={isExporting}>
							{#snippet children()}
								<Download size={18} />
								<span>{isExporting ? 'Generating...' : 'Export PDF'}</span>
							{/snippet}
						</Button>
					{/if}
				{/if}
			</div>
		</div>

		<!-- Subtle AI disclaimer at bottom of page -->
		<AiDisclaimer class="mt-8" />
	</main>
</div>
