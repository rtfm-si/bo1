<script lang="ts">
	/**
	 * DependencyGraph - Visual dependency chain for actions
	 * Shows upstream dependencies (what this action depends on)
	 */
	import type { DependencyResponse, ActionStatus, DependencyType } from '$lib/api/types';
	import { ArrowRight, Clock, CheckCircle2, Circle, AlertTriangle, XCircle, Timer } from 'lucide-svelte';

	interface Props {
		dependencies: DependencyResponse[];
		actionId: string;
		hasIncomplete?: boolean;
	}

	let { dependencies, actionId, hasIncomplete = false }: Props = $props();

	// Status configuration for badges
	const statusConfig: Record<ActionStatus, { label: string; bgColor: string; textColor: string; borderColor: string }> = {
		todo: {
			label: 'To Do',
			bgColor: 'bg-neutral-100 dark:bg-neutral-800',
			textColor: 'text-neutral-700 dark:text-neutral-300',
			borderColor: 'border-neutral-300 dark:border-neutral-600'
		},
		in_progress: {
			label: 'In Progress',
			bgColor: 'bg-brand-50 dark:bg-brand-900/20',
			textColor: 'text-brand-700 dark:text-brand-300',
			borderColor: 'border-brand-300 dark:border-brand-700'
		},
		blocked: {
			label: 'Blocked',
			bgColor: 'bg-error-50 dark:bg-error-900/20',
			textColor: 'text-error-700 dark:text-error-300',
			borderColor: 'border-error-300 dark:border-error-700'
		},
		in_review: {
			label: 'In Review',
			bgColor: 'bg-purple-50 dark:bg-purple-900/20',
			textColor: 'text-purple-700 dark:text-purple-300',
			borderColor: 'border-purple-300 dark:border-purple-700'
		},
		done: {
			label: 'Done',
			bgColor: 'bg-success-50 dark:bg-success-900/20',
			textColor: 'text-success-700 dark:text-success-300',
			borderColor: 'border-success-300 dark:border-success-700'
		},
		cancelled: {
			label: 'Cancelled',
			bgColor: 'bg-neutral-50 dark:bg-neutral-800',
			textColor: 'text-neutral-500 dark:text-neutral-400',
			borderColor: 'border-neutral-300 dark:border-neutral-600'
		},
		failed: {
			label: 'Failed',
			bgColor: 'bg-error-50 dark:bg-error-900/20',
			textColor: 'text-error-700 dark:text-error-300',
			borderColor: 'border-error-300 dark:border-error-700'
		},
		abandoned: {
			label: 'Abandoned',
			bgColor: 'bg-neutral-50 dark:bg-neutral-800',
			textColor: 'text-neutral-500 dark:text-neutral-400',
			borderColor: 'border-neutral-300 dark:border-neutral-600'
		},
		replanned: {
			label: 'Replanned',
			bgColor: 'bg-warning-50 dark:bg-warning-900/20',
			textColor: 'text-warning-700 dark:text-warning-300',
			borderColor: 'border-warning-300 dark:border-warning-700'
		}
	};

	// Format dependency type for display
	function formatDependencyType(type: DependencyType): string {
		switch (type) {
			case 'finish_to_start':
				return 'Finish → Start';
			case 'start_to_start':
				return 'Start → Start';
			case 'finish_to_finish':
				return 'Finish → Finish';
			default:
				return type;
		}
	}

	// Get status icon component
	function getStatusIcon(status: ActionStatus) {
		switch (status) {
			case 'done':
				return CheckCircle2;
			case 'in_progress':
			case 'in_review':
				return Clock;
			case 'blocked':
				return AlertTriangle;
			case 'cancelled':
				return XCircle;
			default:
				return Circle;
		}
	}

	// Check if a dependency is blocking (incomplete)
	function isBlocking(status: ActionStatus): boolean {
		return status !== 'done' && status !== 'cancelled';
	}
</script>

<div class="dependency-graph">
	{#if dependencies.length === 0}
		<div class="flex items-center justify-center py-4 text-neutral-500 dark:text-neutral-400">
			<p class="text-sm">No dependencies defined</p>
		</div>
	{:else}
		<!-- Blocking warning -->
		{#if hasIncomplete}
			<div class="mb-4 p-3 rounded-lg bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800">
				<div class="flex items-start gap-2">
					<AlertTriangle class="w-4 h-4 text-warning-500 mt-0.5 flex-shrink-0" />
					<div>
						<p class="text-sm font-medium text-warning-700 dark:text-warning-300">
							Blocked by incomplete dependencies
						</p>
						<p class="text-xs text-warning-600 dark:text-warning-400 mt-0.5">
							Complete the actions below to unblock this action
						</p>
					</div>
				</div>
			</div>
		{/if}

		<!-- Dependency chain visualization -->
		<div class="space-y-3">
			{#each dependencies as dep (dep.depends_on_action_id)}
				{@const config = statusConfig[dep.depends_on_status]}
				{@const StatusIcon = getStatusIcon(dep.depends_on_status)}
				{@const blocking = isBlocking(dep.depends_on_status)}

				<div class="flex items-center gap-3">
					<!-- Dependency action card -->
					<a
						href="/actions/{dep.depends_on_action_id}"
						class="flex-1 flex items-center gap-3 p-3 rounded-lg border transition-all hover:shadow-md {blocking ? 'border-warning-300 dark:border-warning-700 bg-warning-50/50 dark:bg-warning-900/10' : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900'}"
					>
						<!-- Status icon -->
						<div class={`flex-shrink-0 p-1.5 rounded-full ${config.bgColor} ${config.textColor}`}>
							<StatusIcon class="w-4 h-4" />
						</div>

						<!-- Action info -->
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<span class="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
									{dep.depends_on_title}
								</span>
								{#if blocking}
									<span class="flex-shrink-0 px-1.5 py-0.5 text-xs font-medium text-warning-700 dark:text-warning-300 bg-warning-100 dark:bg-warning-900/30 rounded">
										Blocking
									</span>
								{/if}
							</div>

							<!-- Status badge and type -->
							<div class="flex items-center gap-2 mt-1">
								<span class={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full border ${config.bgColor} ${config.textColor} ${config.borderColor}`}>
									{config.label}
								</span>
								<span class="text-xs text-neutral-500 dark:text-neutral-400">
									{formatDependencyType(dep.dependency_type as DependencyType)}
								</span>
								{#if dep.lag_days > 0}
									<span class="inline-flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
										<Timer class="w-3 h-3" />
										+{dep.lag_days}d lag
									</span>
								{/if}
							</div>
						</div>
					</a>

					<!-- Arrow to current action -->
					<div class="flex-shrink-0 text-neutral-400 dark:text-neutral-500">
						<ArrowRight class="w-5 h-5" />
					</div>

					<!-- Current action indicator (minimal) -->
					<div class="flex-shrink-0 px-3 py-2 rounded-lg bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800">
						<span class="text-sm font-medium text-brand-700 dark:text-brand-300">This Action</span>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
