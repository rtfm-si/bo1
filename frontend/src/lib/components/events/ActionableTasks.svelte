<script lang="ts">
	/**
	 * ActionableTasks Component
	 * Displays extracted tasks from synthesis with accept/reject functionality
	 */
	import { apiClient } from '$lib/api/client';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { fade, slide } from 'svelte/transition';

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

	let tasks = $state<Task[]>([]);
	let acceptedTasks = $state<Set<string>>(new Set());
	let rejectedTasks = $state<Set<string>>(new Set());
	let customDates = $state<Map<string, string>>(new Map());
	let isLoading = $state(true);
	let isExporting = $state(false);
	let error = $state<string | null>(null);

	$effect(() => {
		loadTasks();
	});

	async function loadTasks() {
		try {
			isLoading = true;
			error = null;
			const response = await apiClient.extractTasks(sessionId);
			tasks = response.tasks;
			isLoading = false;
		} catch (err) {
			console.error('Failed to extract tasks:', err);
			error = err instanceof Error ? err.message : 'Failed to extract tasks';
			isLoading = false;
		}
	}

	function toggleAccept(taskId: string) {
		if (acceptedTasks.has(taskId)) {
			acceptedTasks.delete(taskId);
		} else {
			acceptedTasks.add(taskId);
			rejectedTasks.delete(taskId);
		}
		acceptedTasks = new Set(acceptedTasks);
		rejectedTasks = new Set(rejectedTasks);
	}

	function toggleReject(taskId: string) {
		if (rejectedTasks.has(taskId)) {
			rejectedTasks.delete(taskId);
		} else {
			rejectedTasks.add(taskId);
			acceptedTasks.delete(taskId);
		}
		acceptedTasks = new Set(acceptedTasks);
		rejectedTasks = new Set(rejectedTasks);
	}

	function updateDate(taskId: string, date: string) {
		customDates.set(taskId, date);
		customDates = new Map(customDates);
	}

	async function exportAcceptedTasks() {
		isExporting = true;
		const accepted = tasks.filter(t => acceptedTasks.has(t.id)).map(t => ({
			...t,
			completion_date: customDates.get(t.id) || t.suggested_completion_date || 'TBD'
		}));

		// Download as JSON
		const blob = new Blob([JSON.stringify(accepted, null, 2)], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `tasks_${sessionId}.json`;
		a.click();
		URL.revokeObjectURL(url);

		isExporting = false;
	}

	function getCategoryColor(category: string): string {
		const colors = {
			implementation: 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200',
			research: 'bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200',
			decision: 'bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200',
			communication: 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200',
		};
		return colors[category as keyof typeof colors] || 'bg-slate-100 dark:bg-slate-900';
	}

	function getPriorityColor(priority: string): string {
		if (priority === 'high') return 'border-red-500 dark:border-red-400';
		if (priority === 'medium') return 'border-yellow-500 dark:border-yellow-400';
		return 'border-green-500 dark:border-green-400';
	}
</script>

<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-6 mt-6">
	<div class="flex items-center justify-between mb-4">
		<div>
			<h3 class="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
				</svg>
				Actionable Tasks
			</h3>
			{#if !isLoading && !error}
				<p class="text-sm text-slate-600 dark:text-slate-400 mt-1">
					<span class="font-medium text-green-600 dark:text-green-400">{acceptedTasks.size}</span> accepted,
					<span class="font-medium text-red-600 dark:text-red-400">{rejectedTasks.size}</span> rejected,
					<span class="font-medium text-slate-700 dark:text-slate-300">{tasks.length - acceptedTasks.size - rejectedTasks.size}</span> pending
				</p>
			{/if}
		</div>
		{#if acceptedTasks.size > 0}
			<button
				onclick={exportAcceptedTasks}
				disabled={isExporting}
				class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
				</svg>
				{isExporting ? 'Exporting...' : 'Export Accepted'}
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
				Task extraction requires a completed synthesis. This feature will appear automatically when synthesis is complete.
			</p>
		</div>
	{:else if tasks.length === 0}
		<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-8 text-center">
			<svg class="w-12 h-12 text-slate-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
			</svg>
			<p class="text-sm text-slate-600 dark:text-slate-400">
				No tasks extracted. This synthesis may not contain specific actionable steps.
			</p>
		</div>
	{:else}
		<div class="space-y-3">
			{#each tasks as task (task.id)}
				{@const isAccepted = acceptedTasks.has(task.id)}
				{@const isRejected = rejectedTasks.has(task.id)}
				<div
					class="border-l-4 {getPriorityColor(task.priority)} bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 {isRejected ? 'opacity-50' : ''}"
					transition:slide={{ duration: 200 }}
				>
					<div class="flex items-start gap-3">
						<div class="flex-1">
							<div class="flex items-start justify-between mb-2">
								<div class="flex items-center gap-2 flex-wrap">
									<span class="px-2 py-0.5 rounded text-xs font-medium {getCategoryColor(task.category)}">
										{task.category}
									</span>
									<Badge variant={task.priority === 'high' ? 'error' : task.priority === 'medium' ? 'warning' : 'success'} size="sm">
										{task.priority}
									</Badge>
									{#if task.dependencies.length > 0}
										<Badge variant="neutral" size="sm">
											{task.dependencies.length} dependencies
										</Badge>
									{/if}
								</div>
							</div>

							<p class="text-sm text-slate-900 dark:text-white font-medium mb-3">
								{task.description}
							</p>

							<div class="flex items-center gap-4 mb-3">
								<div class="flex items-center gap-2">
									<label for="task-date-{task.id}" class="text-xs text-slate-600 dark:text-slate-400">Due date:</label>
									<input
										id="task-date-{task.id}"
										type="date"
										value={customDates.get(task.id) || ''}
										onchange={(e) => updateDate(task.id, e.currentTarget.value)}
										class="px-2 py-1 text-xs border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
										placeholder={task.suggested_completion_date || 'Not specified'}
									/>
								</div>
								{#if task.suggested_completion_date}
									<span class="text-xs text-slate-500 dark:text-slate-400">
										Suggested: {task.suggested_completion_date}
									</span>
								{/if}
							</div>

							<div class="flex items-center gap-2">
								<button
									onclick={() => toggleAccept(task.id)}
									class="px-3 py-1 text-xs font-medium rounded-lg transition-colors {isAccepted ? 'bg-green-600 text-white' : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50'}"
								>
									{isAccepted ? '✓ Accepted' : 'Accept'}
								</button>
								<button
									onclick={() => toggleReject(task.id)}
									class="px-3 py-1 text-xs font-medium rounded-lg transition-colors {isRejected ? 'bg-red-600 text-white' : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/50'}"
								>
									{isRejected ? '✗ Rejected' : 'Reject'}
								</button>
							</div>
						</div>
					</div>

					<details class="mt-3">
						<summary class="text-xs text-slate-500 dark:text-slate-400 cursor-pointer hover:text-slate-700 dark:hover:text-slate-300">
							Details
						</summary>
						<div class="mt-2 text-xs text-slate-600 dark:text-slate-400 space-y-1">
							<p><strong>Source:</strong> {task.source_section.replace(/_/g, ' ')}</p>
							<p><strong>Confidence:</strong> {(task.confidence * 100).toFixed(0)}%</p>
							{#if task.dependencies.length > 0}
								<p><strong>Depends on:</strong> {task.dependencies.join(', ')}</p>
							{/if}
						</div>
					</details>
				</div>
			{/each}
		</div>
	{/if}
</div>
