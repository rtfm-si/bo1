<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { apiClient } from '$lib/api/client';
	import type { SSEEvent } from '$lib/api/sse-events';

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
	} from '$lib/components/events';

	const sessionId: string = $page.params.id!; // SvelteKit guarantees this exists due to [id] route

	interface SessionData {
		id: string;
		problem_statement: string;
		status: string;
		phase: string | null;
		round_number?: number; // Optional since it may not exist yet
		created_at: string;
	}

	let session = $state<SessionData | null>(null);
	let events = $state<SSEEvent[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let eventSource: EventSource | null = null;
	let autoScroll = $state(true);
	let retryCount = $state(0);
	let maxRetries = 3;
	let connectionStatus = $state<'connecting' | 'connected' | 'error' | 'retrying'>('connecting');

	// Helper function to add events safely (avoids state mutation in reactive context)
	function addEvent(newEvent: SSEEvent) {
		events = [...events, newEvent];
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
			if (autoScroll) {
				setTimeout(() => {
					const container = document.getElementById('events-container');
					if (container) {
						container.scrollTop = container.scrollHeight;
					}
				}, 100);
			}
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

				// Auto-scroll to bottom
				if (autoScroll) {
					setTimeout(() => {
						const container = document.getElementById('events-container');
						if (container) {
							container.scrollTop = container.scrollHeight;
						}
					}, 100);
				}

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
			eventSource?.close();

			if (retryCount < maxRetries) {
				retryCount++;
				connectionStatus = 'retrying';
				const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 5000);
				console.log(`[SSE] Retrying in ${delay}ms...`);

				setTimeout(() => {
					startEventStream();
				}, delay);
			} else {
				console.error('[SSE] Max retries reached, giving up');
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
					<div>
						<h1 class="text-xl font-bold text-slate-900 dark:text-white">
							Meeting in Progress
						</h1>
						{#if session}
							<p class="text-sm text-slate-600 dark:text-slate-400">
								{session.phase ? session.phase.replace(/_/g, ' ') : 'Initializing'} - Round {session.round_number}
							</p>
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
							<div class="flex items-center justify-center h-full">
								<svg class="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
							</div>
						{:else if events.length === 0}
							<div class="flex items-center justify-center h-full text-slate-500 dark:text-slate-400">
								<p>Waiting for deliberation to start...</p>
							</div>
						{:else}
							{#each events as event (event.timestamp + event.event_type)}
								<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
									<div class="flex items-start gap-3">
										<span class="text-2xl">{getEventIcon(event.event_type)}</span>
										<div class="flex-1 min-w-0">
											<div class="flex items-center justify-between mb-3">
												<span class="text-xs text-slate-500 dark:text-slate-400">
													{formatTimestamp(event.timestamp)}
												</span>
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
							{/each}
						{/if}
					</div>
				</div>
			</div>

			<!-- Sidebar -->
			<div class="space-y-6">
				<!-- Problem Statement -->
				{#if session}
					<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-6">
						<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-3">
							Problem Statement
						</h3>
						<p class="text-sm text-slate-700 dark:text-slate-300">
							{session.problem_statement}
						</p>
					</div>

					<!-- Status Card -->
					<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-6">
						<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
							Status
						</h3>
						<dl class="space-y-3 text-sm">
							<div>
								<dt class="text-slate-600 dark:text-slate-400">Status</dt>
								<dd class="font-medium text-slate-900 dark:text-white mt-1">
									{session.status.toUpperCase()}
								</dd>
							</div>
							<div>
								<dt class="text-slate-600 dark:text-slate-400">Phase</dt>
								<dd class="font-medium text-slate-900 dark:text-white mt-1">
									{session.phase ? session.phase.replace(/_/g, ' ') : 'Initializing'}
								</dd>
							</div>
							<div>
								<dt class="text-slate-600 dark:text-slate-400">Round</dt>
								<dd class="font-medium text-slate-900 dark:text-white mt-1">
									{session.round_number}
								</dd>
							</div>
						</dl>
					</div>

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
