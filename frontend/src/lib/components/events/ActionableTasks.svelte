<script lang="ts">
	/**
	 * ActionableTasks Component (Refactored)
	 *
	 * Cleaner, more executive design with:
	 * - Status dropdown extracted to TaskStatusSelect
	 * - Detailed description with success/kill criteria extracted to TaskDetails
	 * - Dependencies in TaskDetails component
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import { slide } from 'svelte/transition';
	import { ChevronDown, ChevronUp } from 'lucide-svelte';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { TaskStatusSelect, TaskDetails } from '$lib/components/tasks';

	interface Task {
		id: string;
		title?: string;
		description: string;
		what_and_how?: string[];
		success_criteria?: string[];
		kill_criteria?: string[];
		dependencies: string[];
		timeline?: string;
		category: string;
		priority: string;
		suggested_completion_date?: string | null;
		source_section: string | null;
		confidence: number;
		sub_problem_index?: number | null;
	}

	interface Props {
		sessionId: string;
		subProblemIndex?: number; // undefined = show all (Summary tab)
	}

	let { sessionId, subProblemIndex }: Props = $props();

	// Use data fetch utility for tasks
	const tasksData = useDataFetch(() => apiClient.extractTasks(sessionId));

	// Derived state - filter tasks based on sub-problem
	const allTasks = $derived<Task[]>(tasksData.data?.tasks || []);
	const tasks = $derived.by(() => {
		if (subProblemIndex === undefined) {
			return allTasks;
		}
		return allTasks.filter(
			(task) => task.sub_problem_index === subProblemIndex || task.sub_problem_index === null
		);
	});
	const isLoading = $derived(tasksData.isLoading);
	const error = $derived(tasksData.error);

	let taskStatuses = $state<Map<string, string>>(new Map());
	let expandedTasks = $state<Set<string>>(new Set());

	onMount(() => {
		loadTasks();
	});

	async function loadTasks() {
		await tasksData.fetch();
		if (tasksData.data?.tasks) {
			taskStatuses = new Map(tasksData.data.tasks.map((t) => [t.id, 'pending']));
		}
	}

	function updateStatus(taskId: string, status: string) {
		taskStatuses.set(taskId, status);
		taskStatuses = new Map(taskStatuses);
	}

	function toggleDetails(taskId: string) {
		if (expandedTasks.has(taskId)) {
			expandedTasks.delete(taskId);
		} else {
			expandedTasks.add(taskId);
		}
		expandedTasks = new Set(expandedTasks);
	}

	// Get task title from title field or extract from description
	function getTaskTitle(task: Task): string {
		if (task.title && task.title.trim()) {
			return task.title;
		}
		const description = task.description;
		if (typeof description !== 'string') return `Task ${task.id}`;
		const firstSentence = description.split(/[:.]\s/)[0];
		if (firstSentence.length > 100) {
			return firstSentence.substring(0, 100) + '...';
		}
		if (description.length > firstSentence.length + 2) {
			return firstSentence + '...';
		}
		return firstSentence;
	}

	const acceptedCount = $derived(
		Array.from(taskStatuses.values()).filter((s) => s === 'accepted').length
	);
	const rejectedCount = $derived(
		Array.from(taskStatuses.values()).filter((s) => s === 'rejected').length
	);
	const inProgressCount = $derived(
		Array.from(taskStatuses.values()).filter((s) => s === 'in_progress').length
	);
</script>

<div
	class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6 mt-6"
>
	<div class="flex items-center justify-between mb-4">
		<div>
			<h3 class="text-lg font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
					/>
				</svg>
				Recommended Actions
			</h3>
			{#if !isLoading && !error}
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
					{acceptedCount} accepted • {inProgressCount} in progress • {rejectedCount} rejected
				</p>
			{/if}
		</div>
	</div>

	{#if isLoading}
		<div class="flex items-center justify-center py-12">
			<svg class="animate-spin h-8 w-8 text-info-600" fill="none" viewBox="0 0 24 24">
				<circle
					class="opacity-25"
					cx="12"
					cy="12"
					r="10"
					stroke="currentColor"
					stroke-width="4"
				></circle>
				<path
					class="opacity-75"
					fill="currentColor"
					d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
				></path>
			</svg>
		</div>
	{:else if error}
		<div
			class="bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg p-4 text-center"
		>
			<p class="text-sm text-warning-800 dark:text-warning-200 mb-2">{error}</p>
			<p class="text-xs text-warning-700 dark:text-warning-300">
				Action extraction requires a completed synthesis.
			</p>
		</div>
	{:else if tasks.length === 0}
		<div class="bg-neutral-50 dark:bg-neutral-900/50 rounded-lg p-8 text-center">
			<svg
				class="w-12 h-12 text-neutral-400 mx-auto mb-3"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
				/>
			</svg>
			<p class="text-sm text-neutral-600 dark:text-neutral-400">
				No actions extracted from this decision.
			</p>
		</div>
	{:else}
		<div class="space-y-4">
			{#each tasks as task, index (task.id)}
				{@const status = taskStatuses.get(task.id) || 'pending'}
				{@const isExpanded = expandedTasks.has(task.id)}
				<div
					class="bg-neutral-50 dark:bg-neutral-900/50 rounded-xl border border-neutral-200 dark:border-neutral-700 overflow-hidden"
					transition:slide={{ duration: 200 }}
				>
					<!-- Task Header -->
					<div class="p-5 sm:p-6">
						<!-- Top row: Number + Title + Status -->
						<div class="flex flex-col sm:flex-row sm:items-start gap-4 mb-4">
							<div class="flex items-start gap-3 flex-1 min-w-0">
								<span
									class="flex-shrink-0 w-8 h-8 bg-neutral-700 dark:bg-neutral-600 text-white rounded-full flex items-center justify-center text-sm font-bold shadow-sm"
								>
									{index + 1}
								</span>
								<h4
									class="text-base sm:text-lg font-semibold text-neutral-900 dark:text-white leading-snug pt-0.5"
								>
									{getTaskTitle(task)}
								</h4>
							</div>

							<TaskStatusSelect {status} onStatusChange={(s) => updateStatus(task.id, s)} />
						</div>

						<!-- Metadata pills -->
						<div class="flex flex-wrap gap-2 mb-4">
							<span
								class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-neutral-200 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300"
							>
								<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
									/>
								</svg>
								{task.timeline || task.suggested_completion_date || 'Timeline TBD'}
							</span>
							<span
								class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium capitalize
								{task.priority === 'high'
									? 'bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-300'
									: task.priority === 'medium'
										? 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300'
										: 'bg-neutral-200 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300'}"
							>
								<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"
									/>
								</svg>
								{task.priority} priority
							</span>
						</div>

						<!-- Expand/Collapse Details -->
						<button
							onclick={() => toggleDetails(task.id)}
							class="inline-flex items-center gap-1.5 text-sm text-info-600 dark:text-info-400 hover:text-info-700 dark:hover:text-info-300 font-medium transition-colors"
						>
							{isExpanded ? 'Hide details' : 'Show details'}
							{#if isExpanded}
								<ChevronUp class="w-4 h-4" />
							{:else}
								<ChevronDown class="w-4 h-4" />
							{/if}
						</button>
					</div>

					<!-- Expanded Details -->
					{#if isExpanded}
						<TaskDetails {task} />
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
