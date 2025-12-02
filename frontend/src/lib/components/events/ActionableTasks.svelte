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
	import { getTaskStatusColor } from '$lib/utils/color-helpers';

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
		<div class="space-y-4">
			{#each tasks as task, index (task.id)}
				{@const status = taskStatuses.get(task.id) || 'pending'}
				{@const isExpanded = expandedTasks.has(task.id)}
				<div
					class="bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden"
					transition:slide={{ duration: 200 }}
				>
					<!-- Task Header -->
					<div class="p-5 sm:p-6">
						<!-- Top row: Number + Title + Status -->
						<div class="flex flex-col sm:flex-row sm:items-start gap-4 mb-4">
							<div class="flex items-start gap-3 flex-1 min-w-0">
								<span class="flex-shrink-0 w-8 h-8 bg-slate-700 dark:bg-slate-600 text-white rounded-full flex items-center justify-center text-sm font-bold shadow-sm">
									{index + 1}
								</span>
								<h4 class="text-base sm:text-lg font-semibold text-slate-900 dark:text-white leading-snug pt-0.5">
									{getTaskTitle(task)}
								</h4>
							</div>

							<!-- Status Dropdown - Full width on mobile, auto on desktop -->
							<div class="flex-shrink-0 w-full sm:w-auto">
								<select
									value={status}
									onchange={(e) => updateStatus(task.id, e.currentTarget.value)}
									class="w-full sm:w-auto px-4 py-2.5 text-sm font-medium rounded-lg border-0 {getTaskStatusColor(status)} cursor-pointer focus:ring-2 focus:ring-blue-500 shadow-sm"
								>
									{#each statusOptions as option}
										<option value={option.value}>{option.label}</option>
									{/each}
								</select>
							</div>
						</div>

						<!-- Metadata pills -->
						<div class="flex flex-wrap gap-2 mb-4">
							<span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
								<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
								</svg>
								{task.timeline || task.suggested_completion_date || 'Timeline TBD'}
							</span>
							<span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium capitalize
								{task.priority === 'high' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300' :
								 task.priority === 'medium' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300' :
								 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'}">
								<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
								</svg>
								{task.priority} priority
							</span>
						</div>

						<!-- Expand/Collapse Details -->
						<button
							onclick={() => toggleDetails(task.id)}
							class="inline-flex items-center gap-1.5 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium transition-colors"
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
						<div class="px-5 sm:px-6 pb-5 sm:pb-6 pt-0 border-t border-slate-200 dark:border-slate-700">
							<div class="pt-5 space-y-5">
								<!-- What & How -->
								<div>
									<h5 class="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2.5">What & How</h5>
									<ul class="space-y-2">
										{#each getWhatAndHow(task) as item}
											<li class="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
												<span class="text-slate-400 dark:text-slate-500 mt-1.5">•</span>
												<span>{item}</span>
											</li>
										{/each}
									</ul>
								</div>

								<!-- Success & Kill Criteria - Side by side on larger screens -->
								<div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
									<!-- Success Criteria -->
									<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
										<h5 class="text-sm font-semibold text-green-800 dark:text-green-200 mb-2.5 flex items-center gap-2">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
											Success Criteria
										</h5>
										<ul class="space-y-2">
											{#each getSuccessCriteria(task) as criterion}
												<li class="flex items-start gap-2 text-sm text-green-700 dark:text-green-300 leading-relaxed">
													<span class="text-green-500 dark:text-green-400 mt-1">✓</span>
													<span>{criterion}</span>
												</li>
											{/each}
										</ul>
									</div>

									<!-- Kill Criteria -->
									<div class="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
										<h5 class="text-sm font-semibold text-red-800 dark:text-red-200 mb-2.5 flex items-center gap-2">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
											</svg>
											Kill Criteria
										</h5>
										<ul class="space-y-2">
											{#each getKillCriteria(task) as criterion}
												<li class="flex items-start gap-2 text-sm text-red-700 dark:text-red-300 leading-relaxed">
													<span class="text-red-500 dark:text-red-400 mt-1">✗</span>
													<span>{criterion}</span>
												</li>
											{/each}
										</ul>
									</div>
								</div>

								<!-- Dependencies -->
								{#if task.dependencies && task.dependencies.length > 0}
									<div class="bg-slate-100 dark:bg-slate-800 rounded-lg p-4">
										<h5 class="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2.5 flex items-center gap-2">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
											</svg>
											Dependencies
										</h5>
										<ul class="space-y-2">
											{#each task.dependencies as dep}
												<li class="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
													<span class="text-slate-400 dark:text-slate-500 mt-1">→</span>
													<span>{dep}</span>
												</li>
											{/each}
										</ul>
									</div>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
