<script lang="ts">
	/**
	 * KanbanBoard - Dynamic Kanban board for task management
	 * Features drag-and-drop between columns using svelte-dnd-action
	 * Supports user-defined columns via the columns prop
	 */
	import type { TaskWithStatus, TaskWithSessionContext, ActionStatus, KanbanColumn } from '$lib/api/types';
	import TaskCard from './TaskCard.svelte';
	import { dndzone, type DndEvent } from 'svelte-dnd-action';
	import { flip } from 'svelte/animate';

	type TaskType = TaskWithStatus | TaskWithSessionContext;

	// Default columns for fallback
	const DEFAULT_COLUMNS: KanbanColumn[] = [
		{ id: 'todo', title: 'To Do' },
		{ id: 'in_progress', title: 'In Progress' },
		{ id: 'done', title: 'Done' }
	];

	// Default colors for statuses (used when column.color is not set)
	const DEFAULT_STATUS_COLORS: Record<string, string> = {
		todo: 'var(--color-muted)',
		in_progress: 'var(--color-warning)',
		blocked: 'var(--color-error)',
		in_review: 'var(--color-info)',
		done: 'var(--color-success)',
		cancelled: 'var(--color-muted)',
		failed: 'var(--color-error)',
		abandoned: 'var(--color-muted)',
		replanned: 'var(--color-info)'
	};

	interface Props {
		tasks: TaskType[];
		onStatusChange: (taskId: string, newStatus: ActionStatus, sessionId?: string) => void;
		onDelete?: (taskId: string) => void;
		onTaskClick?: (taskId: string) => void;
		loading?: boolean;
		showMeetingContext?: boolean;
		columns?: KanbanColumn[];
	}

	let {
		tasks,
		onStatusChange,
		onDelete,
		onTaskClick,
		loading = false,
		showMeetingContext = false,
		columns = DEFAULT_COLUMNS
	}: Props = $props();

	// Type guard for TaskWithSessionContext
	function hasSessionContext(task: TaskType): task is TaskWithSessionContext {
		return 'session_id' in task && 'problem_statement' in task;
	}

	// Check if task is from a failed (but acknowledged) meeting
	function isFromFailedMeeting(task: TaskType): boolean {
		if (!hasSessionContext(task)) return false;
		return task.source_session_status === 'failed';
	}

	// Track tasks by column for drag-and-drop
	// Use a Map to support dynamic column IDs
	let columnTasks = $state<Map<string, TaskType[]>>(new Map());

	// Get the set of column IDs for quick lookup
	$effect(() => {
		const columnIds = new Set(columns.map(c => c.id));
		const newMap = new Map<string, TaskType[]>();

		// Initialize empty arrays for each column
		for (const col of columns) {
			newMap.set(col.id, []);
		}

		// Distribute tasks to columns
		for (const task of tasks) {
			if (columnIds.has(task.status)) {
				// Task status matches a column
				newMap.get(task.status)!.push(task);
			} else {
				// Unknown status: put in first column
				const firstCol = columns[0]?.id;
				if (firstCol) {
					newMap.get(firstCol)!.push(task);
				}
			}
		}

		columnTasks = newMap;
	});

	// Animation duration for flip
	const flipDurationMs = 200;

	// Get color for a column (use custom color or default based on status)
	function getColumnColor(column: KanbanColumn): string {
		return column.color || DEFAULT_STATUS_COLORS[column.id] || 'var(--color-muted)';
	}

	// Get tasks array for a specific column
	function getColumnTasksArray(columnId: string): TaskType[] {
		return columnTasks.get(columnId) || [];
	}

	// Handle drag consider (while dragging)
	function handleDndConsider(columnId: string, e: CustomEvent<DndEvent<TaskType>>) {
		const newMap = new Map(columnTasks);
		newMap.set(columnId, e.detail.items);
		columnTasks = newMap;
	}

	// Handle drag finalize (drop completed)
	function handleDndFinalize(columnId: string, e: CustomEvent<DndEvent<TaskType>>) {
		const items = e.detail.items;
		const newMap = new Map(columnTasks);
		newMap.set(columnId, items);
		columnTasks = newMap;

		// Find items that changed status and trigger onStatusChange
		for (const item of items) {
			if (item.status !== columnId) {
				const sessionId = hasSessionContext(item) ? item.session_id : undefined;
				onStatusChange(item.id, columnId as ActionStatus, sessionId);
			}
		}
	}

	// Helper to truncate text
	function truncate(text: string, maxLen: number = 40): string {
		if (text.length <= maxLen) return text;
		return text.substring(0, maxLen) + '...';
	}
</script>

<div class="kanban-board" class:loading style="--column-count: {columns.length}" data-tour="kanban-board">
	{#each columns as column, idx (column.id)}
		{@const tasksInColumn = getColumnTasksArray(column.id)}
		<div class="kanban-column" data-tour={idx === 0 ? 'kanban-column' : undefined}>
			<div class="column-header" style="--column-color: {getColumnColor(column)}">
				<span class="column-title">{column.title}</span>
				<span class="column-count">{tasksInColumn.length}</span>
			</div>
			<div
				class="column-content"
				class:empty={tasksInColumn.length === 0}
				use:dndzone={{
					items: tasksInColumn,
					flipDurationMs,
					dropTargetStyle: { outline: '2px dashed var(--color-brand)', outlineOffset: '-2px' }
				}}
				onconsider={(e) => handleDndConsider(column.id, e)}
				onfinalize={(e) => handleDndFinalize(column.id, e)}
			>
				{#each tasksInColumn as task (task.id)}
					<div animate:flip={{ duration: flipDurationMs }} class="task-wrapper">
						{#if onTaskClick}
							<!-- Clickable task card with meeting context -->
							<button
								type="button"
								class="task-card-btn"
								onclick={() => onTaskClick(task.id)}
							>
								<TaskCard
									{task}
									onStatusChange={(id, status) => {
										const sessionId = hasSessionContext(task) ? task.session_id : undefined;
										onStatusChange(id, status, sessionId);
									}}
									{onDelete}
								/>
								{#if showMeetingContext && hasSessionContext(task)}
									<div class="meeting-context" class:from-failed={isFromFailedMeeting(task)}>
										{#if isFromFailedMeeting(task)}
											<span class="failed-badge" title="This action is from a meeting that didn't complete">⚠</span>
										{/if}
										From: {truncate(task.problem_statement)}
									</div>
								{/if}
							</button>
						{:else}
							<TaskCard
								{task}
								onStatusChange={(id, status) => {
									const sessionId = hasSessionContext(task) ? task.session_id : undefined;
									onStatusChange(id, status, sessionId);
								}}
								{onDelete}
							/>
							{#if showMeetingContext && hasSessionContext(task)}
								<div class="meeting-context" class:from-failed={isFromFailedMeeting(task)}>
									{#if isFromFailedMeeting(task)}
										<span class="failed-badge" title="This action is from a meeting that didn't complete">⚠</span>
									{/if}
									From: {truncate(task.problem_statement)}
								</div>
							{/if}
						{/if}
					</div>
				{/each}
			</div>
			{#if tasksInColumn.length === 0}
				<div class="empty-hint">Drop tasks here</div>
			{/if}
		</div>
	{/each}
</div>

<style>
	.kanban-board {
		display: grid;
		grid-template-columns: repeat(var(--column-count, 3), 1fr);
		gap: 16px;
		min-height: 400px;
	}

	.kanban-board.loading {
		opacity: 0.6;
		pointer-events: none;
	}

	@media (max-width: 900px) {
		.kanban-board {
			grid-template-columns: 1fr;
		}
	}

	.kanban-column {
		position: relative;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 12px;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.column-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px 16px;
		border-bottom: 2px solid var(--column-color);
		background: var(--color-surface-hover);
	}

	.column-title {
		font-weight: 600;
		font-size: 0.95rem;
		color: var(--foreground);
	}

	.column-count {
		background: var(--column-color);
		color: white;
		font-size: 0.75rem;
		font-weight: 600;
		padding: 2px 8px;
		border-radius: 10px;
	}

	.column-content {
		padding: 12px;
		flex: 1;
		overflow-y: auto;
		max-height: 600px;
		min-height: 100px;
	}

	.column-content.empty {
		border: 2px dashed var(--color-border);
		border-radius: 8px;
		margin: 4px;
	}

	.empty-hint {
		text-align: center;
		padding: 8px;
		color: var(--color-muted);
		font-size: 0.8rem;
		pointer-events: none;
		position: absolute;
		top: 50%;
		left: 0;
		right: 0;
		transform: translateY(-50%);
	}

	.task-wrapper {
		margin-bottom: 8px;
		cursor: grab;
	}

	.task-wrapper:active {
		cursor: grabbing;
	}

	.task-card-btn {
		all: unset;
		display: block;
		width: 100%;
		cursor: pointer;
	}

	.task-card-btn:hover {
		transform: translateY(-1px);
	}

	.meeting-context {
		margin-top: 6px;
		padding: 4px 8px;
		background: var(--color-surface-hover);
		border-radius: 4px;
		font-size: 0.75rem;
		color: var(--color-brand);
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.meeting-context.from-failed {
		background: rgb(245, 158, 11, 0.15);
		color: rgb(180, 83, 9);
		border: 1px solid rgb(245, 158, 11, 0.3);
	}

	:global(.dark) .meeting-context.from-failed {
		background: rgb(245, 158, 11, 0.1);
		color: rgb(251, 191, 36);
		border-color: rgb(245, 158, 11, 0.2);
	}

	.failed-badge {
		font-size: 0.7rem;
	}

	/* Styles for dragged items (provided by svelte-dnd-action) */
	:global(.kanban-column .column-content [data-is-dnd-shadow-item]) {
		opacity: 0.4;
		border: 2px dashed var(--color-brand);
		border-radius: 8px;
	}
</style>
