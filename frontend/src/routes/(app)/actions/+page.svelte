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
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import type {
		AllActionsResponse,
		TaskWithSessionContext,
		ActionStatus,
		TagResponse,
		ProjectDetailResponse,
		GlobalGanttResponse
	} from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import Badge from '$lib/components/ui/Badge.svelte';
	import GlobalGanttChart from '$lib/components/actions/GlobalGanttChart.svelte';

	// Filter state
	let selectedMeetingId = $state<string | null>(null);
	let selectedProjectId = $state<string | null>(null);
	let selectedTagIds = $state<string[]>([]);

	// View mode state (kanban or gantt)
	let viewMode = $state<'kanban' | 'gantt'>('kanban');
	let ganttViewMode = $state<'Day' | 'Week' | 'Month'>('Week');

	// Loading states
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	// Data
	let actionsData = $state<AllActionsResponse | null>(null);
	let ganttData = $state<GlobalGanttResponse | null>(null);
	let projects = $state<ProjectDetailResponse[]>([]);
	let tags = $state<TagResponse[]>([]);
	let showTagDropdown = $state(false);

	// Fetch all data
	async function fetchData() {
		isLoading = true;
		error = null;
		try {
			// Build filter params
			const params: Record<string, string | undefined> = {};
			if (selectedProjectId) params.project_id = selectedProjectId;
			if (selectedMeetingId) params.session_id = selectedMeetingId;
			if (selectedTagIds.length > 0) params.tag_ids = selectedTagIds.join(',');

			// Fetch actions, projects, tags in parallel
			const [actionsRes, projectsRes, tagsRes] = await Promise.all([
				apiClient.getAllActions(params),
				apiClient.listProjects({ status: 'active' }),
				apiClient.getTags()
			]);

			actionsData = actionsRes;
			projects = projectsRes.projects;
			tags = tagsRes.tags;

			// If gantt view is active, fetch gantt data too
			if (viewMode === 'gantt') {
				ganttData = await apiClient.getGlobalGantt(params);
			}
		} catch (err) {
			console.error('Failed to fetch actions:', err);
			error = err instanceof Error ? err.message : 'Failed to load actions';
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
			? actionsData.sessions.map((s) => ({
					id: s.session_id,
					title: s.problem_statement.length > 50
						? s.problem_statement.substring(0, 50) + '...'
						: s.problem_statement,
					taskCount: s.task_count
				}))
			: []
	);

	// Get all tasks flattened with session context (filtered by selected meeting - client-side filter for meeting)
	const allTasks = $derived.by<TaskWithSessionContext[]>(() => {
		if (!actionsData?.sessions) return [];
		const tasks = actionsData.sessions.flatMap((s) => s.tasks as TaskWithSessionContext[]);
		// Meeting filter is applied server-side via session_id, but also filter client-side for UI responsiveness
		if (selectedMeetingId) {
			return tasks.filter((t) => t.session_id === selectedMeetingId);
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

	// Status update handler
	let updatingTaskId = $state<string | null>(null);
	let deletingTaskId = $state<string | null>(null);
	let confirmDeleteTaskId = $state<string | null>(null);

	async function handleStatusChange(
		sessionId: string,
		taskId: string,
		newStatus: ActionStatus
	) {
		updatingTaskId = taskId;
		try {
			await apiClient.updateTaskStatus(sessionId, taskId, newStatus);
			await fetchData();
		} catch (err) {
			console.error('Failed to update task status:', err);
		} finally {
			updatingTaskId = null;
		}
	}

	async function handleDelete(taskId: string) {
		deletingTaskId = taskId;
		confirmDeleteTaskId = null;
		try {
			await apiClient.deleteAction(taskId);
			await fetchData();
		} catch (err) {
			console.error('Failed to delete action:', err);
		} finally {
			deletingTaskId = null;
		}
	}

	// Navigate to action detail
	function handleTaskClick(actionId: string) {
		goto(`/actions/${actionId}`);
	}

	const columns: { id: ActionStatus; title: string; color: string }[] = [
		{ id: 'todo', title: 'To Do', color: 'var(--color-neutral-500)' },
		{ id: 'in_progress', title: 'In Progress', color: 'var(--color-warning-500)' },
		{ id: 'done', title: 'Done', color: 'var(--color-success-500)' }
	];

	const priorityColors: Record<string, string> = {
		high: 'error',
		medium: 'warning',
		low: 'success'
	};

	function truncate(text: string, maxLen: number = 60): string {
		if (text.length <= maxLen) return text;
		return text.substring(0, maxLen) + '...';
	}

	// Check if any filters are active
	const hasActiveFilters = $derived(
		selectedMeetingId !== null || selectedProjectId !== null || selectedTagIds.length > 0
	);

	onMount(() => {
		fetchData();
	});
</script>

<svelte:head>
	<title>Actions - Board of One</title>
</svelte:head>

<div
	class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800"
>
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
				<div class="flex items-center gap-4">
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

			<!-- Filters Row -->
			{#if actionsData && !isLoading}
				<div class="mb-4 flex flex-wrap items-center gap-3 p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
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

					<!-- Active filter count -->
					<span class="ml-auto text-sm text-neutral-500 dark:text-neutral-400">
						{actionsData.total_tasks} actions
					</span>
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
			<!-- Loading State -->
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				{#each Array(3) as _}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4"
					>
						<ShimmerSkeleton type="text" />
						<div class="mt-4 space-y-3">
							{#each Array(3) as _}
								<ShimmerSkeleton type="card" />
							{/each}
						</div>
					</div>
				{/each}
			</div>
		{:else if error}
			<!-- Error State -->
			<div
				class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-6"
			>
				<div class="flex items-center gap-3">
					<svg
						class="w-6 h-6 text-error-600 dark:text-error-400"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					<div>
						<h3 class="text-lg font-semibold text-error-900 dark:text-error-200">
							Error Loading Actions
						</h3>
						<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
					</div>
				</div>
				<div class="mt-4">
					<Button variant="danger" size="md" onclick={() => fetchData()}>
						{#snippet children()}
							Retry
						{/snippet}
					</Button>
				</div>
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
			<!-- Kanban Board -->
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				{#each columns as column (column.id)}
					{@const columnTasks = getTasksByStatus(column.id)}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 flex flex-col"
					>
						<!-- Column Header -->
						<div
							class="px-4 py-3 border-b-2 flex items-center justify-between"
							style="border-color: {column.color}"
						>
							<span class="font-semibold text-neutral-900 dark:text-white">{column.title}</span>
							<span
								class="text-xs font-medium px-2 py-1 rounded-full text-white"
								style="background: {column.color}"
							>
								{columnTasks.length}
							</span>
						</div>

						<!-- Column Content -->
						<div class="p-3 flex-1 overflow-y-auto max-h-[600px] space-y-3">
							{#if columnTasks.length === 0}
								<div class="text-center py-8 text-neutral-400 dark:text-neutral-500 text-sm">
									{#if column.id === 'todo'}
										No pending actions
									{:else if column.id === 'in_progress'}
										No actions in progress
									{:else}
										No completed actions
									{/if}
								</div>
							{:else}
								{#each columnTasks as task (task.id + '-' + task.session_id)}
									{@const isUpdating = updatingTaskId === task.id}
									<a
										href="/actions/{task.id}"
										class="relative block bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg p-3 transition-all hover:shadow-md hover:border-brand-300 dark:hover:border-brand-600"
										class:opacity-50={isUpdating}
										style="border-left: 3px solid {task.priority === 'high'
											? 'var(--color-error-500)'
											: task.priority === 'medium'
												? 'var(--color-warning-500)'
												: 'var(--color-success-500)'}"
									>
										<!-- Task Title -->
										<h4 class="font-medium text-neutral-900 dark:text-white text-sm mb-1">
											{task.title}
										</h4>

										<!-- Task Description -->
										<p class="text-xs text-neutral-600 dark:text-neutral-400 mb-2">
											{truncate(task.description)}
										</p>

										<!-- Meeting Context -->
										<div class="text-xs text-brand-600 dark:text-brand-400 mb-2">
											From: {truncate(task.problem_statement, 40)}
										</div>

										<!-- Badges -->
										<div class="flex flex-wrap gap-1 mb-2">
											<Badge
												variant={priorityColors[task.priority] as
													| 'error'
													| 'warning'
													| 'success'}
											>
												{task.priority}
											</Badge>
											<Badge variant="info">{task.category}</Badge>
											{#if task.timeline}
												<span
													class="text-xs px-2 py-0.5 bg-neutral-200 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 rounded"
												>
													{task.timeline}
												</span>
											{/if}
										</div>

										<!-- Action Buttons -->
										<div class="flex gap-2 mt-2" role="group" aria-label="Task actions" onkeydown={(e) => e.key === 'Enter' && e.preventDefault()} onclick={(e) => e.preventDefault()}>
											{#if task.status === 'todo'}
												<button
													class="flex-1 text-xs px-2 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded transition-colors disabled:opacity-50"
													onclick={(e) => {
														e.preventDefault();
														e.stopPropagation();
														handleStatusChange(task.session_id, task.id, 'in_progress');
													}}
													disabled={isUpdating}
												>
													{isUpdating ? 'Starting...' : 'Start'}
												</button>
											{:else if task.status === 'in_progress'}
												<button
													class="flex-1 text-xs px-2 py-1.5 bg-success-600 hover:bg-success-700 text-white rounded transition-colors disabled:opacity-50"
													onclick={(e) => {
														e.preventDefault();
														e.stopPropagation();
														handleStatusChange(task.session_id, task.id, 'done');
													}}
													disabled={isUpdating}
												>
													{isUpdating ? 'Completing...' : 'Complete'}
												</button>
												<button
													class="text-xs px-2 py-1.5 bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 rounded transition-colors disabled:opacity-50"
													onclick={(e) => {
														e.preventDefault();
														e.stopPropagation();
														handleStatusChange(task.session_id, task.id, 'todo');
													}}
													disabled={isUpdating}
												>
													Back
												</button>
											{:else}
												<button
													class="flex-1 text-xs px-2 py-1.5 bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 rounded transition-colors disabled:opacity-50"
													onclick={(e) => {
														e.preventDefault();
														e.stopPropagation();
														handleStatusChange(task.session_id, task.id, 'in_progress');
													}}
													disabled={isUpdating}
												>
													{isUpdating ? 'Reopening...' : 'Reopen'}
												</button>
											{/if}
											<!-- Delete Button -->
											<button
												class="text-xs px-2 py-1.5 text-neutral-400 hover:text-error-600 hover:bg-error-50 dark:hover:bg-error-900/20 rounded transition-colors disabled:opacity-50"
												onclick={(e) => {
													e.preventDefault();
													e.stopPropagation();
													confirmDeleteTaskId = task.id;
												}}
												disabled={deletingTaskId === task.id}
												title="Delete action"
											>
												<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
												</svg>
											</button>
										</div>

										<!-- Delete Confirmation Overlay -->
										{#if confirmDeleteTaskId === task.id}
											<div class="absolute inset-0 bg-white/95 dark:bg-neutral-900/95 rounded-lg flex flex-col items-center justify-center gap-3 z-10">
												<p class="text-sm font-medium text-neutral-900 dark:text-white">Delete this action?</p>
												<div class="flex gap-2">
													<button
														class="px-3 py-1.5 text-xs bg-error-600 hover:bg-error-700 text-white rounded transition-colors"
														onclick={(e) => {
															e.preventDefault();
															e.stopPropagation();
															handleDelete(task.id);
														}}
													>
														Delete
													</button>
													<button
														class="px-3 py-1.5 text-xs bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 rounded transition-colors"
														onclick={(e) => {
															e.preventDefault();
															e.stopPropagation();
															confirmDeleteTaskId = null;
														}}
													>
														Cancel
													</button>
												</div>
											</div>
										{/if}
									</a>
								{/each}
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</main>
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
