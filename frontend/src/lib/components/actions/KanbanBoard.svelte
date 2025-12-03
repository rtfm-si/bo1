<script lang="ts">
	/**
	 * KanbanBoard - Three-column Kanban board for task management
	 */
	import type { TaskWithStatus } from '$lib/api/types';
	import TaskCard from './TaskCard.svelte';

	interface Props {
		tasks: TaskWithStatus[];
		onStatusChange: (taskId: string, newStatus: 'todo' | 'doing' | 'done') => void;
		loading?: boolean;
	}

	let { tasks, onStatusChange, loading = false }: Props = $props();

	// Helper function to filter tasks by status (called reactively in template)
	function getTasksByStatus(status: 'todo' | 'doing' | 'done') {
		return tasks.filter((t) => t.status === status);
	}

	const columns = [
		{ id: 'todo' as const, title: 'To Do', color: 'var(--color-muted)' },
		{ id: 'doing' as const, title: 'In Progress', color: 'var(--color-warning)' },
		{ id: 'done' as const, title: 'Done', color: 'var(--color-success)' }
	];
</script>

<div class="kanban-board" class:loading>
	{#each columns as column (column.id)}
		{@const columnTasks = getTasksByStatus(column.id)}
		<div class="kanban-column">
			<div class="column-header" style="--column-color: {column.color}">
				<span class="column-title">{column.title}</span>
				<span class="column-count">{columnTasks.length}</span>
			</div>
			<div class="column-content">
				{#if columnTasks.length === 0}
					<div class="empty-state">
						{#if column.id === 'todo'}
							No pending tasks
						{:else if column.id === 'doing'}
							No tasks in progress
						{:else}
							No completed tasks
						{/if}
					</div>
				{:else}
					{#each columnTasks as task (task.id)}
						<TaskCard {task} {onStatusChange} />
					{/each}
				{/if}
			</div>
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
	}

	.empty-state {
		text-align: center;
		padding: 24px;
		color: var(--color-muted);
		font-size: 0.85rem;
	}
</style>
