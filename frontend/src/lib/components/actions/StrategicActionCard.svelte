<script lang="ts">
	/**
	 * StrategicActionCard - Parent action card with collapsible child tasks
	 * Shows meta-synthesis strategic actions with progress tracking
	 */
	import type { TaskWithSessionContext, ActionStatus } from '$lib/api/types';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		action: TaskWithSessionContext;
		children: TaskWithSessionContext[];
		onStatusChange: (taskId: string, newStatus: ActionStatus) => void;
		onTaskClick?: (taskId: string) => void;
	}

	let { action, children, onStatusChange, onTaskClick }: Props = $props();

	let expanded = $state(false);

	const doneCount = $derived(children.filter((c) => c.status === 'done').length);
	const totalCount = $derived(children.length);
	const progressPct = $derived(totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0);

	const priorityColors: Record<string, string> = {
		high: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20',
		medium: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20',
		low: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20'
	};

	function handleChildToggle(child: TaskWithSessionContext) {
		const newStatus: ActionStatus = child.status === 'done' ? 'todo' : 'done';
		onStatusChange(child.id, newStatus);
	}
</script>

<div
	class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden"
>
	<!-- Parent Action Header -->
	<button
		class="w-full text-left p-4 hover:bg-neutral-50 dark:hover:bg-neutral-750 transition-colors"
		onclick={() => (expanded = !expanded)}
	>
		<div class="flex items-start gap-3">
			<!-- Expand chevron -->
			<svg
				class="w-5 h-5 mt-0.5 text-neutral-400 transition-transform flex-shrink-0 {expanded
					? 'rotate-90'
					: ''}"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 5l7 7-7 7"
				/>
			</svg>

			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-1">
					<h3 class="text-base font-semibold text-neutral-900 dark:text-white truncate">
						{action.title}
					</h3>
					<span
						class="px-2 py-0.5 text-xs font-medium rounded-full flex-shrink-0 {priorityColors[
							action.priority
						] || priorityColors.medium}"
					>
						{action.priority}
					</span>
					{#if action.timeline}
						<span
							class="text-xs text-neutral-500 dark:text-neutral-400 flex-shrink-0"
						>
							{action.timeline}
						</span>
					{/if}
				</div>

				<p class="text-sm text-neutral-600 dark:text-neutral-400 line-clamp-2">
					{action.description}
				</p>

				<!-- Progress bar -->
				{#if totalCount > 0}
					<div class="mt-3 flex items-center gap-3">
						<div class="flex-1 h-1.5 bg-neutral-100 dark:bg-neutral-700 rounded-full overflow-hidden">
							<div
								class="h-full rounded-full transition-all duration-300 {progressPct === 100
									? 'bg-green-500'
									: 'bg-brand-500'}"
								style="width: {progressPct}%"
							></div>
						</div>
						<span class="text-xs font-medium text-neutral-500 dark:text-neutral-400 whitespace-nowrap">
							{doneCount}/{totalCount} tasks
						</span>
					</div>
				{/if}
			</div>

			<!-- Parent action status badge -->
			<Badge
				variant={action.status === 'done'
					? 'success'
					: action.status === 'in_progress'
						? 'warning'
						: 'neutral'}
			>
				{action.status === 'in_progress' ? 'In Progress' : action.status === 'done' ? 'Done' : 'To Do'}
			</Badge>
		</div>
	</button>

	<!-- Expanded Children -->
	{#if expanded && children.length > 0}
		<div class="border-t border-neutral-100 dark:border-neutral-700">
			{#each children as child (child.id)}
				<div
					class="flex items-center gap-3 px-4 py-3 pl-12 hover:bg-neutral-50 dark:hover:bg-neutral-750 border-b border-neutral-50 dark:border-neutral-700/50 last:border-b-0"
				>
					<!-- Checkbox -->
					<button
						class="flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors {child.status ===
						'done'
							? 'bg-green-500 border-green-500 text-white'
							: 'border-neutral-300 dark:border-neutral-600 hover:border-brand-500'}"
						onclick={(e: MouseEvent) => { e.stopPropagation(); handleChildToggle(child); }}
					>
						{#if child.status === 'done'}
							<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="3"
									d="M5 13l4 4L19 7"
								/>
							</svg>
						{/if}
					</button>

					<!-- Task info -->
					<button
						class="flex-1 min-w-0 text-left"
						onclick={() => onTaskClick?.(child.id)}
					>
						<span
							class="text-sm {child.status === 'done'
								? 'text-neutral-400 dark:text-neutral-500 line-through'
								: 'text-neutral-900 dark:text-white'}"
						>
							{child.title}
						</span>
					</button>

					<!-- Priority dot -->
					<span
						class="w-2 h-2 rounded-full flex-shrink-0 {child.priority === 'high'
							? 'bg-red-500'
							: child.priority === 'medium'
								? 'bg-amber-500'
								: 'bg-green-500'}"
					></span>

					<!-- Status badge -->
					{#if child.status !== 'todo' && child.status !== 'done'}
						<Badge
							variant={child.status === 'in_progress'
								? 'warning'
								: child.status === 'blocked'
									? 'error'
									: 'info'}
						>
							{child.status.replace('_', ' ')}
						</Badge>
					{/if}
				</div>
			{/each}
		</div>
	{:else if expanded}
		<div
			class="px-4 py-6 text-center text-sm text-neutral-500 dark:text-neutral-400 border-t border-neutral-100 dark:border-neutral-700"
		>
			No child tasks linked to this action yet
		</div>
	{/if}
</div>
