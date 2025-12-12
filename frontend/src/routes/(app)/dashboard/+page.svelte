<script lang="ts">
	import { onMount } from 'svelte';
	import { user } from '$lib/stores/auth';
	import { apiClient } from '$lib/api/client';
	import type { SessionResponse, AllActionsResponse, TaskWithSessionContext, ActionStatsResponse, UserContextResponse } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import Badge from '$lib/components/ui/Badge.svelte';
	import ContextRefreshBanner from '$lib/components/ui/ContextRefreshBanner.svelte';
	import OnboardingChecklist from '$lib/components/ui/OnboardingChecklist.svelte';
	import ActivityHeatmap from '$lib/components/dashboard/ActivityHeatmap.svelte';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { getSessionStatusColor } from '$lib/utils/colors';
	import { formatCompactRelativeTime } from '$lib/utils/time-formatting';
	import { createLogger } from '$lib/utils/debug';
	import { getDueDateStatus, getDueDateLabel, getDueDateBadgeClasses, needsAttention, getDueDateRelativeText } from '$lib/utils/due-dates';

	const log = createLogger('Dashboard');

	// Use data fetch utility for sessions
	const sessionsData = useDataFetch(() => apiClient.listSessions());
	// Fetch outstanding actions (todo and doing only)
	const actionsData = useDataFetch(() => apiClient.getAllActions());
	// Fetch action stats for activity heatmap (annual view)
	const statsData = useDataFetch(() => apiClient.getActionStats(365));
	// Fetch user context for onboarding checklist
	const contextData = useDataFetch(() => apiClient.getUserContext());

	// Derived state for template compatibility
	const sessions = $derived<SessionResponse[]>(sessionsData.data?.sessions || []);
	const isLoading = $derived(sessionsData.isLoading);
	const error = $derived(sessionsData.error);

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

	// Check if user is admin for cost display
	const isAdmin = $derived($user?.is_admin ?? false);

	onMount(() => {
		log.log('Loading sessions for user:', $user?.email);
		// Auth is already verified by parent layout, safe to load sessions, actions, stats, and context
		sessionsData.fetch();
		actionsData.fetch();
		statsData.fetch();
		contextData.fetch();
	});

	async function loadSessions() {
		await sessionsData.fetch();
	}

	function truncateProblem(problem: string, maxLength: number = 80): string {
		if (problem.length <= maxLength) return problem;
		return problem.substring(0, maxLength) + '...';
	}

	/**
	 * Humanize phase names for user-friendly display
	 * Phases: decomposition, selection, exploration, challenge, convergence, voting, synthesis
	 */
	function humanizePhase(phase: string | null): string {
		if (!phase) return 'Starting';

		const phaseMap: Record<string, string> = {
			// Main deliberation phases
			decomposition: 'Analyzing',
			decompose: 'Analyzing',
			problem_decomposition: 'Analyzing', // Legacy DB default
			selection: 'Selecting Experts',
			exploration: 'Exploring Ideas',
			challenge: 'Deep Analysis',
			convergence: 'Building Consensus',
			voting: 'Collecting Votes',
			synthesis: 'Synthesizing',
			meta_synthesis: 'Final Synthesis',
			// Status-like phases
			complete: 'Completed',
			completed: 'Completed',
			failed: 'Failed',
			killed: 'Stopped',
		};

		return phaseMap[phase.toLowerCase()] || phase.replace(/_/g, ' ');
	}

	async function handleDelete(sessionId: string, event: MouseEvent) {
		event.preventDefault(); // Prevent navigation
		event.stopPropagation(); // Stop event bubbling

		if (!confirm('Are you sure you want to delete this meeting? This cannot be undone.')) {
			return;
		}

		try {
			await apiClient.deleteSession(sessionId);
			// Refresh both sessions and actions lists after successful delete
			// (deleting a session cascade soft-deletes its associated actions)
			await Promise.all([sessionsData.fetch(), actionsData.fetch()]);
		} catch (err) {
			console.error('Failed to delete session:', err);
			// Error will be reflected in sessionsData.error
		}
	}
</script>

<svelte:head>
	<title>Dashboard - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Onboarding checklist for new users -->
		{#if showOnboarding}
			<OnboardingChecklist
				userContext={contextData.data?.context}
				sessionCount={sessions.length}
				onDismiss={dismissOnboarding}
			/>
		{/if}

		<!-- Context refresh reminder -->
		<ContextRefreshBanner />

		<!-- Quick Actions Panel -->
		<div class="mb-8">
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
				<!-- New Meeting -->
				<a
					href="/meeting/new"
					class="group flex items-center gap-4 p-4 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-lg hover:bg-brand-100 dark:hover:bg-brand-900/30 hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-200"
				>
					<div class="flex-shrink-0 w-12 h-12 flex items-center justify-center rounded-full bg-brand-100 dark:bg-brand-800/50 group-hover:bg-brand-200 dark:group-hover:bg-brand-800 transition-colors">
						<svg class="w-6 h-6 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
						</svg>
					</div>
					<div class="flex-1 min-w-0">
						<h3 class="text-sm font-semibold text-brand-900 dark:text-brand-100">Start New Meeting</h3>
						<p class="text-xs text-brand-600 dark:text-brand-400">Get expert perspectives on a decision</p>
					</div>
					<svg class="w-5 h-5 text-brand-400 dark:text-brand-500 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</a>

				<!-- View Actions -->
				<a
					href="/actions"
					class="group flex items-center gap-4 p-4 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-700/50 hover:border-neutral-300 dark:hover:border-neutral-600 transition-all duration-200"
				>
					<div class="flex-shrink-0 w-12 h-12 flex items-center justify-center rounded-full bg-neutral-100 dark:bg-neutral-700 group-hover:bg-neutral-200 dark:group-hover:bg-neutral-600 transition-colors">
						<svg class="w-6 h-6 text-neutral-600 dark:text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
						</svg>
					</div>
					<div class="flex-1 min-w-0">
						<h3 class="text-sm font-semibold text-neutral-900 dark:text-white">View All Actions</h3>
						<p class="text-xs text-neutral-500 dark:text-neutral-400">Track and manage your tasks</p>
					</div>
					<svg class="w-5 h-5 text-neutral-400 dark:text-neutral-500 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</a>

				<!-- Settings -->
				<a
					href="/settings"
					class="group flex items-center gap-4 p-4 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-700/50 hover:border-neutral-300 dark:hover:border-neutral-600 transition-all duration-200"
				>
					<div class="flex-shrink-0 w-12 h-12 flex items-center justify-center rounded-full bg-neutral-100 dark:bg-neutral-700 group-hover:bg-neutral-200 dark:group-hover:bg-neutral-600 transition-colors">
						<svg class="w-6 h-6 text-neutral-600 dark:text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
						</svg>
					</div>
					<div class="flex-1 min-w-0">
						<h3 class="text-sm font-semibold text-neutral-900 dark:text-white">Settings</h3>
						<p class="text-xs text-neutral-500 dark:text-neutral-400">Configure your business context</p>
					</div>
					<svg class="w-5 h-5 text-neutral-400 dark:text-neutral-500 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</a>
			</div>
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
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-xl font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
						<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
						</svg>
						Completion Trends
					</h2>
					<div class="flex items-center gap-4 text-sm text-neutral-500 dark:text-neutral-400">
						<span class="flex items-center gap-1.5">
							<span class="font-medium text-brand-600 dark:text-brand-400">{statsData.data.totals.completed}</span>
							completed
						</span>
						<span class="flex items-center gap-1.5">
							<span class="font-medium text-warning-600 dark:text-warning-400">{statsData.data.totals.in_progress}</span>
							in progress
						</span>
						<span class="flex items-center gap-1.5">
							<span class="font-medium text-neutral-600 dark:text-neutral-300">{statsData.data.totals.todo}</span>
							to do
						</span>
					</div>
				</div>

				<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-4">
					{#if statsData.isLoading}
						<ShimmerSkeleton type="chart" />
					{:else if statsData.data}
						<ActivityHeatmap data={statsData.data.daily} />
					{:else}
						<div class="text-center text-neutral-500 dark:text-neutral-400 py-8">No data available</div>
					{/if}
				</div>
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
			<div class="mb-8">
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
			<div class="mb-8">
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
									<div class="text-sm text-neutral-500 dark:text-neutral-400 truncate">
										From: {truncateProblem(action.problem_statement, 60)}
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

		{#if isLoading}
			<!-- Loading State -->
			<div class="space-y-4">
				{#each Array(3) as _, i (i)}
					<ShimmerSkeleton type="card" />
				{/each}
			</div>
		{:else if error}
			<!-- Error State -->
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-6">
				<div class="flex items-center gap-3">
					<svg class="w-6 h-6 text-error-600 dark:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<div>
						<h3 class="text-lg font-semibold text-error-900 dark:text-error-200">Error Loading Sessions</h3>
						<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
					</div>
				</div>
				<div class="mt-4">
					<Button variant="danger" size="md" onclick={loadSessions}>
						{#snippet children()}
							Retry
						{/snippet}
					</Button>
				</div>
			</div>
		{:else if sessions.length === 0}
			<!-- Empty State -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-12 text-center">
				<svg class="w-16 h-16 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
				</svg>
				<h2 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-2">
					No meetings yet
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-md mx-auto">
					Get started by creating your first strategic decision meeting. Our AI board will analyze your decision from multiple expert perspectives.
				</p>
				<a href="/meeting/new">
					<Button variant="brand" size="lg">
						{#snippet children()}
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
							</svg>
							Start Your First Meeting
						{/snippet}
					</Button>
				</a>
			</div>
		{:else}
			<!-- Sessions List -->
			<div class="space-y-4">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-xl font-semibold text-neutral-900 dark:text-white">
						Your Meetings ({sessions.length})
					</h2>
					<a href="/meeting/new">
						<Button variant="brand" size="md">
							{#snippet children()}
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
								</svg>
								New Meeting
							{/snippet}
						</Button>
					</a>
				</div>

				{#each sessions as session (session.id)}
					<a
						href="/meeting/{session.id}"
						class="block bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-200"
					>
						<div class="flex items-start justify-between gap-4">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-3 mb-2">
									<span class="px-2.5 py-1 text-xs font-medium rounded-full {getSessionStatusColor(session.status)}">
										{session.status}
									</span>
									<span class="text-xs text-neutral-500 dark:text-neutral-400" title="Created">
										Created {formatCompactRelativeTime(session.created_at)}
									</span>
									{#if session.last_activity_at}
										<span class="text-xs text-neutral-500 dark:text-neutral-400" title="Last activity">
											<span class="inline-block w-1.5 h-1.5 bg-neutral-400 dark:bg-neutral-500 rounded-full mr-1"></span>
											Activity {formatCompactRelativeTime(session.last_activity_at)}
										</span>
									{/if}
									{#if session.status === 'active'}
										<span class="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
											<span class="inline-block w-2 h-2 bg-brand-600 dark:bg-brand-400 rounded-full animate-pulse"></span>
											Active
										</span>
									{/if}
								</div>

								<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
									{truncateProblem(session.problem_statement)}
								</h3>

								<div class="flex items-center gap-4 text-sm text-neutral-600 dark:text-neutral-400">
									{#if session.status !== 'completed'}
										<span class="flex items-center gap-1.5">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
											{humanizePhase(session.phase)}
										</span>
									{/if}
									{#if session.expert_count}
										<span class="flex items-center gap-1.5" title="Experts consulted">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
											</svg>
											{session.expert_count} experts
										</span>
									{/if}
									{#if session.contribution_count}
										<span class="flex items-center gap-1.5" title="Total contributions">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
											</svg>
											{session.contribution_count} insights
										</span>
									{/if}
									{#if session.task_count}
										<span class="flex items-center gap-1.5" title="Action items">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
											</svg>
											{session.task_count} actions
										</span>
									{/if}
									{#if isAdmin && session.cost != null}
										<span class="flex items-center gap-1.5 text-neutral-500 dark:text-neutral-500" title="Meeting cost (admin only)">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
											${session.cost.toFixed(4)}
										</span>
									{/if}
								</div>
							</div>

							<div class="flex items-center gap-2 flex-shrink-0">
								<button
									onclick={(e) => handleDelete(session.id, e)}
									class="p-2 hover:bg-error-50 dark:hover:bg-error-900/20 rounded-lg transition-colors duration-200 group"
									title="Delete meeting"
									aria-label="Delete meeting"
								>
									<svg class="w-5 h-5 text-neutral-400 dark:text-neutral-500 group-hover:text-error-600 dark:group-hover:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
									</svg>
								</button>

								<svg class="w-5 h-5 text-neutral-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
								</svg>
							</div>
						</div>
					</a>
				{/each}
			</div>
		{/if}
	</main>
</div>
