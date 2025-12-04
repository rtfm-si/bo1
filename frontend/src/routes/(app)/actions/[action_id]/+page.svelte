<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { ActionDetailResponse, ActionUpdateResponse, ActionUpdateCreateRequest } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';
	import ActivityTimeline from '$lib/components/actions/ActivityTimeline.svelte';
	import UpdateInput from '$lib/components/actions/UpdateInput.svelte';
	import {
		ArrowLeft,
		CheckCircle2,
		Circle,
		Clock,
		Target,
		XCircle,
		Link2,
		Calendar,
		CalendarDays,
		CalendarCheck,
		AlertTriangle,
		Layers,
		Timer,
		History,
		Sparkles,
		Loader2,
		ExternalLink,
		X
	} from 'lucide-svelte';

	// Helper function to format dates nicely
	function formatDate(dateStr: string | null | undefined): string {
		if (!dateStr) return '—';
		try {
			const date = new Date(dateStr);
			return date.toLocaleDateString('en-US', {
				month: 'short',
				day: 'numeric',
				year: 'numeric'
			});
		} catch {
			return dateStr;
		}
	}

	// Check if action has any date information
	function hasAnyDates(action: ActionDetailResponse): boolean {
		return !!(
			action.target_start_date ||
			action.target_end_date ||
			action.estimated_start_date ||
			action.estimated_end_date ||
			action.actual_start_date ||
			action.actual_end_date ||
			action.estimated_duration_days
		);
	}

	const actionId = $page.params.action_id!;

	let action = $state<ActionDetailResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let isUpdatingStatus = $state(false);

	// Activity updates state
	let updates = $state<ActionUpdateResponse[]>([]);
	let updatesLoading = $state(false);
	let updatesError = $state<string | null>(null);

	// Replanning state
	let showReplanModal = $state(false);
	let replanContext = $state('');
	let isRequestingReplan = $state(false);
	let replanError = $state<string | null>(null);

	// Open replan modal
	function openReplanModal() {
		showReplanModal = true;
		replanContext = '';
		replanError = null;
	}

	// Close replan modal
	function closeReplanModal() {
		showReplanModal = false;
		replanContext = '';
		replanError = null;
	}

	// Submit replan request
	async function submitReplanRequest() {
		if (!action) return;

		isRequestingReplan = true;
		replanError = null;

		try {
			const result = await apiClient.requestReplan(
				action.id,
				replanContext.trim() || undefined
			);

			// Redirect to the replanning meeting
			goto(result.redirect_url);
		} catch (e) {
			console.error('Failed to request replan:', e);
			replanError = e instanceof Error ? e.message : 'Failed to create replanning session';
		} finally {
			isRequestingReplan = false;
		}
	}

	import type { ActionStatus } from '$lib/api/types';

	// Status configuration
	const statusConfig: Record<ActionStatus, { label: string; icon: typeof Circle; bgColor: string; textColor: string; borderColor: string }> = {
		todo: {
			label: 'To Do',
			icon: Circle,
			bgColor: 'bg-neutral-100 dark:bg-neutral-800',
			textColor: 'text-neutral-700 dark:text-neutral-300',
			borderColor: 'border-neutral-300 dark:border-neutral-600'
		},
		in_progress: {
			label: 'In Progress',
			icon: Clock,
			bgColor: 'bg-brand-50 dark:bg-brand-900/20',
			textColor: 'text-brand-700 dark:text-brand-300',
			borderColor: 'border-brand-300 dark:border-brand-700'
		},
		blocked: {
			label: 'Blocked',
			icon: AlertTriangle,
			bgColor: 'bg-error-50 dark:bg-error-900/20',
			textColor: 'text-error-700 dark:text-error-300',
			borderColor: 'border-error-300 dark:border-error-700'
		},
		in_review: {
			label: 'In Review',
			icon: Clock,
			bgColor: 'bg-purple-50 dark:bg-purple-900/20',
			textColor: 'text-purple-700 dark:text-purple-300',
			borderColor: 'border-purple-300 dark:border-purple-700'
		},
		done: {
			label: 'Done',
			icon: CheckCircle2,
			bgColor: 'bg-success-50 dark:bg-success-900/20',
			textColor: 'text-success-700 dark:text-success-300',
			borderColor: 'border-success-300 dark:border-success-700'
		},
		cancelled: {
			label: 'Cancelled',
			icon: XCircle,
			bgColor: 'bg-neutral-50 dark:bg-neutral-800',
			textColor: 'text-neutral-500 dark:text-neutral-400',
			borderColor: 'border-neutral-300 dark:border-neutral-600'
		}
	};

	// Priority configuration
	const priorityConfig: Record<string, { label: string; color: string; bg: string }> = {
		high: { label: 'High', color: 'text-error-600 dark:text-error-400', bg: 'bg-error-100 dark:bg-error-900/30' },
		medium: { label: 'Medium', color: 'text-warning-600 dark:text-warning-400', bg: 'bg-warning-100 dark:bg-warning-900/30' },
		low: { label: 'Low', color: 'text-neutral-600 dark:text-neutral-400', bg: 'bg-neutral-100 dark:bg-neutral-800' }
	};

	// Category configuration
	const categoryConfig: Record<string, { label: string; color: string }> = {
		implementation: { label: 'Implementation', color: 'text-brand-600 dark:text-brand-400' },
		research: { label: 'Research', color: 'text-purple-600 dark:text-purple-400' },
		decision: { label: 'Decision', color: 'text-amber-600 dark:text-amber-400' },
		communication: { label: 'Communication', color: 'text-teal-600 dark:text-teal-400' }
	};

	// Helper functions with fallbacks
	function getPriorityConfig(priority: string) {
		const key = priority?.toLowerCase() || 'medium';
		return priorityConfig[key] || priorityConfig.medium;
	}

	function getCategoryConfig(category: string) {
		const key = category?.toLowerCase() || 'implementation';
		return categoryConfig[key] || categoryConfig.implementation;
	}

	async function loadAction() {
		try {
			isLoading = true;
			error = null;
			action = await apiClient.getActionDetail(actionId);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load action';
		} finally {
			isLoading = false;
		}
	}

	async function updateStatus(newStatus: ActionStatus) {
		if (!action || action.status === newStatus || isUpdatingStatus) return;

		try {
			isUpdatingStatus = true;
			await apiClient.updateTaskStatus(action.session_id, actionId, newStatus);
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
		if (action) {
			goto(`/meeting/${action.session_id}`);
		}
	}

	// Load activity updates
	async function loadUpdates() {
		try {
			updatesLoading = true;
			updatesError = null;
			const response = await apiClient.getActionUpdates(actionId);
			updates = response.updates;
		} catch (err) {
			updatesError = err instanceof Error ? err.message : 'Failed to load updates';
		} finally {
			updatesLoading = false;
		}
	}

	// Add a new update
	async function handleAddUpdate(update: ActionUpdateCreateRequest) {
		const created = await apiClient.addActionUpdate(actionId, update);
		// Add to the beginning of the list (most recent first)
		updates = [created, ...updates];
	}

	onMount(() => {
		loadAction();
		loadUpdates();
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
								{:else if action.status === 'in_progress'}
									<Clock class="w-4 h-4" />
								{:else if action.status === 'blocked'}
									<AlertTriangle class="w-4 h-4" />
								{:else if action.status === 'in_review'}
									<Clock class="w-4 h-4" />
								{:else if action.status === 'done'}
									<CheckCircle2 class="w-4 h-4" />
								{:else}
									<XCircle class="w-4 h-4" />
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
							{#if action.status !== 'in_progress'}
								<Button
									variant="ghost"
									size="sm"
									onclick={() => updateStatus('in_progress')}
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
							<span class={`text-sm font-medium px-2 py-0.5 rounded ${getPriorityConfig(action.priority).bg} ${getPriorityConfig(action.priority).color}`}>
								{getPriorityConfig(action.priority).label}
							</span>
						</div>

						<!-- Category -->
						<div class="flex items-center gap-2">
							<Layers class="w-4 h-4 text-neutral-400" />
							<span class={`text-sm font-medium ${getCategoryConfig(action.category).color}`}>
								{getCategoryConfig(action.category).label}
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

				<!-- Dates & Schedule -->
				{#if hasAnyDates(action)}
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
						<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-4">
							<CalendarDays class="w-4 h-4 text-brand-500" />
							Schedule & Dates
						</h2>

						<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
							<!-- Duration -->
							{#if action.estimated_duration_days || action.timeline}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
									<Timer class="w-5 h-5 text-brand-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Duration</div>
										<div class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
											{#if action.timeline}
												{action.timeline}
											{:else if action.estimated_duration_days}
												{action.estimated_duration_days} business days
											{/if}
										</div>
									</div>
								</div>
							{/if}

							<!-- Target Start Date -->
							{#if action.target_start_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
									<Calendar class="w-5 h-5 text-amber-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Target Start</div>
										<div class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
											{formatDate(action.target_start_date)}
										</div>
									</div>
								</div>
							{/if}

							<!-- Target End Date -->
							{#if action.target_end_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
									<Calendar class="w-5 h-5 text-amber-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Target End</div>
										<div class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
											{formatDate(action.target_end_date)}
										</div>
									</div>
								</div>
							{/if}

							<!-- Estimated Start Date (calculated) -->
							{#if action.estimated_start_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-brand-50 dark:bg-brand-900/20">
									<CalendarDays class="w-5 h-5 text-brand-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-brand-600 dark:text-brand-400 uppercase">Est. Start</div>
										<div class="text-sm font-medium text-brand-900 dark:text-brand-100">
											{formatDate(action.estimated_start_date)}
										</div>
									</div>
								</div>
							{/if}

							<!-- Estimated End Date (calculated) -->
							{#if action.estimated_end_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-brand-50 dark:bg-brand-900/20">
									<CalendarDays class="w-5 h-5 text-brand-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-brand-600 dark:text-brand-400 uppercase">Est. End</div>
										<div class="text-sm font-medium text-brand-900 dark:text-brand-100">
											{formatDate(action.estimated_end_date)}
										</div>
									</div>
								</div>
							{/if}

							<!-- Actual Start Date -->
							{#if action.actual_start_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-success-50 dark:bg-success-900/20">
									<CalendarCheck class="w-5 h-5 text-success-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-success-600 dark:text-success-400 uppercase">Started</div>
										<div class="text-sm font-medium text-success-900 dark:text-success-100">
											{formatDate(action.actual_start_date)}
										</div>
									</div>
								</div>
							{/if}

							<!-- Actual End Date -->
							{#if action.actual_end_date}
								<div class="flex items-start gap-3 p-3 rounded-lg bg-success-50 dark:bg-success-900/20">
									<CalendarCheck class="w-5 h-5 text-success-500 mt-0.5" />
									<div>
										<div class="text-xs font-medium text-success-600 dark:text-success-400 uppercase">Completed</div>
										<div class="text-sm font-medium text-success-900 dark:text-success-100">
											{formatDate(action.actual_end_date)}
										</div>
									</div>
								</div>
							{/if}
						</div>

						<!-- Blocking info if blocked -->
						{#if action.status === 'blocked' && action.blocking_reason}
							<div class="mt-4 p-3 rounded-lg bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800">
								<div class="flex items-start gap-2">
									<AlertTriangle class="w-4 h-4 text-error-500 mt-0.5 flex-shrink-0" />
									<div class="flex-1">
										<div class="text-xs font-medium text-error-600 dark:text-error-400 uppercase">Blocked</div>
										<div class="text-sm text-error-700 dark:text-error-300">{action.blocking_reason}</div>
										{#if action.blocked_at}
											<div class="text-xs text-error-500 dark:text-error-400 mt-1">
												Since {formatDate(action.blocked_at)}
											</div>
										{/if}

										<!-- Replan options -->
										<div class="mt-3 pt-3 border-t border-error-200 dark:border-error-700">
											{#if action.replan_session_id}
												<!-- Existing replan session -->
												<div class="flex items-center justify-between">
													<div>
														<span class="text-xs text-error-600 dark:text-error-400">Replanning in progress</span>
														{#if action.replan_requested_at}
															<span class="text-xs text-error-500 dark:text-error-500 ml-2">
																Started {formatDate(action.replan_requested_at)}
															</span>
														{/if}
													</div>
													<a
														href="/meeting/{action.replan_session_id}"
														class="inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300"
													>
														<ExternalLink class="w-3.5 h-3.5" />
														View Meeting
													</a>
												</div>
											{:else if action.can_replan}
												<!-- Request replan button -->
												<button
													onclick={openReplanModal}
													class="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-brand-700 dark:text-brand-300 bg-brand-50 dark:bg-brand-900/30 hover:bg-brand-100 dark:hover:bg-brand-900/50 rounded-lg transition-colors"
												>
													<Sparkles class="w-4 h-4" />
													Request AI Replanning
												</button>
												<p class="text-xs text-error-500 dark:text-error-400 mt-1.5">
													Get AI assistance to find an alternative approach for this blocked action
												</p>
											{/if}
										</div>
									</div>
								</div>
							</div>
						{/if}
					</div>
				{/if}

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

				<!-- Activity Timeline -->
				<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
					<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-4">
						<History class="w-4 h-4 text-brand-500" />
						Activity
					</h2>

					<!-- Add Update Form -->
					<div class="mb-6 pb-6 border-b border-neutral-200 dark:border-neutral-700">
						<UpdateInput onSubmit={handleAddUpdate} disabled={action.status === 'done' || action.status === 'cancelled'} />
					</div>

					<!-- Activity Timeline -->
					<ActivityTimeline {updates} loading={updatesLoading} />

					{#if updatesError}
						<p class="text-sm text-error-600 dark:text-error-400 mt-2">{updatesError}</p>
					{/if}
				</div>

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

<!-- Replan Modal -->
{#if showReplanModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center">
		<!-- Backdrop -->
		<button
			type="button"
			class="absolute inset-0 bg-black/50 backdrop-blur-sm"
			onclick={closeReplanModal}
			aria-label="Close modal"
		></button>

		<!-- Modal Content -->
		<div class="relative bg-white dark:bg-neutral-900 rounded-xl shadow-xl max-w-lg w-full mx-4 overflow-hidden">
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3">
					<div class="p-2 rounded-lg bg-brand-50 dark:bg-brand-900/30">
						<Sparkles class="w-5 h-5 text-brand-600 dark:text-brand-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Request AI Replanning</h3>
						<p class="text-sm text-neutral-500 dark:text-neutral-400">Get help finding an alternative approach</p>
					</div>
				</div>
				<button
					onclick={closeReplanModal}
					class="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
					aria-label="Close"
				>
					<X class="w-5 h-5 text-neutral-500" />
				</button>
			</div>

			<!-- Body -->
			<div class="px-6 py-4">
				{#if action}
					<div class="mb-4 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
						<div class="text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-1">{action.title}</div>
						{#if action.blocking_reason}
							<div class="text-xs text-error-600 dark:text-error-400">
								<span class="font-medium">Blocked:</span> {action.blocking_reason}
							</div>
						{/if}
					</div>
				{/if}

				<label class="block">
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5 block">
						Additional Context (Optional)
					</span>
					<textarea
						bind:value={replanContext}
						placeholder="Provide any additional context that might help find an alternative approach..."
						rows="4"
						class="w-full px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
					></textarea>
					<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1.5">
						This will start a new meeting with AI experts to discuss alternatives for this blocked action.
					</p>
				</label>

				{#if replanError}
					<div class="mt-4 p-3 rounded-lg bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800">
						<p class="text-sm text-error-700 dark:text-error-300">{replanError}</p>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-end gap-3 px-6 py-4 bg-neutral-50 dark:bg-neutral-800/50">
				<Button variant="ghost" onclick={closeReplanModal} disabled={isRequestingReplan}>
					Cancel
				</Button>
				<Button variant="brand" onclick={submitReplanRequest} disabled={isRequestingReplan}>
					{#if isRequestingReplan}
						<Loader2 class="w-4 h-4 mr-2 animate-spin" />
						Creating Meeting...
					{:else}
						<Sparkles class="w-4 h-4 mr-2" />
						Start Replanning Meeting
					{/if}
				</Button>
			</div>
		</div>
	</div>
{/if}
