<script lang="ts">
	/**
	 * ActionsPanel - Wrapper for task management in meeting context
	 *
	 * Handles loading, extracting, and displaying tasks for a session.
	 */
	import { onMount } from 'svelte';
	import { apiClient, ApiClientError } from '$lib/api/client';
	import type { TaskWithStatus, SessionActionsResponse } from '$lib/api/types';
	import KanbanBoard from './KanbanBoard.svelte';
	import { Button, Spinner } from '$lib/components/ui';

	interface Props {
		sessionId: string;
		sessionStatus: string;
	}

	let { sessionId, sessionStatus }: Props = $props();

	let loading = $state(true);
	let extracting = $state(false);
	let error = $state<string | null>(null);
	let actionsData = $state<SessionActionsResponse | null>(null);

	// Computed values
	const tasks = $derived<TaskWithStatus[]>(actionsData?.tasks || []);
	const canExtract = $derived(sessionStatus === 'completed' && !actionsData);

	onMount(() => {
		loadActions();
	});

	async function loadActions() {
		loading = true;
		error = null;

		try {
			const data = await apiClient.getSessionActions(sessionId);
			actionsData = data;
		} catch (err) {
			if (err instanceof ApiClientError && err.status === 404) {
				// No actions yet - that's fine
				actionsData = null;
			} else {
				error = err instanceof Error ? err.message : 'Failed to load actions';
			}
		} finally {
			loading = false;
		}
	}

	async function extractActions() {
		extracting = true;
		error = null;

		try {
			// First extract tasks
			await apiClient.extractTasks(sessionId);
			// Then load the actions with statuses
			await loadActions();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to extract actions';
		} finally {
			extracting = false;
		}
	}

	import type { ActionStatus } from '$lib/api/types';

	async function handleStatusChange(taskId: string, newStatus: ActionStatus) {
		if (!actionsData) return;

		// Optimistic update
		const oldTasks = [...actionsData.tasks];
		actionsData = {
			...actionsData,
			tasks: actionsData.tasks.map((t) =>
				t.id === taskId ? { ...t, status: newStatus } : t
			)
		};

		try {
			await apiClient.updateTaskStatus(sessionId, taskId, newStatus);
		} catch (err) {
			// Revert on error
			actionsData = { ...actionsData, tasks: oldTasks };
			error = err instanceof Error ? err.message : 'Failed to update status';
		}
	}

	async function handleDelete(taskId: string) {
		if (!actionsData) return;

		// Optimistic update - remove from list
		const oldTasks = [...actionsData.tasks];
		const oldByStatus = { ...actionsData.by_status };
		const taskToDelete = actionsData.tasks.find((t) => t.id === taskId);

		if (taskToDelete) {
			actionsData = {
				...actionsData,
				tasks: actionsData.tasks.filter((t) => t.id !== taskId),
				total_tasks: actionsData.total_tasks - 1,
				by_status: {
					...actionsData.by_status,
					[taskToDelete.status]: (actionsData.by_status[taskToDelete.status] || 1) - 1
				}
			};
		}

		try {
			await apiClient.deleteAction(taskId);
		} catch (err) {
			// Revert on error
			actionsData = { ...actionsData, tasks: oldTasks, total_tasks: oldTasks.length, by_status: oldByStatus };
			error = err instanceof Error ? err.message : 'Failed to delete action';
		}
	}
</script>

<div class="actions-panel">
	{#if loading}
		<div class="loading-state">
			<Spinner size="lg" />
			<p>Loading actions...</p>
		</div>
	{:else if error}
		<div class="error-state">
			<p class="error-message">{error}</p>
			<Button variant="secondary" onclick={loadActions}>
				{#snippet children()}
					Retry
				{/snippet}
			</Button>
		</div>
	{:else if !actionsData && canExtract}
		<div class="extract-state">
			<div class="extract-content">
				<h3>Extract Action Items</h3>
				<p>
					Analyze this meeting's synthesis to identify actionable tasks.
					Tasks will be organized in a Kanban board for easy tracking.
				</p>
				<Button variant="brand" onclick={extractActions} disabled={extracting}>
					{#snippet children()}
						{#if extracting}
							<Spinner size="sm" />
							<span>Extracting...</span>
						{:else}
							Extract Actions
						{/if}
					{/snippet}
				</Button>
			</div>
		</div>
	{:else if !actionsData}
		<div class="empty-state">
			<p>No actions available yet.</p>
			{#if sessionStatus !== 'completed'}
				<p class="hint">Actions can be extracted once the meeting is complete.</p>
			{/if}
		</div>
	{:else}
		<div class="kanban-container">
			<div class="kanban-header">
				<h3>Action Items ({actionsData.total_tasks})</h3>
				<div class="status-summary">
					<span class="status-badge todo">{actionsData.by_status.todo || 0} to do</span>
					<span class="status-badge doing">{actionsData.by_status.in_progress || 0} in progress</span>
					<span class="status-badge done">{actionsData.by_status.done || 0} done</span>
				</div>
			</div>
			<KanbanBoard tasks={tasks} onStatusChange={handleStatusChange} onDelete={handleDelete} loading={extracting} />
		</div>
	{/if}
</div>

<style>
	.actions-panel {
		padding: 16px;
		min-height: 400px;
	}

	.loading-state,
	.error-state,
	.extract-state,
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 300px;
		gap: 16px;
		text-align: center;
	}

	.loading-state p,
	.empty-state p {
		color: var(--color-muted);
	}

	.error-message {
		color: var(--color-error);
		margin-bottom: 8px;
	}

	.extract-content {
		max-width: 400px;
		padding: 24px;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 12px;
	}

	.extract-content h3 {
		margin: 0 0 8px 0;
		font-size: 1.1rem;
		color: var(--color-text);
	}

	.extract-content p {
		margin: 0 0 16px 0;
		color: var(--color-muted);
		font-size: 0.9rem;
		line-height: 1.5;
	}

	.hint {
		font-size: 0.85rem;
		color: var(--color-muted);
		font-style: italic;
	}

	.kanban-container {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.kanban-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex-wrap: wrap;
		gap: 12px;
	}

	.kanban-header h3 {
		margin: 0;
		font-size: 1.1rem;
		color: var(--color-text);
	}

	.status-summary {
		display: flex;
		gap: 8px;
	}

	.status-badge {
		font-size: 0.75rem;
		padding: 4px 8px;
		border-radius: 12px;
		font-weight: 500;
	}

	.status-badge.todo {
		background: var(--color-surface-hover);
		color: var(--color-muted);
	}

	.status-badge.doing {
		background: rgba(245, 158, 11, 0.1);
		color: var(--color-warning);
	}

	.status-badge.done {
		background: rgba(34, 197, 94, 0.1);
		color: var(--color-success);
	}
</style>
