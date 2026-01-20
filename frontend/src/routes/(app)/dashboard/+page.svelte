<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { browser } from '$app/environment';
	import { beforeNavigate, goto } from '$app/navigation';
	import { user } from '$lib/stores/auth';
	import { apiClient } from '$lib/api/client';
	import type { SessionResponse, AllActionsResponse, TaskWithSessionContext, ActionStatsResponse, UserContextResponse } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import Badge from '$lib/components/ui/Badge.svelte';
	import ContextRefreshBanner from '$lib/components/ui/ContextRefreshBanner.svelte';
	import OnboardingChecklist from '$lib/components/ui/OnboardingChecklist.svelte';
	import ActivityHeatmap from '$lib/components/dashboard/ActivityHeatmap.svelte';
	import PendingReminders from '$lib/components/dashboard/PendingReminders.svelte';
	import FailedMeetingAlert from '$lib/components/dashboard/FailedMeetingAlert.svelte';
	import GoalBanner from '$lib/components/dashboard/GoalBanner.svelte';
	import SmartFocusBanner, { type FocusState } from '$lib/components/dashboard/SmartFocusBanner.svelte';
	import ObjectiveProgressModal from '$lib/components/dashboard/ObjectiveProgressModal.svelte';
	import type { ObjectiveProgress } from '$lib/api/types';
	import WeeklyPlanView from '$lib/components/dashboard/WeeklyPlanView.svelte';
	import DailyActivities from '$lib/components/dashboard/DailyActivities.svelte';
	import RecentMeetingsWidget from '$lib/components/dashboard/RecentMeetingsWidget.svelte';
	import CognitionWidget from '$lib/components/dashboard/CognitionWidget.svelte';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { formatCompactRelativeTime } from '$lib/utils/time-formatting';
	import { createLogger } from '$lib/utils/debug';
	import { getDueDateStatus, getDueDateLabel, getDueDateBadgeClasses, needsAttention, getDueDateRelativeText } from '$lib/utils/due-dates';
	import { startOnboardingTour, injectTourStyles, cleanupTour, destroyActiveTour, setTourNavigationCallbacks } from '$lib/tour/onboarding-tour';
	import tourStore, { checkOnboardingStatus, setTourActive, completeTour, handleNavigationDuringTour, setTourPage, allowTourNavigation } from '$lib/stores/tour';
	import { toast } from '$lib/stores/toast';

	// Navigation lock during tour + cleanup on navigation
	beforeNavigate(({ cancel }) => {
		// Destroy any active tour popup to prevent persistence
		destroyActiveTour();
		if (handleNavigationDuringTour()) {
			cancel();
		}
	});

	const log = createLogger('Dashboard');

	// Use data fetch utility for sessions
	const sessionsData = useDataFetch(() => apiClient.listSessions());
	// Fetch outstanding actions (todo and doing only)
	const actionsData = useDataFetch(() => apiClient.getAllActions());
	// Fetch action stats for activity heatmap (annual view)
	const statsData = useDataFetch(() => apiClient.getActionStats(365));
	// Fetch user context for onboarding checklist
	const contextData = useDataFetch(() => apiClient.getUserContext());
	// Fetch working pattern for activity heatmap
	const workingPatternData = useDataFetch(() => apiClient.getWorkingPattern());
	// Fetch heatmap depth preference
	const heatmapDepthData = useDataFetch(() => apiClient.getHeatmapDepth());
	// Fetch cognition profile for onboarding checklist
	const cognitionData = useDataFetch(() => apiClient.getCognitionProfile());

	// Goal staleness state (fetched separately as it's a new endpoint)
	interface GoalStaleness {
		days_since_change: number | null;
		should_prompt: boolean;
		last_goal: string | null;
	}
	let goalStaleness = $state<GoalStaleness | null>(null);

	// Objective progress state
	let objectivesProgress = $state<Record<string, ObjectiveProgress>>({});
	let progressModalOpen = $state(false);
	let progressModalLoading = $state(false);
	let selectedObjectiveIndex = $state(0);
	let selectedObjectiveText = $state('');
	let selectedObjectiveProgress = $state<ObjectiveProgress | null>(null);

	// Derived state for template compatibility
	const sessions = $derived<SessionResponse[]>(sessionsData.data?.sessions || []);
	const isLoading = $derived(sessionsData.isLoading);
	const error = $derived(sessionsData.error);

	// Show toast when error changes - defer to avoid state mutation during render
	$effect(() => {
		if (error) {
			setTimeout(() => toast.error(error), 0);
		}
	});

	// Onboarding state
	let onboardingDismissed = $state(false);

	
	// Show onboarding only for new users who haven't dismissed or completed it
	const showOnboarding = $derived(
		!onboardingDismissed &&
		!contextData.data?.context?.onboarding_completed &&
		sessions.length < 3
	);

	async function dismissOnboarding() {
		onboardingDismissed = true;
		// Persist to backend
		try {
			await apiClient.updateUserContext({ onboarding_completed: true });
		} catch (err) {
			console.error('Failed to save onboarding dismissal:', err);
		}
	}

	// Objective progress handlers
	function handleEditProgress(index: number, objective: string, progress: ObjectiveProgress | null) {
		selectedObjectiveIndex = index;
		selectedObjectiveText = objective;
		selectedObjectiveProgress = progress;
		progressModalOpen = true;
	}

	async function handleSaveProgress(index: number, current: string, target: string, unit: string | null) {
		progressModalLoading = true;
		try {
			const response = await apiClient.updateObjectiveProgress(index, { current, target, unit });
			if (response.progress) {
				objectivesProgress = {
					...objectivesProgress,
					[String(index)]: response.progress
				};
			}
			progressModalOpen = false;
			toast.success('Progress updated');
		} catch (err) {
			log.error('Failed to save progress:', err);
			toast.error('Failed to save progress');
		} finally {
			progressModalLoading = false;
		}
	}

	function handleCloseProgressModal() {
		progressModalOpen = false;
	}

	// Outstanding actions (todo + in_progress, sorted by priority)
	const outstandingActions = $derived.by<TaskWithSessionContext[]>(() => {
		if (!actionsData.data?.sessions) return [];
		const allTasks = actionsData.data.sessions.flatMap((s) => s.tasks as TaskWithSessionContext[]);
		// Filter to only todo and in_progress, then sort by priority (high first) then status (in_progress first)
		return allTasks
			.filter((t) => t.status === 'todo' || t.status === 'in_progress')
			.sort((a, b) => {
				// Status priority: in_progress > todo
				if (a.status !== b.status) {
					return a.status === 'in_progress' ? -1 : 1;
				}
				// Priority order: high > medium > low
				const priorityOrder = { high: 0, medium: 1, low: 2 };
				return (priorityOrder[a.priority as keyof typeof priorityOrder] || 2) -
					(priorityOrder[b.priority as keyof typeof priorityOrder] || 2);
			})
			.slice(0, 5); // Show top 5 outstanding actions
	});

	// Total count of outstanding actions (for badge display)
	const outstandingCount = $derived(
		actionsData.data ? ((actionsData.data.by_status.todo || 0) + (actionsData.data.by_status.in_progress || 0)) : 0
	);

	// Actions needing attention (overdue or due today)
	const actionsNeedingAttention = $derived.by<TaskWithSessionContext[]>(() => {
		if (!actionsData.data?.sessions) return [];
		const allTasks = actionsData.data.sessions.flatMap((s) => s.tasks as TaskWithSessionContext[]);
		return allTasks
			.filter((t) => (t.status === 'todo' || t.status === 'in_progress') && needsAttention(t.suggested_completion_date))
			.sort((a, b) => {
				// Overdue first, then due-today
				const statusA = getDueDateStatus(a.suggested_completion_date);
				const statusB = getDueDateStatus(b.suggested_completion_date);
				if (statusA === 'overdue' && statusB !== 'overdue') return -1;
				if (statusB === 'overdue' && statusA !== 'overdue') return 1;
				// Then by priority
				const priorityOrder = { high: 0, medium: 1, low: 2 };
				return (priorityOrder[a.priority as keyof typeof priorityOrder] || 2) -
					(priorityOrder[b.priority as keyof typeof priorityOrder] || 2);
			});
	});

	// Count overdue and due-today actions
	const overdueCount = $derived.by<number>(() => {
		if (!actionsData.data?.sessions) return 0;
		const allTasks = actionsData.data.sessions.flatMap((s) => s.tasks as TaskWithSessionContext[]);
		return allTasks.filter((t) =>
			(t.status === 'todo' || t.status === 'in_progress') &&
			getDueDateStatus(t.suggested_completion_date) === 'overdue'
		).length;
	});

	const dueTodayCount = $derived.by<number>(() => {
		if (!actionsData.data?.sessions) return 0;
		const allTasks = actionsData.data.sessions.flatMap((s) => s.tasks as TaskWithSessionContext[]);
		return allTasks.filter((t) =>
			(t.status === 'todo' || t.status === 'in_progress') &&
			getDueDateStatus(t.suggested_completion_date) === 'due-today'
		).length;
	});

	// Derive focus state for SmartFocusBanner (priority-ordered)
	const focusState = $derived.by<FocusState>(() => {
		const hasGoal = !!contextData.data?.context?.north_star_goal;
		const goalStale = goalStaleness?.should_prompt ?? false;
		const hasContext = !!(contextData.data?.context?.product_description || contextData.data?.context?.industry);

		// Priority order:
		// 1. No goal set
		if (!hasGoal) return 'no_goal';
		// 2. Goal is stale (>30 days)
		if (goalStale) return 'stale_goal';
		// 3. Overdue actions
		if (overdueCount > 0) return 'overdue_actions';
		// 4. Actions due today
		if (dueTodayCount > 0) return 'due_today';
		// 5. No business context
		if (!hasContext) return 'stale_context';
		// 6. Default: ready to decide
		return 'ready';
	});

	// Loading state for SmartFocusBanner
	const focusBannerLoading = $derived(actionsData.isLoading || contextData.isLoading);

	onMount(async () => {
		log.log('Loading sessions for user:', $user?.email);
		// Auth is already verified by parent layout, safe to load sessions, actions, stats, and context
		sessionsData.fetch();
		actionsData.fetch();
		statsData.fetch();

		// Fetch context first to check if new user needs redirect
		await contextData.fetch();

		// Check if new user needs redirect to context setup
		const ctx = contextData.data?.context;
		const hasNoContext = !ctx?.product_description && !ctx?.business_model && !ctx?.industry;
		const notOnboarded = !ctx?.onboarding_completed;
		// Only redirect if truly new (no context set, not onboarded, and no sessions yet)
		if (hasNoContext && notOnboarded && sessions.length === 0) {
			log.log('New user detected, redirecting to context setup');
			goto('/context/overview?welcome=true');
			return;
		}

		// Fetch goal staleness (new endpoint)
		try {
			const res = await fetch('/api/v1/context/goal-staleness', { credentials: 'include' });
			if (res.ok) {
				goalStaleness = await res.json();
			}
		} catch (e) {
			log.error('Failed to fetch goal staleness:', e);
		}

		// Fetch objective progress
		try {
			const progressRes = await apiClient.getObjectivesProgress();
			// Convert array to keyed object for GoalBanner
			const progressMap: Record<string, ObjectiveProgress> = {};
			for (const obj of progressRes.objectives) {
				if (obj.progress) {
					progressMap[String(obj.objective_index)] = obj.progress;
				}
			}
			objectivesProgress = progressMap;
		} catch (e) {
			log.error('Failed to fetch objective progress:', e);
		}

		// Check if user needs onboarding tour
		if (browser) {
			const needsTour = await checkOnboardingStatus();
			if (needsTour) {
				// Wait for DOM to be fully rendered
				await tick();

				// Set up navigation callbacks for tour
				setTourNavigationCallbacks({
					onNavigateToActions: () => {
						// Set tour page for continuation
						setTourPage('actions');
						// Allow navigation without confirmation
						allowTourNavigation();
						cleanupTour();
						goto('/actions');
					},
					onNavigateToProjects: () => {
						// Set tour page for continuation
						setTourPage('projects');
						// Allow navigation without confirmation
						allowTourNavigation();
						cleanupTour();
						goto('/projects');
					},
				});

				// Inject tour styles and start after a short delay for animations
				injectTourStyles();
				setTimeout(() => {
					setTourActive(true);
					startOnboardingTour(async () => {
						setTourActive(false);
						cleanupTour();
						const freshCompletion = await completeTour();
						if (freshCompletion) {
							// Redirect to context overview after tour completion
							goto('/context/overview');
						}
					});
				}, 300);
			}
		}
	});

	async function loadSessions() {
		// Refresh both sessions and actions lists
		// (deleting a session cascade soft-deletes its associated actions)
		await Promise.all([sessionsData.fetch(), actionsData.fetch()]);
	}

	function truncateProblem(problem: string, maxLength: number = 80): string {
		if (problem.length <= maxLength) return problem;
		return problem.substring(0, maxLength) + '...';
	}
</script>

<svelte:head>
	<title>Dashboard - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">
	<!-- Visually hidden page heading for screen readers -->
	<h1 class="sr-only">Dashboard</h1>

	<!-- Page Content -->
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Onboarding checklist for new users -->
		{#if showOnboarding}
			<OnboardingChecklist
				userContext={contextData.data?.context}
				sessionCount={sessions.length}
				hasCognitionProfile={!!cognitionData.data?.cognitive_style_summary}
				onDismiss={dismissOnboarding}
			/>
		{/if}

		<!-- Context refresh reminder -->
		<ContextRefreshBanner />

		<!-- Failed meeting alert -->
		<FailedMeetingAlert class="mb-6" />

		<!-- Goal Banner - Primary visual element -->
		<GoalBanner
			northStarGoal={contextData.data?.context?.north_star_goal}
			strategicObjectives={contextData.data?.context?.strategic_objectives}
			{objectivesProgress}
			daysSinceChange={goalStaleness?.days_since_change}
			shouldPromptReview={goalStaleness?.should_prompt ?? false}
			onEditProgress={handleEditProgress}
		/>

		<!-- Objective Progress Modal -->
		<ObjectiveProgressModal
			bind:open={progressModalOpen}
			objectiveIndex={selectedObjectiveIndex}
			objectiveText={selectedObjectiveText}
			progress={selectedObjectiveProgress}
			loading={progressModalLoading}
			onSave={handleSaveProgress}
			onClose={handleCloseProgressModal}
		/>

		<!-- Cognitive Profile Widget -->
		<div class="mb-6">
			<CognitionWidget />
		</div>

		<!-- Smart Focus Banner - Context-aware primary CTA -->
		<SmartFocusBanner
			{focusState}
			{overdueCount}
			{dueTodayCount}
			daysSinceGoalChange={goalStaleness?.days_since_change}
			hasBusinessContext={!!(contextData.data?.context?.product_description || contextData.data?.context?.industry)}
			loading={focusBannerLoading}
		/>

		<!-- Pending Reminders Panel -->
		<div class="mb-8">
			<PendingReminders />
		</div>

		<!-- Completion Trends Chart -->
		{#if statsData.isLoading}
			<div class="mb-8">
				<div class="flex items-center justify-between mb-4">
					<div class="h-6 w-40 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse"></div>
					<div class="flex gap-4">
						<div class="h-4 w-20 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse"></div>
						<div class="h-4 w-20 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse"></div>
					</div>
				</div>
				<ShimmerSkeleton type="chart" height="200px" />
			</div>
		{:else if statsData.data?.daily && statsData.data.daily.length > 0}
			<div class="mb-8">
				<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
						<svg class="w-4 h-4 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
						</svg>
						Completion Trends
					</h2>
					<div class="flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
						<span class="flex items-center gap-1">
							<span class="font-semibold text-success-600 dark:text-success-400">{statsData.data.totals.completed}</span>
							<span class="hidden sm:inline">done</span>
						</span>
						<span class="flex items-center gap-1">
							<span class="font-semibold text-amber-600 dark:text-amber-400">{statsData.data.totals.in_progress}</span>
							<span class="hidden sm:inline">active</span>
						</span>
						<span class="flex items-center gap-1">
							<span class="font-semibold text-neutral-600 dark:text-neutral-300">{statsData.data.totals.todo}</span>
							<span class="hidden sm:inline">todo</span>
						</span>
					</div>
				</div>

				<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-3 sm:p-4 relative z-0">
					{#if statsData.isLoading}
						<ShimmerSkeleton type="chart" />
					{:else if statsData.data}
						<ActivityHeatmap
							data={statsData.data.daily}
							workingDays={workingPatternData.data?.pattern.working_days ?? [1, 2, 3, 4, 5]}
							historyMonths={heatmapDepthData.data?.depth.history_months ?? 3}
						/>
					{:else}
						<div class="text-center text-neutral-500 dark:text-neutral-400 py-8">No data available</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Weekly Plan View -->
		<div class="mb-8">
			<WeeklyPlanView
				actionsData={actionsData.data}
				workingPattern={workingPatternData.data?.pattern.working_days ?? [1, 2, 3, 4, 5]}
			/>
		</div>

		<!-- Daily Activities / Today's Focus -->
		<DailyActivities actionsData={actionsData.data} />

		<!-- Recent Meetings Widget -->
		{#if sessionsData.isLoading}
			<div class="mb-8">
				<ShimmerSkeleton type="card" />
			</div>
		{:else}
			<div class="mb-8">
				<RecentMeetingsWidget
					sessions={sessions}
					onDelete={loadSessions}
				/>
			</div>
		{/if}

		<!-- Actions Needing Attention (overdue + due today) -->
		{#if actionsData.isLoading}
			<div class="mb-8">
				<div class="flex items-center justify-between mb-4">
					<div class="h-6 w-36 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse"></div>
					<div class="h-4 w-24 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse"></div>
				</div>
				<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					<div class="divide-y divide-neutral-200 dark:divide-neutral-700">
						{#each Array(3) as _, i (i)}
							<ShimmerSkeleton type="list-item" />
						{/each}
					</div>
				</div>
			</div>
		{:else if actionsNeedingAttention.length > 0}
			<div class="mb-8" data-tour={outstandingActions.length === 0 ? 'actions-view' : undefined}>
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-xl font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
						<svg class="w-5 h-5 text-error-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
						</svg>
						Needs Attention
						<span class="px-2 py-0.5 text-sm font-medium bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-300 rounded-full">
							{actionsNeedingAttention.length}
						</span>
					</h2>
					<a href="/actions" class="text-sm text-brand-600 dark:text-brand-400 hover:underline flex items-center gap-1">
						View all actions
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
					</a>
				</div>

				<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border-2 border-error-200 dark:border-error-800 overflow-hidden">
					<div class="divide-y divide-neutral-200 dark:divide-neutral-700">
						{#each actionsNeedingAttention as action (action.id + '-attention')}
							{@const dueDateStatus = getDueDateStatus(action.suggested_completion_date)}
							<a
								href="/actions/{action.id}"
								class="flex items-center gap-4 p-4 hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors {dueDateStatus === 'overdue' ? 'bg-error-50/50 dark:bg-error-900/10' : 'bg-warning-50/50 dark:bg-warning-900/10'}"
							>
								<!-- Alert indicator -->
								<div class="flex-shrink-0">
									<span class="flex items-center justify-center w-8 h-8 rounded-full {dueDateStatus === 'overdue' ? 'bg-error-100 dark:bg-error-900/30' : 'bg-warning-100 dark:bg-warning-900/30'}">
										{#if dueDateStatus === 'overdue'}
											<svg class="w-4 h-4 text-error-600 dark:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
											</svg>
										{:else}
											<svg class="w-4 h-4 text-warning-600 dark:text-warning-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
										{/if}
									</span>
								</div>

								<!-- Action content -->
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="font-medium text-neutral-900 dark:text-white truncate">
											{action.title}
										</span>
										<span class={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded border ${getDueDateBadgeClasses(dueDateStatus)}`}>
											{getDueDateLabel(dueDateStatus)}
										</span>
										<Badge variant={action.priority === 'high' ? 'error' : action.priority === 'medium' ? 'warning' : 'success'}>
											{action.priority}
										</Badge>
									</div>
									<div class="flex items-center gap-3 text-sm text-neutral-500 dark:text-neutral-400">
										<span class={dueDateStatus === 'overdue' ? 'text-error-600 dark:text-error-400 font-medium' : 'text-warning-600 dark:text-warning-400'}>
											{getDueDateRelativeText(action.suggested_completion_date)}
										</span>
										<span class="truncate">From: {truncateProblem(action.problem_statement, 40)}</span>
									</div>
								</div>

								<!-- Arrow -->
								<svg class="w-5 h-5 text-neutral-400 dark:text-neutral-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
								</svg>
							</a>
						{/each}
					</div>
				</div>
			</div>
		{/if}

		<!-- Outstanding Actions Section (at top per UX best practices) -->
		{#if outstandingActions.length > 0}
			<div class="mb-8" data-tour="actions-view">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-xl font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
						<svg class="w-5 h-5 text-warning-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
						</svg>
						Outstanding Actions
						{#if outstandingCount > 0}
							<span class="px-2 py-0.5 text-sm font-medium bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300 rounded-full">
								{outstandingCount}
							</span>
						{/if}
					</h2>
					<a href="/actions" class="text-sm text-brand-600 dark:text-brand-400 hover:underline flex items-center gap-1">
						View all
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
					</a>
				</div>

				<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					<div class="divide-y divide-neutral-200 dark:divide-neutral-700">
						{#each outstandingActions as action (action.id + '-' + action.session_id)}
							<a
								href="/actions/{action.id}"
								class="flex items-center gap-4 p-4 hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors"
							>
								<!-- Status indicator -->
								<div class="flex-shrink-0">
									{#if action.status === 'in_progress'}
										<span class="flex items-center justify-center w-8 h-8 rounded-full bg-warning-100 dark:bg-warning-900/30">
											<svg class="w-4 h-4 text-warning-600 dark:text-warning-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
										</span>
									{:else}
										<span class="flex items-center justify-center w-8 h-8 rounded-full bg-neutral-100 dark:bg-neutral-700">
											<svg class="w-4 h-4 text-neutral-500 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
										</span>
									{/if}
								</div>

								<!-- Action content -->
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="font-medium text-neutral-900 dark:text-white truncate">
											{action.title}
										</span>
										<Badge variant={action.status === 'in_progress' ? 'warning' : 'neutral'}>
											{action.status === 'in_progress' ? 'In Progress' : 'To Do'}
										</Badge>
										<Badge variant={action.priority === 'high' ? 'error' : action.priority === 'medium' ? 'warning' : 'success'}>
											{action.priority}
										</Badge>
										{#if getDueDateStatus(action.suggested_completion_date) === 'overdue' || getDueDateStatus(action.suggested_completion_date) === 'due-today' || getDueDateStatus(action.suggested_completion_date) === 'due-soon'}
											{@const dueDateStatus = getDueDateStatus(action.suggested_completion_date)}
											<span class={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded border ${getDueDateBadgeClasses(dueDateStatus)}`}>
												{#if dueDateStatus === 'overdue'}
													<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
													</svg>
												{:else}
													<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
													</svg>
												{/if}
												{getDueDateLabel(dueDateStatus)}
											</span>
										{/if}
									</div>
									<div class="text-sm text-neutral-500 dark:text-neutral-400 truncate flex items-center gap-2">
										<span>From: {truncateProblem(action.problem_statement, 50)}</span>
										{#if action.updated_at}
											<span class="text-neutral-400 dark:text-neutral-500">·</span>
											<span class="text-neutral-400 dark:text-neutral-500 whitespace-nowrap">Updated {formatCompactRelativeTime(action.updated_at)}</span>
										{/if}
									</div>
								</div>

								<!-- Timeline -->
								{#if action.timeline}
									<div class="flex-shrink-0 text-sm text-neutral-500 dark:text-neutral-400">
										{action.timeline}
									</div>
								{/if}

								<!-- Arrow -->
								<svg class="w-5 h-5 text-neutral-400 dark:text-neutral-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
								</svg>
							</a>
						{/each}
					</div>
				</div>
			</div>
		{/if}

	</div>
</div>
