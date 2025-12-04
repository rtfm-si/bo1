<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { ActionDetailResponse } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';
	import {
		ArrowLeft,
		CheckCircle2,
		Circle,
		Clock,
		Target,
		XCircle,
		Link2,
		Calendar,
		AlertTriangle,
		Layers
	} from 'lucide-svelte';

	const sessionId = $page.params.session_id!;
	const taskId = $page.params.task_id!;

	let action = $state<ActionDetailResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let isUpdatingStatus = $state(false);

	// Status configuration
	const statusConfig = {
		todo: {
			label: 'To Do',
			icon: Circle,
			bgColor: 'bg-neutral-100 dark:bg-neutral-800',
			textColor: 'text-neutral-700 dark:text-neutral-300',
			borderColor: 'border-neutral-300 dark:border-neutral-600'
		},
		doing: {
			label: 'In Progress',
			icon: Clock,
			bgColor: 'bg-brand-50 dark:bg-brand-900/20',
			textColor: 'text-brand-700 dark:text-brand-300',
			borderColor: 'border-brand-300 dark:border-brand-700'
		},
		done: {
			label: 'Done',
			icon: CheckCircle2,
			bgColor: 'bg-success-50 dark:bg-success-900/20',
			textColor: 'text-success-700 dark:text-success-300',
			borderColor: 'border-success-300 dark:border-success-700'
		}
	};

	// Priority configuration
	const priorityConfig = {
		high: { label: 'High', color: 'text-error-600 dark:text-error-400', bg: 'bg-error-100 dark:bg-error-900/30' },
		medium: { label: 'Medium', color: 'text-warning-600 dark:text-warning-400', bg: 'bg-warning-100 dark:bg-warning-900/30' },
		low: { label: 'Low', color: 'text-neutral-600 dark:text-neutral-400', bg: 'bg-neutral-100 dark:bg-neutral-800' }
	};

	// Category configuration
	const categoryConfig = {
		implementation: { label: 'Implementation', color: 'text-brand-600 dark:text-brand-400' },
		research: { label: 'Research', color: 'text-purple-600 dark:text-purple-400' },
		decision: { label: 'Decision', color: 'text-amber-600 dark:text-amber-400' },
		communication: { label: 'Communication', color: 'text-teal-600 dark:text-teal-400' }
	};

	async function loadAction() {
		try {
			isLoading = true;
			error = null;
			action = await apiClient.getActionDetail(sessionId, taskId);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load action';
		} finally {
			isLoading = false;
		}
	}

	async function updateStatus(newStatus: 'todo' | 'doing' | 'done') {
		if (!action || action.status === newStatus || isUpdatingStatus) return;

		try {
			isUpdatingStatus = true;
			await apiClient.updateTaskStatus(sessionId, taskId, newStatus);
			action = { ...action, status: newStatus };
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to update status';
		} finally {
			isUpdatingStatus = false;
		}
	}

	function goBack() {
		goto('/actions');
	}

	function goToMeeting() {
		goto(`/meeting/${sessionId}`);
	}

	onMount(() => {
		loadAction();
	});
</script>

<svelte:head>
	<title>{action?.title ?? 'Action'} | Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-950">
	<!-- Header -->
	<div class="sticky top-0 z-10 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 py-4">
			<div class="flex items-center gap-4">
				<button
					onclick={goBack}
					class="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
				>
					<ArrowLeft class="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
				</button>
				<div class="flex-1 min-w-0">
					<h1 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 truncate">
						{#if isLoading}
							<span class="animate-pulse bg-neutral-200 dark:bg-neutral-700 rounded h-6 w-48 inline-block"></span>
						{:else if action}
							{action.title}
						{:else}
							Action Not Found
						{/if}
					</h1>
				</div>
			</div>
		</div>
	</div>

	<div class="max-w-4xl mx-auto px-4 sm:px-6 py-6">
		{#if isLoading}
			<!-- Loading skeleton -->
			<div class="space-y-6 animate-pulse">
				<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm">
					<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4 mb-4"></div>
					<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2"></div>
				</div>
				<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm">
					<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/4 mb-4"></div>
					<div class="space-y-2">
						<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-full"></div>
						<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-5/6"></div>
					</div>
				</div>
			</div>
		{:else if error}
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-xl p-6 text-center">
				<AlertTriangle class="w-12 h-12 text-error-500 mx-auto mb-3" />
				<h2 class="text-lg font-semibold text-error-900 dark:text-error-100 mb-2">Error Loading Action</h2>
				<p class="text-error-700 dark:text-error-300 mb-4">{error}</p>
				<Button variant="secondary" onclick={loadAction}>Try Again</Button>
			</div>
		{:else if action}
			<div class="space-y-6">
				<!-- Status & Quick Actions -->
				<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<!-- Current Status -->
						<div class="flex items-center gap-3">
							<span class="text-sm font-medium text-neutral-500 dark:text-neutral-400">Status:</span>
							<div class={`flex items-center gap-2 px-3 py-1.5 rounded-full ${statusConfig[action.status].bgColor} ${statusConfig[action.status].textColor} border ${statusConfig[action.status].borderColor}`}>
								{#if action.status === 'todo'}
									<Circle class="w-4 h-4" />
								{:else if action.status === 'doing'}
									<Clock class="w-4 h-4" />
								{:else}
									<CheckCircle2 class="w-4 h-4" />
								{/if}
								<span class="text-sm font-medium">{statusConfig[action.status].label}</span>
							</div>
						</div>

						<!-- Status Change Buttons -->
						<div class="flex items-center gap-2">
							{#if action.status !== 'todo'}
								<Button
									variant="ghost"
									size="sm"
									onclick={() => updateStatus('todo')}
									disabled={isUpdatingStatus}
								>
									<Circle class="w-4 h-4 mr-1" />
									To Do
								</Button>
							{/if}
							{#if action.status !== 'doing'}
								<Button
									variant="ghost"
									size="sm"
									onclick={() => updateStatus('doing')}
									disabled={isUpdatingStatus}
								>
									<Clock class="w-4 h-4 mr-1" />
									Start
								</Button>
							{/if}
							{#if action.status !== 'done'}
								<Button
									variant="brand"
									size="sm"
									onclick={() => updateStatus('done')}
									disabled={isUpdatingStatus}
								>
									<CheckCircle2 class="w-4 h-4 mr-1" />
									Complete
								</Button>
							{/if}
						</div>
					</div>
				</div>

				<!-- Meta Info -->
				<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
					<div class="flex flex-wrap gap-4">
						<!-- Priority -->
						<div class="flex items-center gap-2">
							<span class="text-sm text-neutral-500 dark:text-neutral-400">Priority:</span>
							<span class={`text-sm font-medium px-2 py-0.5 rounded ${priorityConfig[action.priority].bg} ${priorityConfig[action.priority].color}`}>
								{priorityConfig[action.priority].label}
							</span>
						</div>

						<!-- Category -->
						<div class="flex items-center gap-2">
							<Layers class="w-4 h-4 text-neutral-400" />
							<span class={`text-sm font-medium ${categoryConfig[action.category].color}`}>
								{categoryConfig[action.category].label}
							</span>
						</div>

						<!-- Timeline -->
						{#if action.timeline}
							<div class="flex items-center gap-2">
								<Calendar class="w-4 h-4 text-neutral-400" />
								<span class="text-sm text-neutral-600 dark:text-neutral-400">{action.timeline}</span>
							</div>
						{/if}

						<!-- Confidence -->
						<div class="flex items-center gap-2">
							<span class="text-sm text-neutral-500 dark:text-neutral-400">Confidence:</span>
							<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">
								{Math.round(action.confidence * 100)}%
							</span>
						</div>
					</div>

					<!-- Source Meeting Link -->
					<div class="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
						<button
							onclick={goToMeeting}
							class="flex items-center gap-2 text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 transition-colors"
						>
							<Link2 class="w-4 h-4" />
							<span class="truncate max-w-md">{action.problem_statement}</span>
						</button>
					</div>
				</div>

				<!-- Description -->
				<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
					<h2 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-3">
						Description
					</h2>
					<p class="text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
						{action.description}
					</p>
				</div>

				<!-- Steps (What & How) -->
				{#if action.what_and_how.length > 0}
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
						<h2 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-3">
							Steps to Complete
						</h2>
						<ul class="space-y-2">
							{#each action.what_and_how as step, i (i)}
								<li class="flex items-start gap-3">
									<span class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 text-sm font-medium flex items-center justify-center">
										{i + 1}
									</span>
									<span class="text-neutral-700 dark:text-neutral-300 pt-0.5">{step}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Success Criteria -->
				{#if action.success_criteria.length > 0}
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
						<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-3">
							<Target class="w-4 h-4 text-success-500" />
							Success Criteria
						</h2>
						<ul class="space-y-2">
							{#each action.success_criteria as criterion, i (i)}
								<li class="flex items-start gap-2 text-neutral-700 dark:text-neutral-300">
									<CheckCircle2 class="w-4 h-4 text-success-500 mt-1 flex-shrink-0" />
									<span>{criterion}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Kill Criteria -->
				{#if action.kill_criteria.length > 0}
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
						<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-3">
							<XCircle class="w-4 h-4 text-error-500" />
							Stop Conditions
						</h2>
						<ul class="space-y-2">
							{#each action.kill_criteria as criterion, i (i)}
								<li class="flex items-start gap-2 text-neutral-700 dark:text-neutral-300">
									<XCircle class="w-4 h-4 text-error-500 mt-1 flex-shrink-0" />
									<span>{criterion}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Dependencies -->
				{#if action.dependencies.length > 0}
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
						<h2 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-3">
							Dependencies
						</h2>
						<ul class="space-y-2">
							{#each action.dependencies as dependency, i (i)}
								<li class="flex items-start gap-2 text-neutral-700 dark:text-neutral-300">
									<span class="text-neutral-400">-</span>
									<span>{dependency}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Back Button -->
				<div class="pt-4">
					<Button variant="ghost" onclick={goBack}>
						<ArrowLeft class="w-4 h-4 mr-2" />
						Back to Actions
					</Button>
				</div>
			</div>
		{/if}
	</div>
</div>
