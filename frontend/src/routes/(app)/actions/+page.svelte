<script lang="ts">
	/**
	 * Actions Page - Global Kanban board for all user actions
	 *
	 * Displays all actions from completed meetings in a Kanban view.
	 * Follows 2025 UX best practices:
	 * - F/Z-pattern layout with critical info at top
	 * - 5-second rule for finding key information
	 * - Color-coded status indicators
	 * - Click-through to meeting context
	 * - Filter by source meeting
	 */
	import { onMount } from 'svelte';
	import Header from '$lib/components/Header.svelte';
	import { apiClient } from '$lib/api/client';
	import type { AllActionsResponse, TaskWithSessionContext, SessionWithTasks } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';

	// Fetch all actions
	const actionsData = useDataFetch(() => apiClient.getAllActions());

	const data = $derived<AllActionsResponse | null>(actionsData.data);
	const isLoading = $derived(actionsData.isLoading);
	const error = $derived(actionsData.error);

	// Meeting filter state
	let selectedMeetingId = $state<string | null>(null);

	// Get unique meetings for filter dropdown
	const meetings = $derived<{ id: string; title: string; taskCount: number }[]>(
		data?.sessions
			? data.sessions.map((s) => ({
					id: s.session_id,
					title: s.problem_statement.length > 50
						? s.problem_statement.substring(0, 50) + '...'
						: s.problem_statement,
					taskCount: s.task_count
				}))
			: []
	);

	// Get all tasks flattened with session context (filtered by selected meeting)
	const allTasks = $derived.by<TaskWithSessionContext[]>(() => {
		if (!data?.sessions) return [];
		const tasks = data.sessions.flatMap((s) => s.tasks as TaskWithSessionContext[]);
		if (selectedMeetingId) {
			return tasks.filter((t) => t.session_id === selectedMeetingId);
		}
		return tasks;
	});

	// Filter tasks by status
	function getTasksByStatus(status: 'todo' | 'doing' | 'done') {
		return allTasks.filter((t) => t.status === status);
	}

	// Clear meeting filter
	function clearMeetingFilter() {
		selectedMeetingId = null;
	}

	// Status update handler
	let updatingTaskId = $state<string | null>(null);

	async function handleStatusChange(
		sessionId: string,
		taskId: string,
		newStatus: 'todo' | 'doing' | 'done'
	) {
		updatingTaskId = taskId;
		try {
			await apiClient.updateTaskStatus(sessionId, taskId, newStatus);
			// Refresh data
			await actionsData.fetch();
		} catch (err) {
			console.error('Failed to update task status:', err);
		} finally {
			updatingTaskId = null;
		}
	}

	const columns = [
		{ id: 'todo' as const, title: 'To Do', color: 'var(--color-neutral-500)' },
		{ id: 'doing' as const, title: 'In Progress', color: 'var(--color-warning-500)' },
		{ id: 'done' as const, title: 'Done', color: 'var(--color-success-500)' }
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

	onMount(() => {
		actionsData.fetch();
	});
</script>

<svelte:head>
	<title>Actions - Board of One</title>
</svelte:head>

<Header transparent={false} showCTA={true} />

<div
	class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800 pt-16"
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
				<a href="/dashboard">
					<Button variant="ghost" size="sm">
						{#snippet children()}
							<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M10 19l-7-7m0 0l7-7m-7 7h18"
								/>
							</svg>
							Dashboard
						{/snippet}
					</Button>
				</a>
			</div>

			<!-- Meeting Filter -->
			{#if data && !isLoading && meetings.length > 0}
				<div class="mb-4 flex flex-wrap items-center gap-3">
					<label for="meeting-filter" class="text-sm font-medium text-neutral-700 dark:text-neutral-300">
						Filter by meeting:
					</label>
					<div class="flex items-center gap-2">
						<select
							id="meeting-filter"
							bind:value={selectedMeetingId}
							class="px-3 py-2 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-lg text-sm text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 min-w-[200px] max-w-[400px]"
						>
							<option value={null}>All meetings ({data.total_tasks} actions)</option>
							{#each meetings as meeting (meeting.id)}
								<option value={meeting.id}>
									{meeting.title} ({meeting.taskCount} actions)
								</option>
							{/each}
						</select>
						{#if selectedMeetingId}
							<button
								onclick={clearMeetingFilter}
								class="p-2 text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
								title="Clear filter"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
								</svg>
							</button>
						{/if}
					</div>
					{#if selectedMeetingId}
						<span class="text-sm text-brand-600 dark:text-brand-400">
							Showing {allTasks.length} actions from selected meeting
						</span>
					{/if}
				</div>
			{/if}

			<!-- Quick Stats (filtered) -->
			{#if data && !isLoading}
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
							{getTasksByStatus('doing').length}
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
					<Button variant="danger" size="md" onclick={() => actionsData.fetch()}>
						{#snippet children()}
							Retry
						{/snippet}
					</Button>
				</div>
			</div>
		{:else if !data || data.total_tasks === 0}
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
				<h2 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-2">No actions yet</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-md mx-auto">
					Complete a meeting and extract action items to see them here. Actions help you track the
					next steps from your strategic decisions.
				</p>
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
			</div>
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
									{:else if column.id === 'doing'}
										No actions in progress
									{:else}
										No completed actions
									{/if}
								</div>
							{:else}
								{#each columnTasks as task (task.id + '-' + task.session_id)}
									{@const isUpdating = updatingTaskId === task.id}
									<a
										href="/actions/{task.session_id}/{task.id}"
										class="block bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg p-3 transition-all hover:shadow-md hover:border-brand-300 dark:hover:border-brand-600"
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
										<div class="flex gap-2 mt-2" onclick={(e) => e.preventDefault()}>
											{#if task.status === 'todo'}
												<button
													class="flex-1 text-xs px-2 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded transition-colors disabled:opacity-50"
													onclick={(e) => {
														e.preventDefault();
														e.stopPropagation();
														handleStatusChange(task.session_id, task.id, 'doing');
													}}
													disabled={isUpdating}
												>
													{isUpdating ? 'Starting...' : 'Start'}
												</button>
											{:else if task.status === 'doing'}
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
														handleStatusChange(task.session_id, task.id, 'doing');
													}}
													disabled={isUpdating}
												>
													{isUpdating ? 'Reopening...' : 'Reopen'}
												</button>
											{/if}
										</div>
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
