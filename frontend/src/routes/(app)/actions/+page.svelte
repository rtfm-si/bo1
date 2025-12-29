<script lang="ts">
	/**
	 * Actions Page - Global Kanban/Gantt board for all user actions
	 *
	 * Displays all actions from completed meetings.
	 * Features:
	 * - Kanban and Gantt views
	 * - Filter by meeting, project, and tags
	 * - Click-through to action details
	 */
	import { onMount, tick } from 'svelte';
	import { goto, beforeNavigate } from '$app/navigation';
	import { page } from '$app/stores';
	import { apiClient } from '$lib/api/client';
	import { getPersistedTourPage, setTourActive, clearTourPage } from '$lib/stores/tour';
	import { startActionsPageTour, injectTourStyles, destroyActiveTour } from '$lib/tour/onboarding-tour';
	import type {
		AllActionsResponse,
		TaskWithSessionContext,
		ActionStatus,
		TagResponse,
		ProjectDetailResponse,
		GlobalGanttResponse,
		KanbanColumn
	} from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import GlobalGanttChart from '$lib/components/actions/GlobalGanttChart.svelte';
	import KanbanBoard from '$lib/components/actions/KanbanBoard.svelte';
	import { getDueDateStatus } from '$lib/utils/due-dates';
	import { toast } from '$lib/stores/toast';

	// Cleanup tour popup on navigation to prevent persistence
	beforeNavigate(() => {
		destroyActiveTour();
	});

	// Filter state
	let selectedMeetingId = $state<string | null>(null);
	let selectedProjectId = $state<string | null>(null);
	let selectedTagIds = $state<string[]>([]);
	let selectedStatus = $state<ActionStatus | 'all'>('all');
	let selectedDueDate = $state<'all' | 'overdue' | 'due-today' | 'due-soon' | 'no-date'>('all');
	// Specific date filter from URL (YYYY-MM-DD format)
	let selectedSpecificDate = $state<string | null>(null);

	type DueDateFilterOption = 'all' | 'overdue' | 'due-today' | 'due-soon' | 'no-date';

	// View mode state (kanban or gantt)
	let viewMode = $state<'kanban' | 'gantt'>('kanban');
	let ganttViewMode = $state<'Day' | 'Week' | 'Month'>('Week');

	// Loading states
	let isLoading = $state(true);

	// Data
	let actionsData = $state<AllActionsResponse | null>(null);
	let ganttData = $state<GlobalGanttResponse | null>(null);
	let projects = $state<ProjectDetailResponse[]>([]);
	let tags = $state<TagResponse[]>([]);
	let kanbanColumns = $state<KanbanColumn[] | undefined>(undefined);
	let showTagDropdown = $state(false);

	// Fetch all data
	async function fetchData() {
		isLoading = true;
		try {
			// Build filter params
			const params: Record<string, string | undefined> = {};
			if (selectedProjectId) params.project_id = selectedProjectId;
			if (selectedMeetingId) params.session_id = selectedMeetingId;
			if (selectedTagIds.length > 0) params.tag_ids = selectedTagIds.join(',');

			// Fetch actions, projects, tags, and kanban columns in parallel
			const [actionsRes, projectsRes, tagsRes, columnsRes] = await Promise.all([
				apiClient.getAllActions(params),
				apiClient.listProjects({ status: 'active' }),
				apiClient.getTags(),
				apiClient.getKanbanColumns().catch(() => null) // Graceful fallback
			]);

			actionsData = actionsRes;
			projects = projectsRes.projects;
			tags = tagsRes.tags;
			kanbanColumns = columnsRes?.columns;

			// If gantt view is active, fetch gantt data too
			if (viewMode === 'gantt') {
				ganttData = await apiClient.getGlobalGantt(params);
			}
		} catch (err) {
			console.error('Failed to fetch actions:', err);
			toast.error(err instanceof Error ? err.message : 'Failed to load actions');
		} finally {
			isLoading = false;
		}
	}

	// Fetch gantt data when switching to gantt view
	async function fetchGanttData() {
		try {
			const params: Record<string, string | undefined> = {};
			if (selectedProjectId) params.project_id = selectedProjectId;
			if (selectedMeetingId) params.session_id = selectedMeetingId;
			if (selectedTagIds.length > 0) params.tag_ids = selectedTagIds.join(',');
			ganttData = await apiClient.getGlobalGantt(params);
		} catch (err) {
			console.error('Failed to fetch gantt data:', err);
		}
	}

	// Watch for view mode changes
	$effect(() => {
		if (viewMode === 'gantt' && !ganttData && actionsData) {
			fetchGanttData();
		}
	});

	// Get unique meetings for filter dropdown
	const meetings = $derived<{ id: string; title: string; taskCount: number }[]>(
		actionsData?.sessions
			? actionsData.sessions.map((s) => {
					const statement = String(s.problem_statement ?? '');
					return {
						id: s.session_id as string,
						title: statement.length > 50 ? statement.substring(0, 50) + '...' : statement,
						taskCount: s.task_count as number
					};
				})
			: []
	);

	// Get all tasks flattened with session context (filtered by selected meeting, status, due date - client-side)
	const allTasks = $derived.by<TaskWithSessionContext[]>(() => {
		if (!actionsData?.sessions) return [];
		let tasks = actionsData.sessions.flatMap((s) => s.tasks as TaskWithSessionContext[]);

		// Meeting filter (also applied server-side, but filter client-side for UI responsiveness)
		if (selectedMeetingId) {
			tasks = tasks.filter((t) => t.session_id === selectedMeetingId);
		}

		// Status filter
		if (selectedStatus !== 'all') {
			tasks = tasks.filter((t) => t.status === selectedStatus);
		}

		// Specific date filter (from URL ?due_date=YYYY-MM-DD)
		if (selectedSpecificDate) {
			tasks = tasks.filter((t) => {
				if (!t.suggested_completion_date) return false;
				const taskDate = t.suggested_completion_date.split('T')[0];
				return taskDate === selectedSpecificDate;
			});
		}
		// Due date filter (dropdown)
		else if (selectedDueDate !== 'all') {
			tasks = tasks.filter((t) => {
				const status = getDueDateStatus(t.suggested_completion_date);
				switch (selectedDueDate) {
					case 'overdue': return status === 'overdue';
					case 'due-today': return status === 'due-today';
					case 'due-soon': return status === 'due-soon';
					case 'no-date': return status === null;
					default: return true;
				}
			});
		}

		return tasks;
	});

	// Filter tasks by status
	function getTasksByStatus(status: ActionStatus) {
		return allTasks.filter((t) => t.status === status);
	}

	// Clear all filters
	function clearFilters() {
		selectedMeetingId = null;
		selectedProjectId = null;
		selectedTagIds = [];
		selectedStatus = 'all';
		selectedDueDate = 'all';
		selectedSpecificDate = null;
		// Clear URL params
		goto('/actions', { replaceState: true });
		fetchData();
	}

	// Toggle tag selection
	function toggleTag(tagId: string) {
		if (selectedTagIds.includes(tagId)) {
			selectedTagIds = selectedTagIds.filter((id) => id !== tagId);
		} else {
			selectedTagIds = [...selectedTagIds, tagId];
		}
	}

	// Apply filters
	function applyFilters() {
		showTagDropdown = false;
		fetchData();
	}

	// Selection state for bulk actions
	let selectedTaskIds = $state<Set<string>>(new Set());
	let isBulkUpdating = $state(false);

	// Selection helper functions
	function toggleTaskSelection(taskId: string, event: Event) {
		event.preventDefault();
		event.stopPropagation();
		const newSet = new Set(selectedTaskIds);
		if (newSet.has(taskId)) {
			newSet.delete(taskId);
		} else {
			newSet.add(taskId);
		}
		selectedTaskIds = newSet;
	}

	function selectAllVisible() {
		const newSet = new Set(selectedTaskIds);
		for (const task of allTasks) {
			newSet.add(task.id);
		}
		selectedTaskIds = newSet;
	}

	function deselectAll() {
		selectedTaskIds = new Set();
	}

	const selectedCount = $derived(selectedTaskIds.size);
	const allVisibleSelected = $derived(
		allTasks.length > 0 && allTasks.every(t => selectedTaskIds.has(t.id))
	);

	// Bulk status update
	async function handleBulkStatusChange(newStatus: ActionStatus) {
		if (selectedTaskIds.size === 0) return;
		// Confirm if updating more than 1 item
		if (selectedTaskIds.size > 1) {
			const confirmed = confirm(`Update status of ${selectedTaskIds.size} actions to "${newStatus}"?`);
			if (!confirmed) return;
		}
		isBulkUpdating = true;
		try {
			const tasksToUpdate = allTasks.filter(t => selectedTaskIds.has(t.id));
			await Promise.all(
				tasksToUpdate.map(t => apiClient.updateActionStatus(t.id, newStatus))
			);
			selectedTaskIds = new Set();
			await fetchData();
		} catch (err) {
			console.error('Failed to bulk update tasks:', err);
			toast.error(err instanceof Error ? err.message : 'Failed to update actions');
		} finally {
			isBulkUpdating = false;
		}
	}

	// Status update handler
	let deletingTaskId = $state<string | null>(null);
	let isKanbanLoading = $state(false);

	// Handler for KanbanBoard drag-drop status changes
	async function handleKanbanStatusChange(
		taskId: string,
		newStatus: ActionStatus
	) {
		isKanbanLoading = true;
		try {
			await apiClient.updateActionStatus(taskId, newStatus);
			await fetchData();
		} catch (err) {
			console.error('Failed to update task status:', err);
			toast.error(err instanceof Error ? err.message : 'Failed to update action status');
		} finally {
			isKanbanLoading = false;
		}
	}

	async function handleDelete(taskId: string) {
		deletingTaskId = taskId;
		try {
			await apiClient.deleteAction(taskId);
			await fetchData();
		} catch (err) {
			console.error('Failed to delete action:', err);
			toast.error(err instanceof Error ? err.message : 'Failed to delete action');
		} finally {
			deletingTaskId = null;
		}
	}

	// Navigate to action detail
	function handleTaskClick(actionId: string) {
		goto(`/actions/${actionId}`);
	}

	// Check if any filters are active
	const hasActiveFilters = $derived(
		selectedMeetingId !== null || selectedProjectId !== null || selectedTagIds.length > 0 ||
		selectedStatus !== 'all' || selectedDueDate !== 'all' || selectedSpecificDate !== null
	);

	onMount(async () => {
		// Read specific date filter from URL
		const dueDateParam = $page.url.searchParams.get('due_date');
		if (dueDateParam && /^\d{4}-\d{2}-\d{2}$/.test(dueDateParam)) {
			selectedSpecificDate = dueDateParam;
		}

		await fetchData();

		// Check if we should continue the tour on this page
		const tourPage = getPersistedTourPage();
		if (tourPage === 'actions') {
			// Wait for DOM to settle
			await tick();
			injectTourStyles();
			setTourActive(true);
			startActionsPageTour(() => {
				setTourActive(false);
				clearTourPage();
			});
		}
	});
</script>

<svelte:head>
	<title>Actions - Board of One</title>
</svelte:head>

<div
	class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800"
>
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Header with stats -->
		<div class="mb-8">
			<div class="flex items-center justify-between mb-4">
				<div>
					<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">Actions</h1>
					<p class="text-neutral-600 dark:text-neutral-400">
						Track and manage actions from your meetings
					</p>
				</div>
				<!-- View Toggle -->
				<div class="flex items-center gap-4" data-tour="view-toggle">
					{#if viewMode === 'gantt'}
						<select
							bind:value={ganttViewMode}
							class="px-2 py-1 text-sm bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-lg"
						>
							<option value="Day">Day</option>
							<option value="Week">Week</option>
							<option value="Month">Month</option>
						</select>
					{/if}
					<div class="flex items-center gap-1 p-1 bg-neutral-100 dark:bg-neutral-800 rounded-lg">
						<button
							onclick={() => viewMode = 'kanban'}
							class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {viewMode === 'kanban' ? 'bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white shadow-sm' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
						>
							<svg class="w-4 h-4 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
							</svg>
							Kanban
						</button>
						<button
							onclick={() => viewMode = 'gantt'}
							class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {viewMode === 'gantt' ? 'bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white shadow-sm' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
						>
							<svg class="w-4 h-4 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
							</svg>
							Gantt
						</button>
					</div>
				</div>
			</div>

			<!-- Specific Date Filter Badge (from URL) -->
			{#if selectedSpecificDate}
				<div class="mb-4 flex items-center gap-2 p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700 rounded-lg">
					<svg class="w-4 h-4 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
					</svg>
					<span class="text-sm font-medium text-brand-700 dark:text-brand-300">
						Showing actions due on {new Date(selectedSpecificDate + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
					</span>
					<button
						onclick={clearFilters}
						class="ml-auto text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300"
					>
						Clear filter
					</button>
				</div>
			{/if}

			<!-- Filters Row -->
			{#if actionsData && !isLoading}
				<div class="mb-4 flex flex-wrap items-center gap-3 p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700" data-tour="actions-filters">
					<!-- Meeting Filter -->
					<div class="flex items-center gap-2">
						<label for="meeting-filter" class="text-sm font-medium text-neutral-700 dark:text-neutral-300">
							Meeting:
						</label>
						<select
							id="meeting-filter"
							bind:value={selectedMeetingId}
							onchange={() => applyFilters()}
							class="px-3 py-2 bg-neutral-50 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 rounded-lg text-sm text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 min-w-[180px]"
						>
							<option value={null}>All meetings</option>
							{#each meetings as meeting (meeting.id)}
								<option value={meeting.id}>
									{meeting.title} ({meeting.taskCount})
								</option>
							{/each}
						</select>
					</div>

					<!-- Status Filter -->
					<div class="flex items-center gap-2">
						<label for="status-filter" class="text-sm font-medium text-neutral-700 dark:text-neutral-300">
							Status:
						</label>
						<select
							id="status-filter"
							bind:value={selectedStatus}
							class="px-3 py-2 bg-neutral-50 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 rounded-lg text-sm text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 min-w-[140px]"
						>
							<option value="all">All statuses</option>
							<option value="todo">To Do</option>
							<option value="in_progress">In Progress</option>
							<option value="blocked">Blocked</option>
							<option value="in_review">In Review</option>
							<option value="done">Done</option>
							<option value="cancelled">Cancelled</option>
							<option value="failed">Failed</option>
							<option value="abandoned">Abandoned</option>
							<option value="replanned">Replanned</option>
						</select>
					</div>

					<!-- Due Date Filter -->
					<div class="flex items-center gap-2">
						<label for="due-date-filter" class="text-sm font-medium text-neutral-700 dark:text-neutral-300">
							Due:
						</label>
						<select
							id="due-date-filter"
							bind:value={selectedDueDate}
							class="px-3 py-2 bg-neutral-50 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 rounded-lg text-sm text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 min-w-[140px]"
						>
							<option value="all">All dates</option>
							<option value="overdue">Overdue</option>
							<option value="due-today">Due Today</option>
							<option value="due-soon">Due Soon</option>
							<option value="no-date">No Due Date</option>
						</select>
					</div>

					<!-- Project Filter -->
					{#if projects.length > 0}
						<div class="flex items-center gap-2">
							<label for="project-filter" class="text-sm font-medium text-neutral-700 dark:text-neutral-300">
								Project:
							</label>
							<select
								id="project-filter"
								bind:value={selectedProjectId}
								onchange={() => applyFilters()}
								class="px-3 py-2 bg-neutral-50 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 rounded-lg text-sm text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 min-w-[180px]"
							>
								<option value={null}>All projects</option>
								{#each projects as project (project.id)}
									<option value={project.id}>
										{project.name}
									</option>
								{/each}
							</select>
						</div>
					{/if}

					<!-- Tags Filter -->
					{#if tags.length > 0}
						<div class="relative">
							<button
								onclick={() => showTagDropdown = !showTagDropdown}
								class="flex items-center gap-2 px-3 py-2 bg-neutral-50 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 rounded-lg text-sm text-neutral-900 dark:text-white hover:border-brand-500 transition-colors"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
								</svg>
								Tags
								{#if selectedTagIds.length > 0}
									<span class="px-1.5 py-0.5 bg-brand-500 text-white text-xs rounded-full">
										{selectedTagIds.length}
									</span>
								{/if}
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
								</svg>
							</button>

							{#if showTagDropdown}
								<div class="absolute top-full left-0 mt-1 w-64 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg z-50 p-3">
									<div class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
										Select tags (AND logic)
									</div>
									<div class="max-h-48 overflow-y-auto space-y-1">
										{#each tags as tag (tag.id)}
											<label class="flex items-center gap-2 p-2 rounded hover:bg-neutral-50 dark:hover:bg-neutral-700 cursor-pointer">
												<input
													type="checkbox"
													checked={selectedTagIds.includes(tag.id)}
													onchange={() => toggleTag(tag.id)}
													class="rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
												/>
												<span
													class="w-3 h-3 rounded-full flex-shrink-0"
													style="background-color: {tag.color}"
												></span>
												<span class="text-sm text-neutral-900 dark:text-white truncate">
													{tag.name}
												</span>
												<span class="text-xs text-neutral-500 ml-auto">
													{tag.action_count}
												</span>
											</label>
										{/each}
									</div>
									<div class="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700 flex justify-end gap-2">
										<button
											onclick={() => { selectedTagIds = []; showTagDropdown = false; applyFilters(); }}
											class="px-3 py-1 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white"
										>
											Clear
										</button>
										<button
											onclick={() => applyFilters()}
											class="px-3 py-1 text-sm bg-brand-600 text-white rounded hover:bg-brand-700"
										>
											Apply
										</button>
									</div>
								</div>
							{/if}
						</div>
					{/if}

					<!-- Clear Filters Button -->
					{#if hasActiveFilters}
						<button
							onclick={clearFilters}
							class="flex items-center gap-1 px-3 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white transition-colors"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
							</svg>
							Clear filters
						</button>
					{/if}

					<!-- Select All / Active filter count -->
					<div class="ml-auto flex items-center gap-3">
						{#if viewMode === 'kanban' && allTasks.length > 0}
							<label class="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400 cursor-pointer">
								<input
									type="checkbox"
									checked={allVisibleSelected}
									onchange={() => allVisibleSelected ? deselectAll() : selectAllVisible()}
									class="rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
								/>
								Select all
							</label>
						{/if}
						<span class="text-sm text-neutral-500 dark:text-neutral-400">
							{actionsData.total_tasks} actions
						</span>
					</div>
				</div>
			{/if}

			<!-- Bulk Action Bar -->
			{#if selectedCount > 0}
				<div class="mb-4 flex items-center gap-4 p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700 rounded-lg" data-tour="bulk-actions">
					<span class="text-sm font-medium text-brand-700 dark:text-brand-300">
						{selectedCount} item{selectedCount !== 1 ? 's' : ''} selected
					</span>
					<div class="flex items-center gap-2">
						<button
							onclick={() => handleBulkStatusChange('done')}
							disabled={isBulkUpdating}
							class="px-3 py-1.5 text-sm font-medium bg-success-600 hover:bg-success-700 text-white rounded transition-colors disabled:opacity-50"
						>
							{isBulkUpdating ? 'Updating...' : 'Mark Complete'}
						</button>
						<button
							onclick={() => handleBulkStatusChange('in_progress')}
							disabled={isBulkUpdating}
							class="px-3 py-1.5 text-sm font-medium bg-warning-600 hover:bg-warning-700 text-white rounded transition-colors disabled:opacity-50"
						>
							Start
						</button>
						<button
							onclick={() => handleBulkStatusChange('todo')}
							disabled={isBulkUpdating}
							class="px-3 py-1.5 text-sm font-medium bg-neutral-600 hover:bg-neutral-700 text-white rounded transition-colors disabled:opacity-50"
						>
							To Do
						</button>
					</div>
					<button
						onclick={deselectAll}
						class="ml-auto text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300"
					>
						Clear selection
					</button>
				</div>
			{/if}

			<!-- Quick Stats -->
			{#if actionsData && !isLoading}
				<div class="grid grid-cols-3 gap-4 mb-6">
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="text-2xl font-bold text-neutral-900 dark:text-white">
							{getTasksByStatus('todo').length}
						</div>
						<div class="text-sm text-neutral-500 dark:text-neutral-400">To Do</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="text-2xl font-bold text-warning-600 dark:text-warning-400">
							{getTasksByStatus('in_progress').length}
						</div>
						<div class="text-sm text-neutral-500 dark:text-neutral-400">In Progress</div>
					</div>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
					>
						<div class="text-2xl font-bold text-success-600 dark:text-success-400">
							{getTasksByStatus('done').length}
						</div>
						<div class="text-sm text-neutral-500 dark:text-neutral-400">Completed</div>
					</div>
				</div>
			{/if}
		</div>

		{#if isLoading}
			<!-- Loading State - Kanban skeleton -->
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				{#each Array(3) as _, i (i)}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4"
					>
						<div class="flex items-center gap-2 mb-4">
							<div class="h-5 w-20 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse"></div>
							<div class="h-5 w-6 bg-neutral-200 dark:bg-neutral-700 rounded-full animate-pulse"></div>
						</div>
						<div class="space-y-3">
							{#each Array(3) as _, j (j)}
								<ShimmerSkeleton type="list-item" />
							{/each}
						</div>
					</div>
				{/each}
			</div>
		{:else if !actionsData || actionsData.total_tasks === 0}
			<!-- Empty State -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-12 text-center"
			>
				<svg
					class="w-16 h-16 mx-auto text-neutral-400 dark:text-neutral-500 mb-4"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="1.5"
						d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
					/>
				</svg>
				<h2 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-2">
					{hasActiveFilters ? 'No matching actions' : 'No actions yet'}
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-md mx-auto">
					{#if hasActiveFilters}
						Try adjusting your filters to see more actions.
					{:else}
						Complete a meeting and extract action items to see them here. Actions help you track the
						next steps from your strategic decisions.
					{/if}
				</p>
				{#if hasActiveFilters}
					<Button variant="secondary" size="md" onclick={clearFilters}>
						{#snippet children()}
							Clear Filters
						{/snippet}
					</Button>
				{:else}
					<a href="/meeting/new">
						<Button variant="brand" size="lg">
							{#snippet children()}
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M12 4v16m8-8H4"
									/>
								</svg>
								Start a Meeting
							{/snippet}
						</Button>
					</a>
				{/if}
			</div>
		{:else if viewMode === 'gantt'}
			<!-- Gantt View -->
			{#if ganttData}
				<GlobalGanttChart
					data={ganttData}
					onTaskClick={handleTaskClick}
					viewMode={ganttViewMode}
				/>
			{:else}
				<div class="flex items-center justify-center h-96 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
					<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600"></div>
				</div>
			{/if}
		{:else}
			<!-- Kanban Board with drag-and-drop -->
			<KanbanBoard
				tasks={allTasks}
				onStatusChange={handleKanbanStatusChange}
				onDelete={handleDelete}
				onTaskClick={handleTaskClick}
				loading={isKanbanLoading}
				showMeetingContext={true}
				columns={kanbanColumns}
			/>
		{/if}
	</div>
</div>

<!-- Click outside to close tag dropdown -->
{#if showTagDropdown}
	<button
		class="fixed inset-0 z-40"
		onclick={() => showTagDropdown = false}
		onkeydown={(e) => e.key === 'Escape' && (showTagDropdown = false)}
		aria-label="Close dropdown"
	></button>
{/if}
