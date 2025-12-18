<script lang="ts">
	import { fade } from 'svelte/transition';
	import { CheckCircle, AlertCircle, AlertTriangle, X } from 'lucide-svelte';
	import type { SSEEvent, ExpertInfo, ContributionEvent, PersonaSelectedPayload } from '$lib/api/sse-events';
	import { isPersonaSelectedEvent } from '$lib/api/sse-events';
	import type { EventGroup } from '../../../routes/(app)/meeting/[id]/lib/eventGrouping';
	import type { SessionData } from '../../../routes/(app)/meeting/[id]/lib/sessionStore.svelte';
	import { getEventPriority, type EventPriority } from '$lib/utils/event-humanization';

	import DynamicEventComponent from '$lib/components/events/DynamicEventComponent.svelte';
	import ContributionRound from '$lib/components/events/ContributionRound.svelte';
	import { RelativeTimestamp, LazyRender } from '$lib/components/ui';
	import { ActivityStatus } from '$lib/components/ui/loading';
	import { EventCardSkeleton } from '$lib/components/ui/skeletons';

	// Threshold for enabling lazy rendering (number of grouped events)
	const LAZY_RENDER_THRESHOLD = 20;

	interface Props {
		events: SSEEvent[];
		groupedEvents: EventGroup[];
		session: SessionData | null;
		isLoading: boolean;
		visibleContributionCounts: Map<string, number>;
		contributionViewMode: 'simple' | 'full';
		showFullTranscripts: boolean;
		cardViewModes: Map<string, 'simple' | 'full'>;
		thinkingMessages: Array<(name: string) => string>;

		// Waiting state
		isWaitingForFirstContributions: boolean;
		phaseWaitingMessage: string;
		isWaitingForNextRound: boolean;
		betweenRoundsMessages: string[];
		betweenRoundsMessageIndex: number;
		initialWaitingMessages: string[];
		initialWaitingMessageIndex: number;

		// Synthesis/Voting states
		isSynthesizing: boolean;
		isVoting: boolean;
		elapsedSeconds: number;
		votingStartTime: number | null;

		// Transition state
		isTransitioningSubProblem: boolean;

		// Gap detection state
		hasGap?: boolean;
		missedEventCount?: number;
		onDismissGapWarning?: () => void;

		// Callbacks
		onToggleCardViewMode: (cardId: string) => void;
	}

	let {
		events,
		groupedEvents,
		session,
		isLoading,
		visibleContributionCounts,
		contributionViewMode,
		showFullTranscripts,
		cardViewModes,
		thinkingMessages,
		isWaitingForFirstContributions,
		phaseWaitingMessage,
		isWaitingForNextRound,
		betweenRoundsMessages,
		betweenRoundsMessageIndex,
		initialWaitingMessages,
		initialWaitingMessageIndex,
		isSynthesizing,
		isVoting,
		elapsedSeconds,
		votingStartTime,
		isTransitioningSubProblem,
		hasGap = false,
		missedEventCount = 0,
		onDismissGapWarning,
		onToggleCardViewMode
	}: Props = $props();

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

<div
	id="events-container"
	class="overflow-y-auto"
	style="height: calc(100vh - 400px); min-height: 600px; overflow-anchor: none;"
>
	<!-- Gap Detection Warning Banner -->
	{#if hasGap}
		<div
			class="mx-4 mt-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-lg p-4"
			transition:fade={{ duration: 200 }}
		>
			<div class="flex items-start gap-3">
				<AlertTriangle size={20} class="text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
				<div class="flex-1 min-w-0">
					<h4 class="text-sm font-medium text-amber-800 dark:text-amber-200">
						Possible Missing Updates
					</h4>
					<p class="text-sm text-amber-700 dark:text-amber-300 mt-1">
						{missedEventCount} event{missedEventCount === 1 ? '' : 's'} may have been missed during reconnection.
						For complete data, consider refreshing the page.
					</p>
				</div>
				{#if onDismissGapWarning}
					<button
						type="button"
						onclick={onDismissGapWarning}
						class="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200 transition-colors"
						aria-label="Dismiss warning"
					>
						<X size={18} />
					</button>
				{/if}
			</div>
		</div>
	{/if}

	{#if isLoading}
		<!-- Skeleton Loading States -->
		<div class="space-y-4 p-4">
			{#each Array(5) as _, i (i)}
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
	{:else}
		<!-- Single sub-problem or linear view -->
		<div class="p-4 space-y-4">
			<!-- Focus area transition loading state -->
			{#if isTransitioningSubProblem}
				<div class="animate-pulse bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
					<div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4 mb-2"></div>
					<div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
					<p class="text-sm text-slate-500 dark:text-slate-400 mt-2">
						Preparing next focus area...
					</p>
				</div>
			{/if}

			<!-- Phase-specific waiting indicator (experts being selected / familiarising) -->
			{#if isWaitingForFirstContributions}
				<div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800 py-4 px-4" transition:fade={{ duration: 300 }}>
					<ActivityStatus
						variant="inline"
						message={phaseWaitingMessage}
						class="text-amber-700 dark:text-amber-300 font-medium"
					/>
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
					<ActivityStatus
						variant="card"
						message="Collecting Expert Recommendations..."
						phase="Experts are providing their final recommendations"
						showElapsedTime
						startTime={votingStartTime ? new Date(votingStartTime) : null}
						class="text-purple-900 dark:text-purple-100"
					/>
				</div>
			{/if}

			{#each groupedEvents as group, index (index)}
				{@const useLazyRendering = groupedEvents.length > LAZY_RENDER_THRESHOLD}
				{@const shouldLazyLoad = useLazyRendering && index < groupedEvents.length - 10}
				{#if group.type === 'expert_panel' && group.events}
					<!-- Render grouped expert panel -->
					<LazyRender height={shouldLazyLoad ? 150 : 0} key={index}>
						<div transition:fade={{ duration: 300, delay: 50 }}>
							<DynamicEventComponent
								event={group.events[0]}
								eventType="expert_panel"
								skeletonProps={{ hasAvatar: false }}
								componentProps={{
									experts: group.events.filter(isPersonaSelectedEvent).map((e): ExpertInfo => ({
										persona: e.data.persona,
										rationale: e.data.rationale,
										order: e.data.order,
									})),
									subProblemGoal: group.subProblemGoal
								}}
							/>
						</div>
					</LazyRender>
				{:else if group.type === 'round' && group.events}
					<!-- Render grouped contributions with new ExpertPerspectiveCard -->
					{@const roundKey = `round-${group.roundNumber}`}
					{@const visibleCount = visibleContributionCounts.get(roundKey) || 0}
					<LazyRender height={shouldLazyLoad ? 200 : 0} key={index}>
						<ContributionRound
							roundNumber={group.roundNumber || 0}
							events={group.events}
							{visibleCount}
							viewMode={contributionViewMode}
							{showFullTranscripts}
							{cardViewModes}
							onToggleCardViewMode={onToggleCardViewMode}
							{thinkingMessages}
						/>
					</LazyRender>
				{:else if group.type === 'single' && group.event}
					{@const event = group.event}
					{@const priority = getEventPriority(event.event_type)}
					<!-- Render single event with visual hierarchy -->
					<LazyRender height={shouldLazyLoad ? 100 : 0} key={index}>
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
										<RelativeTimestamp timestamp={event.timestamp ?? ''} />
									</div>

									<!-- Render appropriate component based on event type with dynamic loading -->
									<DynamicEventComponent
										{event}
										skeletonProps={{ hasAvatar: false }}
									/>
								</div>
							</div>
						</div>
					</LazyRender>
				{/if}
			{/each}

			<!-- Between-rounds waiting indicator -->
			{#if isWaitingForNextRound}
				<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 py-4 px-4" transition:fade={{ duration: 300 }}>
					<ActivityStatus
						variant="inline"
						message={betweenRoundsMessages[betweenRoundsMessageIndex]}
						class="text-blue-700 dark:text-blue-300 font-medium"
					/>
				</div>
			{/if}
		</div>
	{/if}
</div>
