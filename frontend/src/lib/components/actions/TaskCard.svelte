<script lang="ts">
	/**
	 * TaskCard - Individual task card for Kanban board
	 */
	import type { TaskWithStatus } from '$lib/api/types';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { Trash2 } from 'lucide-svelte';

	import type { ActionStatus } from '$lib/api/types';

	interface Props {
		task: TaskWithStatus;
		onStatusChange: (taskId: string, newStatus: ActionStatus) => void;
		onDelete?: (taskId: string) => void;
	}

	let { task, onStatusChange, onDelete }: Props = $props();

	let showDeleteConfirm = $state(false);

	// Determine next status for quick action button
	const nextStatus = $derived(
		task.status === 'todo' ? 'in_progress' : task.status === 'in_progress' ? 'done' : null
	);

	const priorityColors = {
		high: 'var(--color-error)',
		medium: 'var(--color-warning)',
		low: 'var(--color-success)'
	};

	const categoryIcons = {
		implementation: 'wrench',
		research: 'magnifying-glass',
		decision: 'scale',
		communication: 'chat'
	};

	let expanded = $state(false);
</script>

<div
	class="task-card"
	style="--priority-color: {priorityColors[task.priority as keyof typeof priorityColors] || 'var(--color-muted)'}"
>
	<div class="task-header">
		<span class="task-title">{task.title}</span>
		<button class="expand-btn" onclick={() => (expanded = !expanded)}>
			{expanded ? '-' : '+'}
		</button>
	</div>

	<p class="task-description">{task.description}</p>

	<div class="task-meta">
		<Badge variant={task.priority === 'high' ? 'error' : task.priority === 'medium' ? 'warning' : 'success'}>
			{task.priority}
		</Badge>
		<Badge variant="info">{task.category}</Badge>
		{#if task.timeline}
			<span class="timeline">{task.timeline}</span>
		{/if}
	</div>

	{#if expanded}
		<div class="task-details">
			{#if task.what_and_how.length > 0}
				<div class="detail-section">
					<strong>How to do it:</strong>
					<ul>
						{#each task.what_and_how as step}
							<li>{step}</li>
						{/each}
					</ul>
				</div>
			{/if}

			{#if task.success_criteria.length > 0}
				<div class="detail-section">
					<strong>Success looks like:</strong>
					<ul>
						{#each task.success_criteria as criterion}
							<li>{criterion}</li>
						{/each}
					</ul>
				</div>
			{/if}

			{#if task.kill_criteria.length > 0}
				<div class="detail-section">
					<strong>Stop if:</strong>
					<ul>
						{#each task.kill_criteria as criterion}
							<li>{criterion}</li>
						{/each}
					</ul>
				</div>
			{/if}

			{#if task.dependencies.length > 0}
				<div class="detail-section">
					<strong>Depends on:</strong>
					<ul>
						{#each task.dependencies as dep}
							<li>{dep}</li>
						{/each}
					</ul>
				</div>
			{/if}
		</div>
	{/if}

	<div class="task-actions">
		{#if nextStatus}
			<button class="action-btn primary" onclick={() => onStatusChange(task.id, nextStatus)}>
				{nextStatus === 'in_progress' ? 'Start' : 'Complete'}
			</button>
		{/if}
		{#if task.status === 'in_progress'}
			<button class="action-btn secondary" onclick={() => onStatusChange(task.id, 'todo')}>
				Move back
			</button>
		{/if}
		{#if task.status === 'done'}
			<button class="action-btn secondary" onclick={() => onStatusChange(task.id, 'in_progress')}>
				Reopen
			</button>
		{/if}
		{#if onDelete}
			<button
				class="action-btn delete"
				onclick={() => showDeleteConfirm = true}
				title="Delete action"
			>
				<Trash2 class="h-4 w-4" />
			</button>
		{/if}
	</div>

	<!-- Delete confirmation overlay -->
	{#if showDeleteConfirm}
		<div class="delete-confirm-overlay">
			<p>Delete this action?</p>
			<div class="confirm-actions">
				<button class="action-btn danger" onclick={() => { onDelete?.(task.id); showDeleteConfirm = false; }}>
					Delete
				</button>
				<button class="action-btn secondary" onclick={() => showDeleteConfirm = false}>
					Cancel
				</button>
			</div>
		</div>
	{/if}
</div>

<style>
	.task-card {
		position: relative;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-left: 3px solid var(--priority-color);
		border-radius: 8px;
		padding: 12px;
		margin-bottom: 8px;
		transition: box-shadow 0.2s;
	}

	.task-card:hover {
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.task-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 8px;
	}

	.task-title {
		font-weight: 600;
		font-size: 0.95rem;
		color: var(--color-text);
		flex: 1;
	}

	.expand-btn {
		background: none;
		border: 1px solid var(--color-border);
		border-radius: 4px;
		width: 24px;
		height: 24px;
		cursor: pointer;
		color: var(--color-muted);
		font-size: 14px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.expand-btn:hover {
		background: var(--color-surface-hover);
	}

	.task-description {
		font-size: 0.85rem;
		color: var(--color-muted);
		margin-bottom: 8px;
		line-height: 1.4;
	}

	.task-meta {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
		align-items: center;
		margin-bottom: 8px;
	}

	.timeline {
		font-size: 0.75rem;
		color: var(--color-muted);
		padding: 2px 6px;
		background: var(--color-surface-hover);
		border-radius: 4px;
	}

	.task-details {
		margin-top: 12px;
		padding-top: 12px;
		border-top: 1px solid var(--color-border);
	}

	.detail-section {
		margin-bottom: 12px;
	}

	.detail-section strong {
		display: block;
		font-size: 0.8rem;
		color: var(--color-muted);
		margin-bottom: 4px;
	}

	.detail-section ul {
		margin: 0;
		padding-left: 16px;
		font-size: 0.85rem;
		color: var(--color-text);
	}

	.detail-section li {
		margin-bottom: 2px;
	}

	.task-actions {
		display: flex;
		gap: 8px;
		margin-top: 8px;
	}

	.action-btn {
		padding: 6px 12px;
		border-radius: 6px;
		font-size: 0.8rem;
		cursor: pointer;
		border: none;
		transition: all 0.2s;
	}

	.action-btn.primary {
		background: var(--color-primary);
		color: white;
	}

	.action-btn.primary:hover {
		filter: brightness(1.1);
	}

	.action-btn.secondary {
		background: var(--color-surface-hover);
		color: var(--color-text);
		border: 1px solid var(--color-border);
	}

	.action-btn.secondary:hover {
		background: var(--color-border);
	}

	.action-btn.delete {
		background: transparent;
		color: var(--color-muted);
		border: 1px solid var(--color-border);
		padding: 6px;
		margin-left: auto;
	}

	.action-btn.delete:hover {
		background: var(--color-error);
		color: white;
		border-color: var(--color-error);
	}

	.action-btn.danger {
		background: var(--color-error);
		color: white;
	}

	.action-btn.danger:hover {
		filter: brightness(1.1);
	}

	.delete-confirm-overlay {
		position: absolute;
		inset: 0;
		background: rgba(255, 255, 255, 0.95);
		border-radius: 8px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		z-index: 10;
	}

	:global(.dark) .delete-confirm-overlay {
		background: rgba(23, 23, 23, 0.95);
	}

	.delete-confirm-overlay p {
		font-size: 0.9rem;
		font-weight: 500;
		color: var(--color-text);
		margin: 0;
	}

	.confirm-actions {
		display: flex;
		gap: 8px;
	}
</style>
