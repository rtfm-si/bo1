<script lang="ts">
	/**
	 * KanbanBoard - Three-column Kanban board for task management
	 * Features drag-and-drop between columns using svelte-dnd-action
	 */
	import type { TaskWithStatus, ActionStatus } from '$lib/api/types';
	import TaskCard from './TaskCard.svelte';
	import { dndzone, type DndEvent } from 'svelte-dnd-action';
	import { flip } from 'svelte/animate';

	interface Props {
		tasks: TaskWithStatus[];
		onStatusChange: (taskId: string, newStatus: ActionStatus) => void;
		onDelete?: (taskId: string) => void;
		loading?: boolean;
	}

	let { tasks, onStatusChange, onDelete, loading = false }: Props = $props();

	// Track tasks by column for drag-and-drop
	// We need mutable state for dndzone to work
	let todoTasks = $state<TaskWithStatus[]>([]);
	let inProgressTasks = $state<TaskWithStatus[]>([]);
	let doneTasks = $state<TaskWithStatus[]>([]);

	// Sync from props when tasks change
	$effect(() => {
		todoTasks = tasks.filter((t) => t.status === 'todo');
		inProgressTasks = tasks.filter((t) => t.status === 'in_progress');
		doneTasks = tasks.filter((t) => t.status === 'done');
	});

	// Animation duration for flip
	const flipDurationMs = 200;

	// Column configuration
	const columns: { id: ActionStatus; title: string; color: string }[] = [
		{ id: 'todo', title: 'To Do', color: 'var(--color-muted)' },
		{ id: 'in_progress', title: 'In Progress', color: 'var(--color-warning)' },
		{ id: 'done', title: 'Done', color: 'var(--color-success)' }
	];

	// Get tasks array for a specific column
	function getColumnTasks(status: ActionStatus): TaskWithStatus[] {
		switch (status) {
			case 'todo':
				return todoTasks;
			case 'in_progress':
				return inProgressTasks;
			case 'done':
				return doneTasks;
			default:
				return [];
		}
	}

	// Handle drag consider (while dragging)
	function handleDndConsider(status: ActionStatus, e: CustomEvent<DndEvent<TaskWithStatus>>) {
		switch (status) {
			case 'todo':
				todoTasks = e.detail.items;
				break;
			case 'in_progress':
				inProgressTasks = e.detail.items;
				break;
			case 'done':
				doneTasks = e.detail.items;
				break;
		}
	}

	// Handle drag finalize (drop completed)
	function handleDndFinalize(status: ActionStatus, e: CustomEvent<DndEvent<TaskWithStatus>>) {
		const items = e.detail.items;

		// Update the column state
		switch (status) {
			case 'todo':
				todoTasks = items;
				break;
			case 'in_progress':
				inProgressTasks = items;
				break;
			case 'done':
				doneTasks = items;
				break;
		}

		// Find items that changed status and trigger onStatusChange
		for (const item of items) {
			if (item.status !== status) {
				onStatusChange(item.id, status);
			}
		}
	}
</script>

<div class="kanban-board" class:loading>
	{#each columns as column (column.id)}
		{@const columnTasks = getColumnTasks(column.id)}
		<div class="kanban-column">
			<div class="column-header" style="--column-color: {column.color}">
				<span class="column-title">{column.title}</span>
				<span class="column-count">{columnTasks.length}</span>
			</div>
			<div
				class="column-content"
				class:empty={columnTasks.length === 0}
				use:dndzone={{
					items: columnTasks,
					flipDurationMs,
					dropTargetStyle: { outline: '2px dashed var(--color-brand)', outlineOffset: '-2px' }
				}}
				onconsider={(e) => handleDndConsider(column.id, e)}
				onfinalize={(e) => handleDndFinalize(column.id, e)}
			>
				{#each columnTasks as task (task.id)}
					<div animate:flip={{ duration: flipDurationMs }} class="task-wrapper">
						<TaskCard {task} {onStatusChange} {onDelete} />
					</div>
				{/each}
			</div>
			{#if columnTasks.length === 0}
				<div class="empty-hint">Drop tasks here</div>
			{/if}
		</div>
	{/each}
</div>

<style>
	.kanban-board {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
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
		color: var(--color-text);
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

	/* Styles for dragged items (provided by svelte-dnd-action) */
	:global(.kanban-column .column-content [data-is-dnd-shadow-item]) {
		opacity: 0.4;
		border: 2px dashed var(--color-brand);
		border-radius: 8px;
	}
</style>
