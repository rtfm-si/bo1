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
		description: string;
		category: string;
		priority: string;
		suggested_completion_date: string | null;
		dependencies: string[];
		source_section: string;
		confidence: number;
	}

	interface Props {
		sessionId: string;
	}

	let { sessionId }: Props = $props();

	// Use data fetch utility for tasks
	const tasksData = useDataFetch(() => apiClient.extractTasks(sessionId));

	// Derived state
	const tasks = $derived<Task[]>(tasksData.data?.tasks || []);
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

	// Generate mock success/kill criteria from task description and category
	function getSuccessCriteria(task: Task): string[] {
		// This would ideally come from the API, but for now we'll generate placeholder text
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

	function getKillCriteria(task: Task): string[] {
		// This would ideally come from the API
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

	// Get task name from ID for dependency display
	function getTaskName(taskId: string): string {
		const task = tasks.find(t => t.id === taskId);
		if (task) {
			// Return first 50 chars of description
			return task.description.substring(0, 50) + (task.description.length > 50 ? '...' : '');
		}
		return taskId;
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
		{#if tasks.length > 0 && !isLoading}
			<button
				onclick={exportTasks}
				disabled={isExporting}
				class="inline-flex items-center gap-2 px-4 py-2 bg-slate-600 hover:bg-slate-700 disabled:bg-slate-400 text-white text-sm font-medium rounded-lg transition-colors"
			>
				<Download class="w-4 h-4" />
				{isExporting ? 'Exporting...' : 'Export'}
			</button>
		{/if}
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
					<!-- Task Header -->
					<div class="flex items-start justify-between gap-4 mb-3">
						<div class="flex-1">
							<div class="flex items-center gap-2 mb-2">
								<span class="flex-shrink-0 w-6 h-6 bg-slate-600 text-white rounded-full flex items-center justify-center text-xs font-semibold">
									{index + 1}
								</span>
								<h4 class="text-base font-semibold text-slate-900 dark:text-white">
									{task.description}
								</h4>
							</div>

							<!-- Success & Kill Criteria (Brief) -->
							<div class="ml-8 space-y-2 text-sm text-slate-600 dark:text-slate-400">
								<div>
									<span class="font-medium text-slate-700 dark:text-slate-300">Success:</span>
									{getSuccessCriteria(task)[0]}
								</div>
								<div>
									<span class="font-medium text-slate-700 dark:text-slate-300">Kill if:</span>
									{getKillCriteria(task)[0]}
								</div>
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
						<div class="ml-8 mt-3 pt-3 border-t border-slate-300 dark:border-slate-600 space-y-3 text-sm">
							<!-- All Success Criteria -->
							<div>
								<p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Success Criteria:</p>
								<ul class="list-disc list-inside text-slate-600 dark:text-slate-400 space-y-1">
									{#each getSuccessCriteria(task) as criterion}
										<li>{criterion}</li>
									{/each}
								</ul>
							</div>

							<!-- All Kill Criteria -->
							<div>
								<p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Kill Criteria:</p>
								<ul class="list-disc list-inside text-slate-600 dark:text-slate-400 space-y-1">
									{#each getKillCriteria(task) as criterion}
										<li>{criterion}</li>
									{/each}
								</ul>
							</div>

							<!-- Dependencies -->
							{#if task.dependencies && task.dependencies.length > 0}
								<div>
									<p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Dependencies:</p>
									<ul class="list-disc list-inside text-slate-600 dark:text-slate-400 space-y-1">
										{#each task.dependencies as dep}
											<li>{getTaskName(dep)}</li>
										{/each}
									</ul>
								</div>
							{/if}

							<!-- Metadata -->
							<div class="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
								<span>Category: {task.category}</span>
								<span>Priority: {task.priority}</span>
								<span>Confidence: {(task.confidence * 100).toFixed(0)}%</span>
								{#if task.suggested_completion_date}
									<span>Suggested: {task.suggested_completion_date}</span>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
