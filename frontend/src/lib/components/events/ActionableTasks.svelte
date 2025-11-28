<script lang="ts">
	/**
	 * ActionableTasks Component (Redesigned)
	 *
	 * Cleaner, more executive design with:
	 * - Status dropdown instead of accept/reject buttons
	 * - Removed color pills (category, priority badges)
	 * - Detailed description with success criteria and kill criteria
	 * - Dependencies moved to expandable details section
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import { fade, slide } from 'svelte/transition';
	import { ChevronDown, ChevronUp, Download } from 'lucide-svelte';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';

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
		source_section: string;
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
			// Summary view - show ALL tasks
			return allTasks;
		}
		// Sub-problem view - show only this sub-problem's tasks + global tasks (sub_problem_index = null)
		return allTasks.filter(
			(task) => task.sub_problem_index === subProblemIndex || task.sub_problem_index === null
		);
	});
	const isLoading = $derived(tasksData.isLoading);
	const error = $derived(tasksData.error);

	let taskStatuses = $state<Map<string, string>>(new Map());
	let expandedTasks = $state<Set<string>>(new Set());
	let isExporting = $state(false);

	const statusOptions = [
		{ value: 'pending', label: 'Pending', color: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300' },
		{ value: 'accepted', label: 'Accepted', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' },
		{ value: 'in_progress', label: 'In Progress', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
		{ value: 'delayed', label: 'Delayed', color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' },
		{ value: 'rejected', label: 'Rejected', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' },
		{ value: 'complete', label: 'Complete', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' },
		{ value: 'failed', label: 'Failed', color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' }
	];

	onMount(() => {
		loadTasks();
	});

	async function loadTasks() {
		await tasksData.fetch();

		// Initialize all tasks as pending
		if (tasksData.data?.tasks) {
			taskStatuses = new Map(tasksData.data.tasks.map(t => [t.id, 'pending']));
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

	async function exportTasks() {
		isExporting = true;

		const exportData = tasks.map(t => ({
			description: t.description,
			status: taskStatuses.get(t.id) || 'pending',
			priority: t.priority,
			category: t.category,
			suggested_date: t.suggested_completion_date || 'TBD',
			dependencies: t.dependencies,
			confidence: (t.confidence * 100).toFixed(0) + '%'
		}));

		const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `actions_${sessionId}.json`;
		a.click();
		URL.revokeObjectURL(url);

		isExporting = false;
	}

	function getStatusColor(status: string): string {
		const option = statusOptions.find(s => s.value === status);
		return option?.color || statusOptions[0].color;
	}

	function getStatusLabel(status: string): string {
		const option = statusOptions.find(s => s.value === status);
		return option?.label || 'Pending';
	}

	// Get success criteria from task or generate fallback
	function getSuccessCriteria(task: Task): string[] {
		// Use API response if available
		if (task.success_criteria && task.success_criteria.length > 0) {
			return task.success_criteria;
		}

		// Fallback for backwards compatibility
		const criteria: string[] = [];
		if (task.category === 'implementation') {
			criteria.push('Feature deployed to production without errors');
			criteria.push('User acceptance testing completed');
		} else if (task.category === 'research') {
			criteria.push('Report delivered with actionable insights');
			criteria.push('Stakeholder review completed');
		} else if (task.category === 'decision') {
			criteria.push('Decision documented and communicated');
			criteria.push('Implementation plan approved');
		} else {
			criteria.push('Task deliverables completed and reviewed');
		}
		return criteria;
	}

	// Get kill criteria from task or generate fallback
	function getKillCriteria(task: Task): string[] {
		// Use API response if available
		if (task.kill_criteria && task.kill_criteria.length > 0) {
			return task.kill_criteria;
		}

		// Fallback for backwards compatibility
		const criteria: string[] = [];
		if (task.priority === 'high') {
			criteria.push('Blocked by missing dependencies for >2 weeks');
			criteria.push('Cost exceeds budget by >50%');
		} else if (task.priority === 'medium') {
			criteria.push('Lower priority work takes precedence');
			criteria.push('Resources unavailable for >1 month');
		} else {
			criteria.push('No longer aligned with strategic goals');
			criteria.push('Opportunity cost too high');
		}
		return criteria;
	}

	// Get what and how from task or use description as fallback
	function getWhatAndHow(task: Task): string[] {
		if (task.what_and_how && task.what_and_how.length > 0) {
			return task.what_and_how;
		}
		// Fallback: use description as single bullet
		return [task.description];
	}

	// Get task name from ID for dependency display
	function getTaskName(taskId: string): string {
		const task = tasks.find(t => t.id === taskId);
		if (task) {
			// Return first 50 chars of description
			return task.description.substring(0, 50) + (task.description.length > 50 ? '...' : '');
		}
		return taskId;
	}

	// Get task title from title field or extract from description
	function getTaskTitle(task: Task): string {
		// Use title field if available
		if (task.title && task.title.trim()) {
			return task.title;
		}

		// Fallback: extract from description (first sentence or first 100 chars)
		const description = task.description;
		const firstSentence = description.split(/[:.]\s/)[0];

		// If first sentence is too long, truncate at 100 chars
		if (firstSentence.length > 100) {
			return firstSentence.substring(0, 100) + '...';
		}

		// If the description is longer than the first sentence, add ellipsis
		if (description.length > firstSentence.length + 2) {
			return firstSentence + '...';
		}

		return firstSentence;
	}

	const acceptedCount = $derived(Array.from(taskStatuses.values()).filter(s => s === 'accepted').length);
	const rejectedCount = $derived(Array.from(taskStatuses.values()).filter(s => s === 'rejected').length);
	const inProgressCount = $derived(Array.from(taskStatuses.values()).filter(s => s === 'in_progress').length);
</script>

<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-6 mt-6">
	<div class="flex items-center justify-between mb-4">
		<div>
			<h3 class="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
				</svg>
				Recommended Actions
			</h3>
			{#if !isLoading && !error}
				<p class="text-sm text-slate-600 dark:text-slate-400 mt-1">
					{acceptedCount} accepted • {inProgressCount} in progress • {rejectedCount} rejected
				</p>
			{/if}
		</div>
	</div>

	{#if isLoading}
		<div class="flex items-center justify-center py-12">
			<svg class="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
			</svg>
		</div>
	{:else if error}
		<div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-center">
			<p class="text-sm text-yellow-800 dark:text-yellow-200 mb-2">{error}</p>
			<p class="text-xs text-yellow-700 dark:text-yellow-300">
				Action extraction requires a completed synthesis.
			</p>
		</div>
	{:else if tasks.length === 0}
		<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-8 text-center">
			<svg class="w-12 h-12 text-slate-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
			</svg>
			<p class="text-sm text-slate-600 dark:text-slate-400">
				No actions extracted from this decision.
			</p>
		</div>
	{:else}
		<div class="space-y-3">
			{#each tasks as task, index (task.id)}
				{@const status = taskStatuses.get(task.id) || 'pending'}
				{@const isExpanded = expandedTasks.has(task.id)}
				<div
					class="bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700 p-4"
					transition:slide={{ duration: 200 }}
				>
					<!-- Task Header (Always Visible) -->
					<div class="flex items-start justify-between gap-4 mb-3">
						<div class="flex-1">
							<!-- Title -->
							<div class="flex items-center gap-2 mb-3">
								<span class="flex-shrink-0 w-6 h-6 bg-slate-600 text-white rounded-full flex items-center justify-center text-xs font-semibold">
									{index + 1}
								</span>
								<h4 class="text-base font-semibold text-slate-900 dark:text-white">
									{getTaskTitle(task)}
								</h4>
							</div>

							<!-- Metadata: Timeline, Priority, Status (Always Visible) -->
							<div class="ml-8 grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
								<div>
									<span class="font-medium text-slate-700 dark:text-slate-300">Timeline:</span>
									<span class="text-slate-600 dark:text-slate-400"> {task.timeline || task.suggested_completion_date || 'TBD'}</span>
								</div>
								<div>
									<span class="font-medium text-slate-700 dark:text-slate-300">Priority:</span>
									<span class="text-slate-600 dark:text-slate-400 capitalize"> {task.priority}</span>
								</div>
								<!-- Status is shown via dropdown, no need for duplicate label -->
							</div>
						</div>

						<!-- Status Dropdown -->
						<div class="flex-shrink-0">
							<select
								value={status}
								onchange={(e) => updateStatus(task.id, e.currentTarget.value)}
								class="px-3 py-2 text-sm font-medium rounded-lg border-0 {getStatusColor(status)} cursor-pointer focus:ring-2 focus:ring-blue-500"
							>
								{#each statusOptions as option}
									<option value={option.value}>{option.label}</option>
								{/each}
							</select>
						</div>
					</div>

					<!-- Expand/Collapse Details -->
					<button
						onclick={() => toggleDetails(task.id)}
						class="ml-8 text-sm text-blue-600 dark:text-blue-400 hover:underline font-medium flex items-center gap-1"
					>
						{isExpanded ? 'Hide' : 'Show'} details
						{#if isExpanded}
							<ChevronUp class="w-4 h-4" />
						{:else}
							<ChevronDown class="w-4 h-4" />
						{/if}
					</button>

					<!-- Expanded Details -->
					{#if isExpanded}
						<div class="ml-8 mt-3 pt-3 border-t border-slate-300 dark:border-slate-600 space-y-4 text-sm">
							<!-- What & How -->
							<div>
								<p class="font-semibold text-slate-700 dark:text-slate-300 mb-2">What & How</p>
								<ul class="list-disc list-inside text-slate-600 dark:text-slate-400 space-y-1">
									{#each getWhatAndHow(task) as item}
										<li>{item}</li>
									{/each}
								</ul>
							</div>

							<!-- Success Criteria -->
							<div>
								<p class="font-semibold text-slate-700 dark:text-slate-300 mb-2">Success Criteria</p>
								<ul class="list-disc list-inside text-slate-600 dark:text-slate-400 space-y-1">
									{#each getSuccessCriteria(task) as criterion}
										<li>{criterion}</li>
									{/each}
								</ul>
							</div>

							<!-- Kill Criteria -->
							<div>
								<p class="font-semibold text-slate-700 dark:text-slate-300 mb-2">Kill Criteria</p>
								<ul class="list-disc list-inside text-slate-600 dark:text-slate-400 space-y-1">
									{#each getKillCriteria(task) as criterion}
										<li>{criterion}</li>
									{/each}
								</ul>
							</div>

							<!-- Dependencies -->
							{#if task.dependencies && task.dependencies.length > 0}
								<div>
									<p class="font-semibold text-slate-700 dark:text-slate-300 mb-2">Dependencies</p>
									<ul class="list-disc list-inside text-slate-600 dark:text-slate-400 space-y-1">
										{#each task.dependencies as dep}
											<li>{dep}</li>
										{/each}
									</ul>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
