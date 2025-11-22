<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { apiClient } from '$lib/api/client';
	import type { SSEEvent } from '$lib/api/sse-events';
	import { fade, scale } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	// Import event components
	import {
		DecompositionComplete,
		PersonaSelection,
		PersonaContribution,
		FacilitatorDecision,
		ModeratorIntervention,
		ConvergenceCheck,
		VotingPhase,
		PersonaVote,
		SynthesisComplete,
		SubProblemProgress,
		PhaseTable,
		DeliberationComplete,
		ErrorEvent,
		GenericEvent,
		RoundGroup,
	} from '$lib/components/events';

	// Import UI components
	import { PhaseTimeline, RelativeTimestamp, DualProgress, DecisionMetrics } from '$lib/components/ui';

	// Import utilities
	import { getEventPriority, type EventPriority } from '$lib/utils/event-humanization';

	const sessionId: string = $page.params.id!; // SvelteKit guarantees this exists due to [id] route

	interface SessionData {
		id: string;
		problem_statement: string;
		status: string;
		phase: string | null;
		round_number?: number; // Optional since it may not exist yet
		created_at: string;
	}

	// Constants for internal event filtering
	const INTERNAL_EVENTS = ['node_start', 'node_end'];

	let session = $state<SessionData | null>(null);
	let events = $state<SSEEvent[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let eventSource: EventSource | null = null;
	let autoScroll = $state(true);
	let retryCount = $state(0);
	let maxRetries = 3;
	let connectionStatus = $state<'connecting' | 'connected' | 'error' | 'retrying'>('connecting');

	// Track seen events for deduplication
	let seenEventKeys = $state(new Set<string>());

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

	// Filter function to hide internal events (unless debug mode)
	function shouldShowEvent(eventType: string): boolean {
		return !INTERNAL_EVENTS.includes(eventType) || debugMode;
	}

	// Helper function to add events safely with deduplication
	function addEvent(newEvent: SSEEvent) {
		// Create unique key from timestamp + event_type + relevant data
		const eventKey = `${newEvent.timestamp}-${newEvent.event_type}-${
			newEvent.data.persona_code ||
			newEvent.data.sub_problem_id ||
			newEvent.data.round_number ||
			''
		}`;

		// Skip if already seen
		if (seenEventKeys.has(eventKey)) {
			console.debug('[Events] Skipping duplicate event:', eventKey);
			return;
		}

		seenEventKeys.add(eventKey);
		events = [...events, newEvent];
	}

	// Helper functions for phase display
	function getPhaseEmoji(phase: string | null): string {
		if (!phase) return '⏳';
		const emojis: Record<string, string> = {
			decomposition: '🔍',
			persona_selection: '👥',
			initial_round: '💭',
			discussion: '💬',
			voting: '🗳️',
			synthesis: '⚙️',
			complete: '✅',
		};
		return emojis[phase] || '⏳';
	}

	function formatPhase(phase: string | null): string {
		if (!phase) return 'Initializing';
		return phase
			.split('_')
			.map(word => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}

	onMount(() => {
		const unsubscribe = isAuthenticated.subscribe((authenticated) => {
			if (!authenticated) {
				goto('/login');
			}
		});

		// Run async initialization
		(async () => {
			await loadSession();
			await loadHistoricalEvents(); // Load history FIRST
			startEventStream(); // THEN connect to stream
		})();

		return unsubscribe;
	});

	onDestroy(() => {
		if (eventSource) {
			eventSource.close();
		}
	});

	async function loadSession() {
		try {
			session = await apiClient.getSession(sessionId);
			isLoading = false;
		} catch (err) {
			console.error('Failed to load session:', err);
			error = err instanceof Error ? err.message : 'Failed to load session';
			isLoading = false;
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
			scrollToLatestEvent(false); // No smooth scroll for initial load
		} catch (err) {
			console.error('[Events] Failed to load historical events:', err);
			// Don't set error state - this is non-fatal, stream will still work
		}
	}

	function startEventStream() {
		// Close existing connection if any
		if (eventSource) {
			eventSource.close();
		}

		// Connect through SvelteKit proxy to handle authentication cookies
		eventSource = new EventSource(`/api/v1/sessions/${sessionId}/stream`);

		eventSource.onopen = () => {
			console.log('[SSE] Connection established');
			retryCount = 0;
			connectionStatus = 'connected';
		};

		// Helper to handle SSE events (converts SSE format to SSEEvent)
		const handleSSEEvent = (eventType: string, event: MessageEvent) => {
			try {
				// Parse the data payload
				const payload = JSON.parse(event.data);

				// Construct SSEEvent by adding event_type from SSE event name
				const sseEvent: SSEEvent = {
					event_type: eventType,
					session_id: payload.session_id || sessionId,
					timestamp: payload.timestamp || new Date().toISOString(),
					data: payload
				};

				addEvent(sseEvent);

				// Auto-scroll to bottom with smooth animation
				scrollToLatestEvent(true);

				// Update session status on complete
				if (eventType === 'complete' && session) {
					session.status = 'completed';
				}
			} catch (err) {
				console.error(`Failed to parse ${eventType} event:`, err);
			}
		};

		// Listen for specific event types (SSE named events)
		// IMPORTANT: We only use addEventListener, NOT onmessage (to avoid duplicates)
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
			'facilitator_decision',
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

		eventTypes.forEach((eventType) => {
			eventSource?.addEventListener(eventType, (event: MessageEvent) => {
				handleSSEEvent(eventType, event);
			});
		});

		eventSource.onerror = (event) => {
			console.error('[SSE] Connection error, retry count:', retryCount);

			// Close existing connection
			eventSource?.close();

			// Don't try to parse event.data - SSE error events don't have data

			if (retryCount < maxRetries) {
				retryCount++;
				connectionStatus = 'retrying';
				const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 5000);
				console.log(`[SSE] Retrying in ${delay}ms...`);

				setTimeout(() => {
					startEventStream();
				}, delay);
			} else {
				console.error('[SSE] Max retries reached');
				connectionStatus = 'error';
				error = 'Failed to connect to session stream. Please refresh the page.';
			}
		};
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
			eventSource?.close();
		} catch (err) {
			console.error('Failed to kill session:', err);
		}
	}

	function getEventIcon(type: string): string {
		const icons: Record<string, string> = {
			session_started: '🚀',
			decomposition_started: '🔍',
			decomposition_complete: '📋',
			persona_selection_started: '👥',
			persona_selected: '👤',
			persona_selection_complete: '✅',
			subproblem_started: '🎯',
			initial_round_started: '💭',
			contribution: '💬',
			facilitator_decision: '⚖️',
			moderator_intervention: '⚡',
			convergence: '📊',
			round_started: '🔄',
			voting_started: '🗳️',
			persona_vote: '✍️',
			voting_complete: '📝',
			synthesis_started: '⚙️',
			synthesis_complete: '✨',
			subproblem_complete: '✅',
			meta_synthesis_started: '🔮',
			meta_synthesis_complete: '🎉',
			phase_cost_breakdown: '💰',
			complete: '🎊',
			error: '❌',
			clarification_requested: '❓',
		};
		return icons[type] || 'ℹ️';
	}

	function formatTimestamp(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleTimeString();
	}

	// Improved auto-scroll function
	function scrollToLatestEvent(smooth = true) {
		if (!autoScroll) return;

		setTimeout(() => {
			const container = document.getElementById('events-container');
			if (container) {
				container.scrollTo({
					top: container.scrollHeight,
					behavior: smooth ? 'smooth' : 'auto',
				});
			}
		}, 100);
	}

	// Event grouping: Group contributions by round
	interface EventGroup {
		type: 'single' | 'round';
		event?: SSEEvent;
		events?: SSEEvent[];
		roundNumber?: number;
	}

	const groupedEvents = $derived.by(() => {
		const filtered = events.filter(e => shouldShowEvent(e.event_type));
		const groups: EventGroup[] = [];
		let currentRound: SSEEvent[] = [];
		let currentRoundNumber = 1;
		let lastRoundEvent: SSEEvent | null = null;

		for (const event of filtered) {
			// Track round_started events to get round numbers
			if (event.event_type === 'round_started' || event.event_type === 'initial_round_started') {
				lastRoundEvent = event;
				if (event.data.round_number) {
					currentRoundNumber = event.data.round_number as number;
				}
			}

			if (event.event_type === 'contribution') {
				currentRound.push(event);
			} else {
				// Push accumulated contributions as a group
				if (currentRound.length > 0) {
					groups.push({
						type: 'round',
						events: currentRound,
						roundNumber: currentRoundNumber
					});
					currentRound = [];
				}
				// Add non-contribution event as single
				groups.push({ type: 'single', event });
			}
		}

		// Push remaining contributions
		if (currentRound.length > 0) {
			groups.push({
				type: 'round',
				events: currentRound,
				roundNumber: currentRoundNumber
			});
		}

		return groups;
	});

	// Progress calculation
	function calculateProgress(session: SessionData | null): number {
		if (!session) return 0;

		// Map phases to progress percentages
		const phaseProgress: Record<string, number> = {
			decomposition: 10,
			persona_selection: 20,
			initial_round: 35,
			discussion: 50,
			voting: 75,
			synthesis: 90,
			complete: 100,
		};

		const baseProgress = phaseProgress[session.phase || ''] || 0;

		// Add round-based progress within discussion phase
		if (session.phase === 'discussion' && session.round_number) {
			const roundProgress = Math.min((session.round_number / 10) * 25, 25);
			return Math.min(baseProgress + roundProgress, 100);
		}

		return baseProgress;
	}

	// Visual hierarchy: Get CSS classes based on event priority
	function getEventCardClasses(priority: EventPriority): string {
		if (priority === 'major') {
			return 'bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/30 dark:to-purple-900/30 border-2 border-blue-300 dark:border-blue-700 shadow-lg';
		}
		if (priority === 'meta') {
			return 'bg-slate-50/50 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-700';
		}
		return 'bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700';
	}
</script>

<svelte:head>
	<title>Meeting {sessionId} - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
	<!-- Header -->
	<header class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-10">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/dashboard"
						class="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors duration-200"
						aria-label="Back to dashboard"
					>
						<svg class="w-5 h-5 text-slate-600 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</a>
					<div class="flex-1">
						<h1 class="text-xl font-bold text-slate-900 dark:text-white">
							Meeting in Progress
						</h1>
						{#if session}
							<!-- Dual Progress Indicators -->
							{#if session.status !== 'completed'}
								<div class="mt-2 w-full max-w-2xl">
									<DualProgress
										currentSubProblem={1}
										totalSubProblems={1}
										currentPhase={session.phase}
										currentRound={session.round_number ?? null}
										maxRounds={10}
										contributionsReceived={events.filter(e =>
											e.event_type === 'contribution' &&
											session && e.data.round_number === session.round_number
										).length}
										expectedContributions={5}
									/>
								</div>
							{/if}
						{/if}
					</div>
				</div>

				<div class="flex items-center gap-2">
					{#if session?.status === 'active'}
						<button
							onclick={handlePause}
							class="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white text-sm font-medium rounded-lg transition-colors duration-200"
						>
							⏸ Pause
						</button>
					{:else if session?.status === 'paused'}
						<button
							onclick={handleResume}
							class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors duration-200"
						>
							▶ Resume
						</button>
					{/if}

					<button
						onclick={handleKill}
						class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors duration-200"
					>
						⏹ Stop
					</button>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Phase Timeline -->
		{#if session}
			<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-6 mb-6">
				<PhaseTimeline currentPhase={session.phase} />
			</div>
		{/if}

		<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
			<!-- Events Stream -->
			<div class="lg:col-span-2">
				<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700">
					<div class="border-b border-slate-200 dark:border-slate-700 p-4 flex items-center justify-between">
						<div class="flex items-center gap-3">
							<h2 class="text-lg font-semibold text-slate-900 dark:text-white">
								Deliberation Stream
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
								<span class="flex items-center gap-1.5 text-xs text-orange-600 dark:text-orange-400">
									<span class="inline-block w-2 h-2 bg-orange-500 rounded-full animate-pulse"></span>
									Retrying... ({retryCount}/{maxRetries})
								</span>
							{:else if connectionStatus === 'error'}
								<span class="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
									<span class="inline-block w-2 h-2 bg-red-500 rounded-full"></span>
									Connection Failed
								</span>
							{/if}
						</div>
						<label class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
							<input
								type="checkbox"
								bind:checked={autoScroll}
								class="rounded"
							/>
							Auto-scroll
						</label>
					</div>

					<div
						id="events-container"
						class="h-[600px] overflow-y-auto p-4 space-y-4"
					>
						{#if isLoading}
							<!-- Skeleton Loading States -->
							<div class="space-y-4">
								{#each Array(5) as _, i}
									<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 border border-slate-200 dark:border-slate-700 animate-pulse">
										<div class="flex items-start gap-3">
											<div class="w-10 h-10 bg-slate-200 dark:bg-slate-700 rounded-full"></div>
											<div class="flex-1 space-y-3">
												<div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4"></div>
												<div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
												<div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-5/6"></div>
											</div>
										</div>
									</div>
								{/each}
							</div>
						{:else if events.length === 0}
							<div class="flex items-center justify-center h-full text-slate-500 dark:text-slate-400">
								<p>Waiting for deliberation to start...</p>
							</div>
						{:else}
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
								{#if group.type === 'round' && group.events}
									<!-- Render grouped contributions as RoundGroup -->
									<div transition:fade={{ duration: 300, delay: 50 }}>
										<RoundGroup
											roundNumber={group.roundNumber || 1}
											contributions={group.events}
											isCurrentRound={index === groupedEvents.length - 1 && session?.phase === 'discussion'}
										/>
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
											<span class="text-2xl">{getEventIcon(event.event_type)}</span>
											<div class="flex-1 min-w-0">
												<div class="flex items-center justify-between mb-3">
													<RelativeTimestamp timestamp={event.timestamp} />
												</div>

												<!-- Render appropriate component based on event type -->
												{#if event.event_type === 'decomposition_complete' && event.data.sub_problems}
													<DecompositionComplete event={event as any} />
												{:else if event.event_type === 'persona_selected' && event.data.persona}
													<PersonaSelection event={event as any} />
												{:else if event.event_type === 'contribution' && event.data.persona_code}
													<PersonaContribution event={event as any} />
												{:else if event.event_type === 'facilitator_decision' && event.data.action}
													<FacilitatorDecision event={event as any} />
												{:else if event.event_type === 'moderator_intervention' && event.data.moderator_type}
													<ModeratorIntervention event={event as any} />
												{:else if event.event_type === 'convergence'}
													<ConvergenceCheck event={event as any} />
												{:else if event.event_type === 'voting_started'}
													<VotingPhase event={event as any} />
												{:else if event.event_type === 'persona_vote' && event.data.persona_code}
													<PersonaVote event={event as any} />
												{:else if (event.event_type === 'synthesis_complete' || event.event_type === 'meta_synthesis_complete') && event.data.synthesis}
													<SynthesisComplete event={event as any} />
												{:else if event.event_type === 'subproblem_complete' && event.data.sub_problem_index !== undefined}
													<SubProblemProgress event={event as any} />
												{:else if event.event_type === 'phase_cost_breakdown' && event.data.phase_costs}
													<PhaseTable event={event as any} />
												{:else if event.event_type === 'complete' && event.data.total_cost !== undefined}
													<DeliberationComplete event={event as any} />
												{:else if event.event_type === 'error' && event.data.error}
													<ErrorEvent event={event as any} />
												{:else}
													<GenericEvent event={event} />
												{/if}
											</div>
										</div>
									</div>
								{/if}
							{/each}
						{/if}
					</div>
				</div>
			</div>

			<!-- Sidebar -->
			<div class="space-y-6">
				<!-- Problem Statement - Collapsible -->
				{#if session}
					<details class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700" open>
						<summary class="cursor-pointer p-4 font-semibold text-slate-900 dark:text-white hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-t-lg transition-colors text-sm">
							Problem Statement
						</summary>
						<div class="px-4 pb-4">
							<p class="text-sm text-slate-700 dark:text-slate-300">
								{session.problem_statement}
							</p>
						</div>
					</details>

					<!-- Decision Metrics Dashboard -->
					<DecisionMetrics
						events={events}
						currentPhase={session.phase}
						currentRound={session.round_number ?? null}
					/>

					<!-- Actions -->
					{#if session.status === 'completed'}
						<a
							href="/meeting/{sessionId}/results"
							class="block w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white text-center font-medium rounded-lg transition-colors duration-200"
						>
							View Results
						</a>
					{/if}
				{/if}
			</div>
		</div>
	</main>
</div>
