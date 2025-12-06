<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { page } from '$app/stores';
	import { apiClient } from '$lib/api/client';
	import type { SSEEvent, ExpertInfo } from '$lib/api/sse-events';
	import { fade } from 'svelte/transition';
	import { CheckCircle, AlertCircle, Download } from 'lucide-svelte';
	import { user } from '$lib/stores/auth';
	import { generateReportHTML } from '$lib/utils/pdf-report-generator';

	// Import DynamicEventComponent (reusable wrapper for dynamic event component loading)
	import DynamicEventComponent from '$lib/components/events/DynamicEventComponent.svelte';
	import ContributionRound from '$lib/components/events/ContributionRound.svelte';

	// Import UI components
	import { RelativeTimestamp, DecisionMetrics, Button } from '$lib/components/ui';
	import AiDisclaimer from '$lib/components/ui/AiDisclaimer.svelte';
	import { EventCardSkeleton } from '$lib/components/ui/skeletons';
	import { ActivityStatus } from '$lib/components/ui/loading';

	// Import meeting components
	import {
		MeetingHeader,
		WorkingStatusBanner,
		MeetingProgress,
		SubProblemTabs,
		EventStream,
		ClarificationForm,
		ContextInsufficientModal,
		ExpertSummariesPanel,
		ResearchPanel,
	} from '$lib/components/meeting';
	import type { ContextInsufficientEvent } from '$lib/api/sse-events';

	// Import utilities
	import { getEventPriority, type EventPriority } from '$lib/utils/event-humanization';
	import { HIDDEN_EVENT_TYPES, SSE_MAX_RETRIES } from '$lib/config/constants';

	// Import business logic modules
	import { createSessionStore, type SessionData } from './lib/sessionStore.svelte';
	import { groupEvents, type EventGroup } from './lib/eventGrouping';
	import { createSSEConnection, type SSEConnection } from './lib/sseConnection.svelte';
	import {
		createContributionReveal,
		THINKING_MESSAGES,
		INITIAL_WAITING_MESSAGES,
		BETWEEN_ROUNDS_MESSAGES,
	} from './lib/contributionReveal.svelte';
	import { createTimingState } from './lib/timingState.svelte';
	import { createMemoizedState } from './lib/memoizedState.svelte';
	import { createViewState } from './lib/viewState.svelte';
	import { createWaitingState } from './lib/waitingState.svelte';
	import { createEventDerivedState } from './lib/eventDerivedState.svelte';

	const sessionId: string = $page.params.id!;
	const debugMode = $derived($page.url.searchParams.has('debug'));
	const maxRetries = SSE_MAX_RETRIES;

	// ============================================================================
	// CREATE STORES
	// ============================================================================

	const store = createSessionStore();
	const revealManager = createContributionReveal();

	// Timing state
	const timing = createTimingState({
		getSession: () => store.session,
		getEvents: () => store.events,
	});

	// Memoized state (debounced calculations)
	const memoized = createMemoizedState({
		getEvents: () => store.events,
		getSession: () => store.session,
		debugMode,
	});

	// View state (tabs, view modes)
	const view = createViewState({
		getEventsBySubProblem: () => memoized.eventsBySubProblem,
	});

	// Event-derived state
	const eventState = createEventDerivedState({
		getEvents: () => store.events,
		getSession: () => store.session,
		getSubProblemTabsLength: () => memoized.subProblemTabs.length,
	});

	// Waiting state
	const waiting = createWaitingState({
		getSession: () => store.session,
		getEvents: () => store.events,
		getGroupedEvents: () => memoized.groupedEvents,
		getVisibleCount: (key) => revealManager.getVisibleCount(key),
		isSynthesizing: () => timing.isSynthesizing,
		isVoting: () => timing.isVoting,
	});

	// SSE connection (initialized in onMount)
	let sseConnection: SSEConnection | null = null;

	// ============================================================================
	// REACTIVE REFERENCES
	// ============================================================================

	let session = $derived(store.session);
	let events = $derived(store.events);
	let isLoading = $derived(store.isLoading);
	let error = $derived(store.error);
	let autoScroll = $state(true);
	let retryCount = $derived(store.retryCount);
	let connectionStatus = $derived(store.connectionStatus);

	// ============================================================================
	// EFFECTS
	// ============================================================================

	// Timer management
	$effect(() => {
		if (session?.status === 'active' || timing.currentWorkingPhase) {
			timing.startTimer();
		} else {
			timing.stopTimer();
		}
		return () => timing.stopTimer();
	});

	// Synthesis timing
	$effect(() => {
		if (timing.isSynthesizing) {
			timing.startSynthesisTiming();
			const interval = setInterval(() => timing.updateElapsedSeconds(), 1000);
			return () => clearInterval(interval);
		} else {
			timing.stopSynthesisTiming();
		}
	});

	// Voting timing
	$effect(() => {
		if (timing.isVoting) {
			timing.startVotingTiming();
			const interval = setInterval(() => timing.updateElapsedSeconds(), 1000);
			return () => clearInterval(interval);
		} else {
			timing.stopVotingTiming();
			if (!timing.isSynthesizing) {
				timing.stopSynthesisTiming();
			}
		}
	});

	// Memoized state updates
	$effect(() => {
		void events.length; // Track events changes
		memoized.updateAll();
	});

	// Tab initialization
	$effect(() => {
		view.initializeTab(memoized.subProblemTabs);
	});

	// Auto-switch to conclusion on completion
	$effect(() => {
		view.switchToConclusionIfCompleted(session?.status, eventState.showConclusionTab);
	});

	// Message cycling effects
	$effect(() => {
		if (events.length === 0) {
			revealManager.startInitialWaitingCycle();
		} else {
			revealManager.stopInitialWaitingCycle();
		}
		return () => revealManager.stopInitialWaitingCycle();
	});

	$effect(() => {
		if (waiting.isWaitingForNextRound) {
			revealManager.startBetweenRoundsCycle();
		} else {
			revealManager.stopBetweenRoundsCycle();
		}
		return () => revealManager.stopBetweenRoundsCycle();
	});

	// Process contribution reveals
	$effect(() => {
		const isCompleted = session?.status === 'completed' || session?.status === 'failed';
		revealManager.processGroups(memoized.groupedEvents, isCompleted);
	});

	// ============================================================================
	// EVENT HANDLING
	// ============================================================================

	function addEvent(newEvent: SSEEvent) {
		if (HIDDEN_EVENT_TYPES.has(newEvent.event_type)) return;
		if (newEvent.event_type === 'phase_cost_breakdown' && !$user?.is_admin) return;

		timing.resetStaleness();
		store.addEvent(newEvent);

		// Force immediate grouping for critical events
		if (
			newEvent.event_type === 'persona_selection_complete' ||
			newEvent.event_type === 'persona_selected' ||
			newEvent.event_type === 'round_started'
		) {
			memoized.forceGroupedEventsUpdate();
		}

		scrollToLatestEventDebounced(true);
	}

	// ============================================================================
	// SCROLL HANDLING
	// ============================================================================

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
		}, 300);
	};

	// ============================================================================
	// API HANDLERS
	// ============================================================================

	async function loadSession() {
		try {
			const sessionData = await apiClient.getSession(sessionId);
			const mappedSession = {
				id: sessionData.id,
				status: sessionData.status,
				phase: sessionData.phase,
				round_number: sessionData.round_number || sessionData.state?.round_number || undefined,
				created_at: sessionData.created_at,
				problem: sessionData.problem,
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

			for (const event of response.events as SSEEvent[]) {
				const sseEvent: SSEEvent = {
					event_type: event.event_type,
					session_id: event.session_id,
					timestamp: event.timestamp,
					data: event.data,
				};
				addEvent(sseEvent);
			}

			if (session?.status === 'completed' || session?.status === 'failed') {
				const container = document.getElementById('events-container');
				if (container) container.scrollTop = 0;
			} else {
				scrollToLatestEventDebounced(false);
			}
		} catch (err) {
			console.error('[Events] Failed to load historical events:', err);
		}
	}

	async function startEventStream() {
		if (!sseConnection) {
			sseConnection = createSSEConnection({
				sessionId,
				store,
				maxRetries,
				onEvent: addEvent,
				onWorkingStatus: (phase, duration) => timing.setWorkingStatus(phase, duration),
			});
		}
		await sseConnection.connect();
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
			await startEventStream();
		} catch (err) {
			console.error('Failed to resume session:', err);
		}
	}

	async function handleClarificationSubmitted() {
		await startEventStream();
	}

	async function handleContextChoiceMade() {
		// Reload session to get updated status
		await loadSession();
		// Restart event stream to continue receiving events
		await startEventStream();
	}

	// ============================================================================
	// PDF EXPORT
	// ============================================================================

	let isExporting = $state(false);

	async function exportPDF() {
		isExporting = true;
		try {
			const reportWindow = window.open('', '_blank', 'width=800,height=600');
			if (!reportWindow) {
				alert('Please allow popups to export the report');
				return;
			}
			if (!session) {
				alert('Session data not loaded');
				return;
			}
			const reportHTML = generateReportHTML({ session, events, sessionId });
			reportWindow.document.write(reportHTML);
			reportWindow.document.close();
			setTimeout(() => reportWindow.print(), 500);
		} finally {
			isExporting = false;
		}
	}

	// ============================================================================
	// UI HELPERS
	// ============================================================================

	function getEventCardClasses(priority: EventPriority): string {
		if (priority === 'major') {
			return 'bg-neutral-50 dark:bg-neutral-900/50 border-2 border-neutral-300 dark:border-neutral-700';
		}
		if (priority === 'meta') {
			return 'bg-neutral-50/50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700';
		}
		return 'bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700';
	}

	// ============================================================================
	// LIFECYCLE
	// ============================================================================

	onMount(() => {
		(async () => {
			try {
				await loadSession();
				await loadHistoricalEvents();
				await tick();

				console.log('[Events] Session and history loaded, checking session status...');

				// Skip SSE connection for sessions that are not actively running
				if (session?.status === 'completed' || session?.status === 'failed' || session?.status === 'paused') {
					console.log(`[Events] Session is ${session.status}, skipping SSE connection`);
					store.setConnectionStatus('connected');
					return;
				}

				await startEventStream();
				console.log('[Events] Initialization sequence complete');
			} catch (err) {
				console.error('[Events] Initialization failed:', err);
				store.setError(err instanceof Error ? err.message : 'Failed to initialize session');
				store.setIsLoading(false);
			}
		})();
	});

	onDestroy(() => {
		sseConnection?.close();
		revealManager.cleanup();
		timing.cleanup();
		memoized.cleanup();
	});
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
			currentWorkingPhase={timing.currentWorkingPhase}
			workingElapsedSeconds={timing.workingElapsedSeconds}
			estimatedDuration={timing.estimatedDuration}
			isStale={timing.isStale}
			staleSinceSeconds={timing.staleSinceSeconds}
			sessionStatus={session?.status}
		/>

		<!-- Clarification Questions -->
		{#if eventState.needsClarification && eventState.clarificationQuestions}
			<ClarificationForm
				{sessionId}
				questions={eventState.clarificationQuestions}
				reason={eventState.clarificationRequiredEvent?.data?.reason as string | undefined}
				onSubmitted={handleClarificationSubmitted}
			/>
		{/if}

		<!-- Context Insufficient Modal (Option D+E Hybrid) -->
		{#if eventState.needsContextChoice && eventState.contextInsufficientEvent}
			<ContextInsufficientModal
				{sessionId}
				eventData={(eventState.contextInsufficientEvent as ContextInsufficientEvent).data}
				onChoiceMade={handleContextChoiceMade}
			/>
		{/if}

		<!-- ARIA Live Region -->
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
				<div
					class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700"
				>
					<div class="border-b border-slate-200 dark:border-slate-700">
						<!-- Header Row -->
						<div class="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-0">
							<div class="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
								<h2 class="text-lg font-semibold text-slate-900 dark:text-white">
									{#if memoized.subProblemTabs.length > 1}
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
								<label
									for="auto-scroll-checkbox"
									class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400"
								>
									<input
										id="auto-scroll-checkbox"
										type="checkbox"
										bind:checked={autoScroll}
										class="rounded"
									/>
									Auto-scroll
								</label>

								<div class="flex items-center gap-2">
									<span class="text-sm text-slate-600 dark:text-slate-400">View:</span>
									<div class="flex items-center gap-1 bg-slate-200 dark:bg-slate-700 rounded-lg p-0.5">
										<button
											onclick={() => view.setGlobalViewMode('simple')}
											class="px-2 py-1 text-xs font-medium rounded-md transition-colors {view.contributionViewMode === 'simple'
												? 'bg-white dark:bg-slate-600 text-slate-900 dark:text-white shadow-sm'
												: 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}"
										>
											Simple
										</button>
										<button
											onclick={() => view.setGlobalViewMode('full')}
											class="px-2 py-1 text-xs font-medium rounded-md transition-colors {view.contributionViewMode === 'full'
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
							<div class="space-y-4 p-4">
								{#each Array(5) as _, i}
									<EventCardSkeleton />
								{/each}
							</div>
						{:else if events.length === 0}
							<div
								class="flex flex-col items-center justify-center h-full text-slate-500 dark:text-slate-400 p-4"
							>
								<ActivityStatus
									variant="card"
									message={INITIAL_WAITING_MESSAGES[revealManager.initialWaitingMessageIndex]}
									showDots
								/>
							</div>
						{:else if memoized.subProblemTabs.length > 1}
							<!-- Tab-based navigation for multiple sub-problems -->
							<div class="h-full flex flex-col">
								<SubProblemTabs
									subProblemTabs={memoized.subProblemTabs}
									showConclusionTab={eventState.showConclusionTab}
									activeSubProblemTab={view.activeSubProblemTab}
									onTabChange={(tabId) => view.setActiveTab(tabId)}
								/>

								{#each memoized.subProblemTabs as tab}
									{@const isTabActive = tab.id === view.activeSubProblemTab}
									{@const tabIndex = parseInt(tab.id.replace('subproblem-', ''))}
									{@const subGroupedEvents = memoized.groupedEvents.filter((group) => {
										if (group.type === 'single' && group.event) {
											if (group.event.event_type === 'decomposition_complete') return false;
											const eventSubIndex = group.event.data.sub_problem_index;
											return eventSubIndex === tabIndex;
										} else if (group.type === 'round' || group.type === 'expert_panel') {
											if (group.events && group.events.length > 0) {
												const eventSubIndex = group.events[0].data.sub_problem_index;
												return eventSubIndex === tabIndex;
											}
										}
										return false;
									})}
									<div
										class="flex-1 overflow-y-auto p-4 space-y-4"
										role="tabpanel"
										id="tabpanel-{tab.id}"
										aria-labelledby="tab-{tab.id}"
										aria-hidden={!isTabActive}
										inert={!isTabActive}
										hidden={!isTabActive}
									>
										<div
											class="bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 p-4"
										>
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
															experts: group.events.map(
																(e): ExpertInfo => ({
																	persona: e.data.persona as {
																		code: string;
																		name: string;
																		display_name: string;
																		archetype: string;
																		domain_expertise: string[];
																	},
																	rationale: e.data.rationale as string,
																	order: e.data.order as number,
																})
															),
															subProblemGoal: group.subProblemGoal,
														}}
													/>
												</div>
											{:else if group.type === 'round' && group.events}
												{@const roundKey = `round-${group.roundNumber}`}
												{@const visibleCount = revealManager.getVisibleCount(roundKey)}
												<ContributionRound
													roundNumber={group.roundNumber || 0}
													events={group.events}
													{visibleCount}
													viewMode={view.contributionViewMode}
													showFullTranscripts={view.showFullTranscripts}
													cardViewModes={view.cardViewModes}
													onToggleCardViewMode={view.toggleCardViewMode}
													thinkingMessages={THINKING_MESSAGES}
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
														{:else if event.event_type === 'error' || event.event_type === 'meeting_failed'}
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

										{#if eventState.subProblemCompleteEvents[tabIndex]?.data?.synthesis}
											<div class="mt-8 border-t border-slate-200 dark:border-slate-700 pt-6 space-y-6">
												<DynamicEventComponent
													event={eventState.subProblemCompleteEvents[tabIndex]}
													eventType="subproblem_complete"
												/>

												<!-- P2-004: Expert Summaries Panel -->
												{#if session?.expert_summaries_by_subproblem?.[tabIndex] && eventState.personasBySubProblem[tabIndex]}
													<ExpertSummariesPanel
														expertSummaries={session.expert_summaries_by_subproblem[tabIndex]}
														personas={eventState.personasBySubProblem[tabIndex]}
														subProblemGoal={tab.goal}
													/>
												{/if}

												<!-- P2-006: Research Panel -->
												{#if session?.research_results_by_subproblem?.[tabIndex]}
													<ResearchPanel
														researchResults={session.research_results_by_subproblem[tabIndex]}
														subProblemGoal={tab.goal}
													/>
												{/if}
											</div>
										{/if}

										{#if waiting.isWaitingForFirstContributions && isTabActive}
											<div
												class="bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800 py-4 px-4"
												transition:fade={{ duration: 300 }}
											>
												<ActivityStatus
													variant="inline"
													message={waiting.phaseWaitingMessage}
													class="text-amber-700 dark:text-amber-300 font-medium"
												/>
											</div>
										{/if}

										{#if waiting.isWaitingForNextRound && isTabActive}
											<div
												class="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 py-4 px-4"
												transition:fade={{ duration: 300 }}
											>
												<ActivityStatus
													variant="inline"
													message={BETWEEN_ROUNDS_MESSAGES[revealManager.betweenRoundsMessageIndex]}
													class="text-blue-700 dark:text-blue-300 font-medium"
												/>
											</div>
										{/if}
									</div>
								{/each}

								<!-- Conclusion Tab Panel -->
								{#if eventState.showConclusionTab}
									{@const isTabActive = view.activeSubProblemTab === 'conclusion'}
									<div
										class="flex-1 overflow-y-auto p-4 space-y-6"
										role="tabpanel"
										id="tabpanel-conclusion"
										aria-labelledby="tab-conclusion"
										aria-hidden={!isTabActive}
										inert={!isTabActive}
										hidden={!isTabActive}
									>
										{#if eventState.decompositionEvent}
											<DynamicEventComponent
												event={eventState.decompositionEvent}
												eventType="decomposition_complete"
											/>
										{/if}

										{#if eventState.subProblemCompleteEvents.length > 0 && !eventState.metaSynthesisEvent && memoized.subProblemTabs.length > 1}
											<div
												class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4 mb-6"
											>
												<ActivityStatus
													variant="inline"
													message="Generating final synthesis..."
													phase="{eventState.subProblemCompleteEvents.length} of {memoized.subProblemTabs.length} focus areas completed"
													class="text-blue-900 dark:text-blue-100"
												/>
											</div>
										{/if}

										{#if eventState.metaSynthesisEvent}
											<DynamicEventComponent
												event={eventState.metaSynthesisEvent}
												eventType="synthesis_complete"
											/>
										{:else if eventState.synthesisCompleteEvent}
											<div class="space-y-6">
												<DynamicEventComponent
													event={eventState.synthesisCompleteEvent}
													eventType="synthesis_complete"
												/>

												<!-- P2-004: Expert Summaries Panel for single sub-problem -->
												{#if eventState.synthesisCompleteEvent}
													{@const subProblemIndex = (eventState.synthesisCompleteEvent.data.sub_problem_index as number | undefined) ?? 0}
													{#if session?.expert_summaries_by_subproblem?.[subProblemIndex] && eventState.personasBySubProblem[subProblemIndex]}
														<ExpertSummariesPanel
															expertSummaries={session.expert_summaries_by_subproblem[subProblemIndex]}
															personas={eventState.personasBySubProblem[subProblemIndex]}
														/>
													{/if}
												{/if}
											</div>
										{:else if eventState.subProblemCompleteEvents.length > 0 && eventState.subProblemCompleteEvents.some((e) => e.data.synthesis)}
											<div class="space-y-6">
												<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
													Sub-Problem Syntheses
												</h3>
												{#each eventState.subProblemCompleteEvents.filter((e) => e.data.synthesis) as spEvent}
													<DynamicEventComponent event={spEvent} eventType="subproblem_complete" />
												{/each}
											</div>
										{:else}
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
								groupedEvents={memoized.groupedEvents}
								{session}
								{isLoading}
								visibleContributionCounts={revealManager.visibleContributionCounts}
								contributionViewMode={view.contributionViewMode}
								showFullTranscripts={view.showFullTranscripts}
								cardViewModes={view.cardViewModes}
								thinkingMessages={THINKING_MESSAGES}
								isWaitingForFirstContributions={waiting.isWaitingForFirstContributions}
								phaseWaitingMessage={waiting.phaseWaitingMessage}
								isWaitingForNextRound={waiting.isWaitingForNextRound}
								betweenRoundsMessages={BETWEEN_ROUNDS_MESSAGES}
								betweenRoundsMessageIndex={revealManager.betweenRoundsMessageIndex}
								initialWaitingMessages={INITIAL_WAITING_MESSAGES}
								initialWaitingMessageIndex={revealManager.initialWaitingMessageIndex}
								isSynthesizing={timing.isSynthesizing}
								isVoting={timing.isVoting}
								elapsedSeconds={timing.elapsedSeconds}
								votingStartTime={timing.votingStartTime}
								isTransitioningSubProblem={waiting.isTransitioningSubProblem}
								onToggleCardViewMode={view.toggleCardViewMode}
							/>
						{/if}
					</div>
				</div>
			</div>

			<!-- Sidebar -->
			<div class="space-y-6 lg:self-stretch flex flex-col">
				{#if session}
					<details
						class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700"
						open
					>
						<summary
							class="cursor-pointer p-4 font-semibold text-slate-900 dark:text-white hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-t-lg transition-colors text-sm"
						>
							Problem Statement
						</summary>
						<div class="px-4 pb-4">
							<p class="text-sm text-slate-700 dark:text-slate-300">
								{session.problem?.statement || 'Problem statement not available'}
							</p>
						</div>
					</details>

					<div class="flex-1">
						<DecisionMetrics
							{events}
							currentPhase={session.phase}
							currentRound={session.round_number ?? null}
							activeSubProblemIndex={view.activeSubProblemTab
								? parseInt(view.activeSubProblemTab.replace('subproblem-', ''))
								: null}
							totalSubProblems={memoized.subProblemTabs.length}
						/>
					</div>

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

		<AiDisclaimer class="mt-8" />
	</main>
</div>
