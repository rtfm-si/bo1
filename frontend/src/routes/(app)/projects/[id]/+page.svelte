<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type {
		ProjectDetailResponse,
		ProjectActionsResponse,
		ProjectSessionsResponse,
		ProjectActionSummary,
		ProjectSessionLink,
		ProjectStatus,
		ActionStatus,
		GanttResponse
	} from '$lib/api/types';
	import GanttChart from '$lib/components/projects/GanttChart.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import {
		ArrowLeft,
		CheckCircle2,
		Circle,
		Clock,
		Calendar,
		CalendarDays,
		AlertTriangle,
		Layers,
		Link2,
		Trash2,
		Play,
		Pause,
		Archive,
		Target,
		XCircle,
		GanttChartSquare,
		MessageSquarePlus
	} from 'lucide-svelte';
	import { toast } from '$lib/stores/toast';

	import { formatDate } from '$lib/utils/time-formatting';
	const projectId = $page.params.id!;

	let project = $state<ProjectDetailResponse | null>(null);
	let actions = $state<ProjectActionSummary[]>([]);
	let sessions = $state<ProjectSessionLink[]>([]);
	let ganttData = $state<GanttResponse | null>(null);
	let isLoading = $state(true);
	let isUpdatingStatus = $state(false);
	let ganttViewMode = $state<'Day' | 'Week' | 'Month' | 'Quarter' | 'Year'>('Week');

	// Status configuration
	const projectStatusConfig: Record<
		ProjectStatus,
		{ label: string; icon: typeof Circle; bgColor: string; textColor: string; borderColor: string }
	> = {
		active: {
			label: 'Active',
			icon: Play,
			bgColor: 'bg-success-50 dark:bg-success-900/20',
			textColor: 'text-success-700 dark:text-success-300',
			borderColor: 'border-success-300 dark:border-success-700'
		},
		paused: {
			label: 'Paused',
			icon: Pause,
			bgColor: 'bg-warning-50 dark:bg-warning-900/20',
			textColor: 'text-warning-700 dark:text-warning-300',
			borderColor: 'border-warning-300 dark:border-warning-700'
		},
		completed: {
			label: 'Completed',
			icon: CheckCircle2,
			bgColor: 'bg-brand-50 dark:bg-brand-900/20',
			textColor: 'text-brand-700 dark:text-brand-300',
			borderColor: 'border-brand-300 dark:border-brand-700'
		},
		archived: {
			label: 'Archived',
			icon: Archive,
			bgColor: 'bg-neutral-50 dark:bg-neutral-800',
			textColor: 'text-neutral-500 dark:text-neutral-400',
			borderColor: 'border-neutral-300 dark:border-neutral-600'
		}
	};

	// Action status configuration
	const actionStatusConfig: Record<ActionStatus, { label: string; color: string }> = {
		todo: { label: 'To Do', color: 'bg-neutral-200 dark:bg-neutral-700' },
		in_progress: { label: 'In Progress', color: 'bg-brand-500' },
		blocked: { label: 'Blocked', color: 'bg-error-500' },
		in_review: { label: 'In Review', color: 'bg-purple-500' },
		done: { label: 'Done', color: 'bg-success-500' },
		cancelled: { label: 'Cancelled', color: 'bg-neutral-400' },
		failed: { label: 'Failed', color: 'bg-error-500' },
		abandoned: { label: 'Abandoned', color: 'bg-neutral-400' },
		replanned: { label: 'Replanned', color: 'bg-warning-500' }
	};

	// Priority configuration
	const priorityConfig: Record<string, { label: string; color: string; bg: string }> = {
		high: {
			label: 'High',
			color: 'text-error-600 dark:text-error-400',
			bg: 'bg-error-100 dark:bg-error-900/30'
		},
		medium: {
			label: 'Medium',
			color: 'text-warning-600 dark:text-warning-400',
			bg: 'bg-warning-100 dark:bg-warning-900/30'
		},
		low: {
			label: 'Low',
			color: 'text-neutral-600 dark:text-neutral-400',
			bg: 'bg-neutral-100 dark:bg-neutral-800'
		}
	};


	function getPriorityConfig(priority: string) {
		const key = priority?.toLowerCase() || 'medium';
		return priorityConfig[key] || priorityConfig.medium;
	}

	function hasAnyDates(p: ProjectDetailResponse): boolean {
		return !!(
			p.target_start_date ||
			p.target_end_date ||
			p.estimated_start_date ||
			p.estimated_end_date ||
			p.actual_start_date ||
			p.actual_end_date
		);
	}

	async function loadProject() {
		try {
			isLoading = true;

			const [projectData, actionsData, sessionsData, ganttDataResult] = await Promise.all([
				apiClient.getProject(projectId),
				apiClient.getProjectActions(projectId),
				apiClient.getProjectSessions(projectId),
				apiClient.getProjectGantt(projectId)
			]);

			project = projectData;
			actions = actionsData.actions;
			sessions = sessionsData.sessions;
			ganttData = ganttDataResult;
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Failed to load project');
		} finally {
			isLoading = false;
		}
	}

	async function updateProjectStatus(newStatus: ProjectStatus) {
		if (!project || project.status === newStatus || isUpdatingStatus) return;

		try {
			isUpdatingStatus = true;
			const updated = await apiClient.updateProjectStatus(projectId, newStatus);
			project = updated;
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Failed to update status');
		} finally {
			isUpdatingStatus = false;
		}
	}

	async function removeActionFromProject(actionId: string, event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();

		if (!confirm('Remove this action from the project?')) return;

		try {
			await apiClient.removeActionFromProject(projectId, actionId);
			actions = actions.filter((a) => a.id !== actionId);
			// Update project counts
			if (project) {
				project = { ...project, total_actions: project.total_actions - 1 };
			}
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Failed to remove action');
		}
	}

	async function unlinkSession(sessionId: string) {
		if (!confirm('Unlink this meeting from the project?')) return;

		try {
			await apiClient.unlinkSessionFromProject(projectId, sessionId);
			sessions = sessions.filter((s) => s.session_id !== sessionId);
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Failed to unlink session');
		}
	}

	function goBack() {
		goto('/projects');
	}

	function goToAction(actionId: string) {
		goto(`/actions/${actionId}`);
	}

	function goToMeeting(sessionId: string) {
		goto(`/meeting/${sessionId}`);
	}

	function handleGanttTaskClick(actionId: string) {
		goToAction(actionId);
	}

	async function handleGanttDateChange(actionId: string, start: Date, end: Date): Promise<void> {
		// Format dates as YYYY-MM-DD
		const formatDate = (d: Date) => d.toISOString().split('T')[0];
		try {
			await apiClient.updateActionDates(actionId, {
				target_start_date: formatDate(start),
				target_end_date: formatDate(end)
			});
			// Reload Gantt data to show updated cascade effects
			const [ganttResult] = await Promise.all([
				apiClient.getProjectGantt(projectId)
			]);
			ganttData = ganttResult;
		} catch (err) {
			console.error('Failed to update action dates:', err);
		}
	}

	function setGanttViewMode(mode: string) {
		ganttViewMode = mode as 'Day' | 'Week' | 'Month' | 'Quarter' | 'Year';
	}

	function getProgressColor(progress: number): string {
		if (progress >= 100) return 'bg-success-500';
		if (progress >= 75) return 'bg-brand-500';
		if (progress >= 50) return 'bg-warning-500';
		return 'bg-neutral-400';
	}

	onMount(() => {
		loadProject();
	});
</script>

<svelte:head>
	<title>{project?.name ?? 'Project'} | Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">
	<!-- Sticky Header -->
	<div class="sticky top-0 z-10 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-md border-b border-neutral-200 dark:border-neutral-800">
		<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-4">
			<div class="flex items-center gap-4">
				<button
					onclick={goBack}
					class="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
				>
					<ArrowLeft class="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
				</button>
				<div class="flex-1 min-w-0">
					{#if isLoading}
						<div class="animate-pulse bg-neutral-200 dark:bg-neutral-700 rounded h-7 w-48"></div>
					{:else if project}
						<div class="flex items-center gap-3">
							{#if project.icon}
								<span class="text-2xl">{project.icon}</span>
							{:else}
								<span
									class="w-8 h-8 rounded flex items-center justify-center text-sm font-bold"
									style="background-color: {project.color || '#6366f1'}20; color: {project.color || '#6366f1'}"
								>
									{project.name.charAt(0).toUpperCase()}
								</span>
							{/if}
							<h1 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 truncate">
								{project.name}
							</h1>
						</div>
					{:else}
						<h1 class="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
							Project Not Found
						</h1>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-6">
		{#if isLoading}
			<!-- Loading skeleton -->
			<div class="space-y-6">
				<ShimmerSkeleton type="card" />
				<ShimmerSkeleton type="card" />
				<ShimmerSkeleton type="card" />
			</div>
		{:else if project}
			<div class="space-y-6">
				<!-- Status & Progress Card -->
				<div class="bg-white dark:bg-neutral-800 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-700">
					<div class="flex flex-wrap items-center justify-between gap-4 mb-6">
						<!-- Current Status -->
						<div class="flex items-center gap-3">
							<span class="text-sm font-medium text-neutral-500 dark:text-neutral-400">Status:</span>
							<div class={`flex items-center gap-2 px-3 py-1.5 rounded-full ${projectStatusConfig[project.status].bgColor} ${projectStatusConfig[project.status].textColor} border ${projectStatusConfig[project.status].borderColor}`}>
								{#if project.status === 'active'}
									<Play class="w-4 h-4" />
								{:else if project.status === 'paused'}
									<Pause class="w-4 h-4" />
								{:else if project.status === 'completed'}
									<CheckCircle2 class="w-4 h-4" />
								{:else}
									<Archive class="w-4 h-4" />
								{/if}
								<span class="text-sm font-medium">{projectStatusConfig[project.status].label}</span>
							</div>
						</div>

						<!-- Action Buttons -->
						<div class="flex items-center gap-2">
							<!-- New Meeting Button -->
							{#if project.status !== 'archived'}
								<Button
									variant="brand"
									size="sm"
									onclick={() => goto(`/meeting/new?project_id=${projectId}`)}
								>
									<MessageSquarePlus class="w-4 h-4 mr-1" />
									New Meeting
								</Button>
							{/if}
							<!-- Status Change Buttons -->
							{#if project.status !== 'active'}
								<Button
									variant="ghost"
									size="sm"
									onclick={() => updateProjectStatus('active')}
									disabled={isUpdatingStatus}
								>
									<Play class="w-4 h-4 mr-1" />
									Activate
								</Button>
							{/if}
							{#if project.status === 'active'}
								<Button
									variant="ghost"
									size="sm"
									onclick={() => updateProjectStatus('paused')}
									disabled={isUpdatingStatus}
								>
									<Pause class="w-4 h-4 mr-1" />
									Pause
								</Button>
							{/if}
							{#if project.status !== 'completed' && project.status !== 'archived'}
								<Button
									variant="secondary"
									size="sm"
									onclick={() => updateProjectStatus('completed')}
									disabled={isUpdatingStatus}
								>
									<CheckCircle2 class="w-4 h-4 mr-1" />
									Complete
								</Button>
							{/if}
						</div>
					</div>

					<!-- Progress Bar -->
					<div>
						<div class="flex items-center justify-between text-sm mb-2">
							<span class="text-neutral-600 dark:text-neutral-400">Progress</span>
							<span class="font-medium text-neutral-900 dark:text-white">
								{project.progress_percent}% ({project.completed_actions}/{project.total_actions} actions)
							</span>
						</div>
						<div class="w-full h-3 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
							<div
								class="h-full rounded-full transition-all duration-300 {getProgressColor(project.progress_percent)}"
								style="width: {project.progress_percent}%"
							></div>
						</div>
					</div>
				</div>

				<!-- Description -->
				{#if project.description}
					<div class="bg-white dark:bg-neutral-800 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-700">
						<h2 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-3">
							Description
						</h2>
						<p class="text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
							{project.description}
						</p>
					</div>
				{/if}

				<!-- Dates & Schedule -->
				{#if hasAnyDates(project)}
					<div class="bg-white dark:bg-neutral-800 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-700">
						<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-4">
							<CalendarDays class="w-4 h-4 text-brand-500" />
							Schedule
						</h2>

						<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
							{#if project.target_start_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
									<Calendar class="w-5 h-5 text-warning-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Target Start</div>
										<div class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
											{formatDate(project.target_start_date)}
										</div>
									</div>
								</div>
							{/if}

							{#if project.target_end_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
									<Calendar class="w-5 h-5 text-warning-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Target End</div>
										<div class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
											{formatDate(project.target_end_date)}
										</div>
									</div>
								</div>
							{/if}

							{#if project.estimated_start_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-brand-50 dark:bg-brand-900/20">
									<CalendarDays class="w-5 h-5 text-brand-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-brand-600 dark:text-brand-400 uppercase">Est. Start</div>
										<div class="text-sm font-medium text-brand-900 dark:text-brand-100">
											{formatDate(project.estimated_start_date)}
										</div>
									</div>
								</div>
							{/if}

							{#if project.estimated_end_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-brand-50 dark:bg-brand-900/20">
									<CalendarDays class="w-5 h-5 text-brand-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-brand-600 dark:text-brand-400 uppercase">Est. End</div>
										<div class="text-sm font-medium text-brand-900 dark:text-brand-100">
											{formatDate(project.estimated_end_date)}
										</div>
									</div>
								</div>
							{/if}

							{#if project.actual_start_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-success-50 dark:bg-success-900/20">
									<CheckCircle2 class="w-5 h-5 text-success-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-success-600 dark:text-success-400 uppercase">Started</div>
										<div class="text-sm font-medium text-success-900 dark:text-success-100">
											{formatDate(project.actual_start_date)}
										</div>
									</div>
								</div>
							{/if}

							{#if project.actual_end_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-success-50 dark:bg-success-900/20">
									<CheckCircle2 class="w-5 h-5 text-success-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-success-600 dark:text-success-400 uppercase">Completed</div>
										<div class="text-sm font-medium text-success-900 dark:text-success-100">
											{formatDate(project.actual_end_date)}
										</div>
									</div>
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<!-- Gantt Chart -->
				{#if ganttData && ganttData.actions.length > 0}
					<div class="bg-white dark:bg-neutral-800 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-700">
						<div class="flex items-center justify-between mb-4">
							<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider">
								<GanttChartSquare class="w-4 h-4 text-brand-500" />
								Timeline
							</h2>
							<div class="flex items-center gap-1 bg-neutral-100 dark:bg-neutral-700 rounded-lg p-1">
								{#each ['Day', 'Week', 'Month', 'Quarter'] as mode (mode)}
									<button
										onclick={() => setGanttViewMode(mode)}
										class="px-3 py-1 text-xs font-medium rounded-md transition-colors {ganttViewMode === mode
											? 'bg-white dark:bg-neutral-600 text-neutral-900 dark:text-white shadow-sm'
											: 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
									>
										{mode}
									</button>
								{/each}
							</div>
						</div>

						<GanttChart
							data={ganttData}
							viewMode={ganttViewMode}
							onTaskClick={handleGanttTaskClick}
							onDateChange={handleGanttDateChange}
						/>
					</div>
				{/if}

				<!-- Actions -->
				<div class="bg-white dark:bg-neutral-800 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between mb-4">
						<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider">
							<Layers class="w-4 h-4 text-brand-500" />
							Actions ({actions.length})
						</h2>
					</div>

					{#if actions.length === 0}
						<div class="text-center py-8">
							<Target class="w-12 h-12 text-neutral-300 dark:text-neutral-600 mx-auto mb-3" />
							<p class="text-neutral-500 dark:text-neutral-400">
								No actions assigned to this project yet.
							</p>
							<p class="text-sm text-neutral-400 dark:text-neutral-500 mt-1">
								Actions can be assigned from the Actions page.
							</p>
						</div>
					{:else}
						<div class="space-y-3">
							{#each actions as action (action.id)}
								<div
									class="flex items-center justify-between gap-4 p-4 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-700 transition-colors cursor-pointer"
									role="button"
									tabindex="0"
									onclick={() => goToAction(action.id)}
									onkeydown={(e) => e.key === 'Enter' && goToAction(action.id)}
								>
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2 mb-1">
											<span class={`w-2 h-2 rounded-full ${actionStatusConfig[action.status].color}`}></span>
											<span class="font-medium text-neutral-900 dark:text-white truncate">
												{action.title}
											</span>
										</div>
										<div class="flex items-center gap-3 text-sm text-neutral-500 dark:text-neutral-400">
											<span class={`px-2 py-0.5 rounded text-xs font-medium ${getPriorityConfig(action.priority).bg} ${getPriorityConfig(action.priority).color}`}>
												{getPriorityConfig(action.priority).label}
											</span>
											<span>{actionStatusConfig[action.status].label}</span>
											{#if action.timeline}
												<span class="flex items-center gap-1">
													<Clock class="w-3 h-3" />
													{action.timeline}
												</span>
											{/if}
										</div>
									</div>
									<button
										onclick={(e) => removeActionFromProject(action.id, e)}
										class="p-2 hover:bg-error-50 dark:hover:bg-error-900/20 rounded-lg transition-colors group"
										title="Remove from project"
										aria-label="Remove action from project"
									>
										<XCircle class="w-4 h-4 text-neutral-400 group-hover:text-error-500" />
									</button>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Linked Sessions -->
				<div class="bg-white dark:bg-neutral-800 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between mb-4">
						<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider">
							<Link2 class="w-4 h-4 text-brand-500" />
							Linked Meetings ({sessions.length})
						</h2>
					</div>

					{#if sessions.length === 0}
						<div class="text-center py-8">
							<Link2 class="w-12 h-12 text-neutral-300 dark:text-neutral-600 mx-auto mb-3" />
							<p class="text-neutral-500 dark:text-neutral-400">
								No meetings linked to this project yet.
							</p>
						</div>
					{:else}
						<div class="space-y-3">
							{#each sessions as session (session.session_id)}
								<div class="flex items-center justify-between gap-4 p-4 rounded-lg border border-neutral-200 dark:border-neutral-700">
									<button
										onclick={() => goToMeeting(session.session_id)}
										class="flex-1 min-w-0 text-left hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
									>
										<div class="font-medium text-neutral-900 dark:text-white truncate">
											{(session as ProjectSessionLink & { problem_statement?: string }).problem_statement ?? 'Untitled Meeting'}
										</div>
										<div class="flex items-center gap-3 text-sm text-neutral-500 dark:text-neutral-400 mt-1">
											<span class="capitalize">{session.relationship.replace('_', ' ')}</span>
											<span>{formatDate((session as ProjectSessionLink & { created_at?: string }).created_at ?? null)}</span>
										</div>
									</button>
									<button
										onclick={() => unlinkSession(session.session_id)}
										class="p-2 hover:bg-error-50 dark:hover:bg-error-900/20 rounded-lg transition-colors group"
										title="Unlink meeting"
										aria-label="Unlink meeting from project"
									>
										<Trash2 class="w-4 h-4 text-neutral-400 group-hover:text-error-500" />
									</button>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Back Button -->
				<div class="pt-4">
					<Button variant="ghost" onclick={goBack}>
						<ArrowLeft class="w-4 h-4 mr-2" />
						Back to Projects
					</Button>
				</div>
			</div>
		{/if}
	</div>
</div>
