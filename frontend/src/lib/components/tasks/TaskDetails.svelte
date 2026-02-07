<script lang="ts">
	/**
	 * TaskDetails - Expanded details section for a task.
	 * Shows What & How, Success Criteria, Kill Criteria, and Dependencies.
	 */

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
		source_section: string | null;
		confidence: number;
		sub_problem_index?: number | null;
	}

	interface Props {
		task: Task;
	}

	let { task }: Props = $props();

	// Get what and how from task or use description as fallback
	function getWhatAndHow(task: Task): string[] {
		if (task.what_and_how && task.what_and_how.length > 0) {
			return task.what_and_how;
		}
		return [task.description];
	}

	// Get success criteria from task or generate fallback
	function getSuccessCriteria(task: Task): string[] {
		if (task.success_criteria && task.success_criteria.length > 0) {
			return task.success_criteria;
		}

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
		if (task.kill_criteria && task.kill_criteria.length > 0) {
			return task.kill_criteria;
		}

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
</script>

<div class="px-5 sm:px-6 pb-5 sm:pb-6 pt-0 border-t border-neutral-200 dark:border-neutral-700">
	<div class="pt-5 space-y-5">
		<!-- What & How -->
		<div>
			<h5 class="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-2.5">What & How</h5>
			<ul class="space-y-2">
				{#each getWhatAndHow(task) as item}
					<li
						class="flex items-start gap-2 text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed"
					>
						<span class="text-neutral-400 dark:text-neutral-500 mt-1.5">•</span>
						<span>{item}</span>
					</li>
				{/each}
			</ul>
		</div>

		<!-- Success & Kill Criteria - Side by side on larger screens -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
			<!-- Success Criteria -->
			<div class="bg-success-50 dark:bg-success-900/20 rounded-lg p-4">
				<h5
					class="text-sm font-semibold text-success-800 dark:text-success-200 mb-2.5 flex items-center gap-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					Success Criteria
				</h5>
				<ul class="space-y-2">
					{#each getSuccessCriteria(task) as criterion}
						<li
							class="flex items-start gap-2 text-sm text-success-700 dark:text-success-300 leading-relaxed"
						>
							<span class="text-success-500 dark:text-success-400 mt-1">✓</span>
							<span>{criterion}</span>
						</li>
					{/each}
				</ul>
			</div>

			<!-- Kill Criteria -->
			<div class="bg-error-50 dark:bg-error-900/20 rounded-lg p-4">
				<h5
					class="text-sm font-semibold text-error-800 dark:text-error-200 mb-2.5 flex items-center gap-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
						/>
					</svg>
					Kill Criteria
				</h5>
				<ul class="space-y-2">
					{#each getKillCriteria(task) as criterion}
						<li
							class="flex items-start gap-2 text-sm text-error-700 dark:text-error-300 leading-relaxed"
						>
							<span class="text-error-500 dark:text-error-400 mt-1">✗</span>
							<span>{criterion}</span>
						</li>
					{/each}
				</ul>
			</div>
		</div>

		<!-- Dependencies -->
		{#if task.dependencies && task.dependencies.length > 0}
			<div class="bg-neutral-100 dark:bg-neutral-800 rounded-lg p-4">
				<h5
					class="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-2.5 flex items-center gap-2"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
						/>
					</svg>
					Dependencies
				</h5>
				<ul class="space-y-2">
					{#each task.dependencies as dep}
						<li
							class="flex items-start gap-2 text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed"
						>
							<span class="text-neutral-400 dark:text-neutral-500 mt-1">→</span>
							<span>{dep}</span>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	</div>
</div>
