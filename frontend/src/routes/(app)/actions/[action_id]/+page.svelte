<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { ActionDetailExtended, ActionUpdateResponse, ActionUpdateCreate, DependencyListResponse } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';
	import RatingPrompt from '$lib/components/ui/RatingPrompt.svelte';
	import ActivityTimeline from '$lib/components/actions/ActivityTimeline.svelte';
	import UpdateInput from '$lib/components/actions/UpdateInput.svelte';
	import CancellationModal from '$lib/components/actions/CancellationModal.svelte';
	import ReplanningSuggestionModal from '$lib/components/actions/ReplanningSuggestionModal.svelte';
	import DependencyGraph from '$lib/components/actions/DependencyGraph.svelte';
	import ReminderSettings from '$lib/components/actions/ReminderSettings.svelte';
	import ProjectSelector from '$lib/components/actions/ProjectSelector.svelte';
	import UnblockSuggestions from '$lib/components/actions/UnblockSuggestions.svelte';
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
		X,
		FolderKanban,
		Trophy,
		HelpCircle,
		MessageCircle,
		Lightbulb,
		ThumbsUp,
		Users
	} from 'lucide-svelte';
	import { getDueDateStatus, getDueDateLabel, getDueDateBadgeClasses, getEffectiveDueDate } from '$lib/utils/due-dates';
	import ActionSocialShare from '$lib/components/actions/ActionSocialShare.svelte';
	import type { ActionAchievementData } from '$lib/utils/canvas-export';

	// Helper function to format dates nicely

	// Check if action has any date information
	function hasAnyDates(action: ActionDetailExtended): boolean {
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

	let action = $state<ActionDetailExtended | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let isUpdatingStatus = $state(false);

	// Activity updates state
	let updates = $state<ActionUpdateResponse[]>([]);
	let updatesLoading = $state(false);
	let updatesError = $state<string | null>(null);

	// Dependency data state
	let dependencyData = $state<DependencyListResponse | null>(null);
	let dependencyLoading = $state(false);
	let dependencyError = $state<string | null>(null);

	// Replanning state
	let showReplanModal = $state(false);
	let replanContext = $state('');
	let isRequestingReplan = $state(false);
	let replanError = $state<string | null>(null);

	// Cancellation state
	let showCancellationModal = $state(false);
	let isCancelling = $state(false);
	let cancellationError = $state<string | null>(null);

	// Close action state (failed/abandoned)
	let showCloseModal = $state(false);
	let closeStatus = $state<'failed' | 'abandoned'>('failed');
	let closeReason = $state('');
	let isClosing = $state(false);
	let closeError = $state<string | null>(null);

	// Clone-replan state
	let isCloneReplanning = $state(false);
	let cloneReplanError = $state<string | null>(null);

	// Replanning suggestion state
	let showReplanningSuggestionModal = $state(false);
	let isCreatingReplanMeeting = $state(false);
	let replanningSuggestionError = $state<string | null>(null);
	let replanSuggestionContext = $state<any>(null);

	// Escalate blocker state
	let isEscalating = $state(false);
	let escalateError = $state<string | null>(null);

	// Post-mortem completion state
	let showCompletionModal = $state(false);
	let completionWentWell = $state('');
	let completionLessonsLearned = $state('');
	let isCompletingWithPostMortem = $state(false);
	let completionError = $state<string | null>(null);

	// Derive achievement data for social sharing (completed actions only)
	const achievementData = $derived.by((): ActionAchievementData | null => {
		if (!action || action.status !== 'done') return null;

		// Calculate days to complete
		let daysToComplete: number | undefined;
		if (action.actual_start_date && action.actual_end_date) {
			const start = new Date(action.actual_start_date);
			const end = new Date(action.actual_end_date);
			daysToComplete = Math.max(1, Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)));
		}

		return {
			title: action.title,
			completionDate: action.actual_end_date || new Date().toISOString(),
			daysToComplete,
			projectName: undefined, // Could be fetched from project if needed
			priority: action.priority as 'high' | 'medium' | 'low'
		};
	});

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

	import { formatDate } from '$lib/utils/time-formatting';
	// Open cancellation modal (instead of directly cancelling)
	function openCancellationModal() {
		showCancellationModal = true;
		cancellationError = null;
	}

	// Close cancellation modal
	function closeCancellationModal() {
		showCancellationModal = false;
		cancellationError = null;
	}

	// Open replanning suggestion modal
	async function openReplanningSuggestionModal() {
		showReplanningSuggestionModal = true;
		replanningSuggestionError = null;
		// Fetch replan context from backend
		try {
			const response = await fetch(`/api/v1/actions/${actionId}/replan-context`);
			if (response.ok) {
				replanSuggestionContext = await response.json();
			}
		} catch (e) {
			console.error('Failed to fetch replan context:', e);
			// Continue with empty context
		}
	}

	// Close replanning suggestion modal
	function closeReplanningSuggestionModal() {
		showReplanningSuggestionModal = false;
		replanSuggestionContext = null;
		replanningSuggestionError = null;
	}

	// Escalate blocker to meeting
	async function escalateBlocker() {
		if (!action) return;

		isEscalating = true;
		escalateError = null;

		try {
			const result = await apiClient.escalateBlocker(action.id);
			// Navigate to the new meeting
			goto(result.redirect_url);
		} catch (e: any) {
			escalateError = e.message || 'Failed to escalate blocker';
			isEscalating = false;
		}
	}

	// Submit replanning suggestion - create new meeting
	async function submitReplanningSuggestion(problemStatement: string) {
		if (!action) return;

		isCreatingReplanMeeting = true;
		replanningSuggestionError = null;

		try {
			const response = await fetch('/api/v1/sessions', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					problem_statement: problemStatement
				})
			});

			if (!response.ok) {
				throw new Error('Failed to create meeting');
			}

			const session = await response.json();

			// Link the new session to this action
			await fetch(`/api/v1/actions/${action.id}/status`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					status: action.status,
					replan_session_created_id: session.id
				})
			});

			// Navigate to new meeting
			goto(`/meeting/${session.id}`);
		} catch (e) {
			console.error('Failed to create replanning meeting:', e);
			replanningSuggestionError = e instanceof Error ? e.message : 'Failed to create meeting';
		} finally {
			isCreatingReplanMeeting = false;
		}
	}

	// Submit cancellation with reason
	async function submitCancellation(reason: string, _category: string) {
		if (!action) return;

		isCancelling = true;
		cancellationError = null;

		try {
			await apiClient.updateActionStatus(action.id, 'cancelled', {
				cancellationReason: reason
			});
			action = {
				...action,
				status: 'cancelled',
				cancellation_reason: reason,
				cancelled_at: new Date().toISOString(),
				replan_requested_at: new Date().toISOString()
			};
			showCancellationModal = false;
		} catch (e) {
			console.error('Failed to cancel action:', e);
			cancellationError = e instanceof Error ? e.message : 'Failed to cancel action';
		} finally {
			isCancelling = false;
		}
	}

	// Open close modal
	function openCloseModal(status: 'failed' | 'abandoned') {
		closeStatus = status;
		closeReason = '';
		closeError = null;
		showCloseModal = true;
	}

	// Close the close modal
	function closeCloseModal() {
		showCloseModal = false;
		closeReason = '';
		closeError = null;
	}

	// Submit close action (failed/abandoned)
	async function submitClose() {
		if (!action || !closeReason.trim()) return;

		isClosing = true;
		closeError = null;

		try {
			await apiClient.closeAction(action.id, closeStatus, closeReason.trim());
			action = {
				...action,
				status: closeStatus,
				closure_reason: closeReason.trim(),
				cancelled_at: new Date().toISOString()
			};
			showCloseModal = false;
		} catch (e) {
			console.error('Failed to close action:', e);
			closeError = e instanceof Error ? e.message : 'Failed to close action';
		} finally {
			isClosing = false;
		}
	}

	// Clone-replan action
	async function handleCloneReplan() {
		if (!action) return;

		isCloneReplanning = true;
		cloneReplanError = null;

		try {
			const result = await apiClient.cloneReplanAction(action.id);
			// Navigate to the new action
			goto(`/actions/${result.new_action_id}`);
		} catch (e) {
			console.error('Failed to replan action:', e);
			cloneReplanError = e instanceof Error ? e.message : 'Failed to replan action';
		} finally {
			isCloneReplanning = false;
		}
	}

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
		},
		failed: {
			label: 'Failed',
			icon: XCircle,
			bgColor: 'bg-error-50 dark:bg-error-900/20',
			textColor: 'text-error-600 dark:text-error-400',
			borderColor: 'border-error-300 dark:border-error-700'
		},
		abandoned: {
			label: 'Abandoned',
			icon: XCircle,
			bgColor: 'bg-neutral-100 dark:bg-neutral-800',
			textColor: 'text-neutral-500 dark:text-neutral-400',
			borderColor: 'border-neutral-400 dark:border-neutral-600'
		},
		replanned: {
			label: 'Replanned',
			icon: Sparkles,
			bgColor: 'bg-brand-50 dark:bg-brand-900/20',
			textColor: 'text-brand-600 dark:text-brand-400',
			borderColor: 'border-brand-300 dark:border-brand-700'
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
		decision: { label: 'Decision', color: 'text-warning-600 dark:text-warning-400' },
		communication: { label: 'Communication', color: 'text-teal-600 dark:text-teal-400' }
	};

	// Build advisor help URL for a specific step
	function getMentorHelpUrl(stepNumber: number, stepText: string): string {
		const message = `@action:${actionId} Help me with step ${stepNumber}: "${stepText}"`;
		const params = new URLSearchParams({
			message,
			persona: 'action_coach'
		});
		return `/advisor/discuss?${params.toString()}`;
	}

	// Build advisor URL for general action help
	function getActionMentorUrl(): string {
		const params = new URLSearchParams({
			message: `Help me with @action:${actionId}`,
			persona: 'task_master'
		});
		return `/advisor/discuss?${params.toString()}`;
	}

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

	// Open completion modal for post-mortem capture
	function openCompletionModal() {
		completionWentWell = '';
		completionLessonsLearned = '';
		completionError = null;
		showCompletionModal = true;
	}

	// Close completion modal
	function closeCompletionModal() {
		showCompletionModal = false;
		completionWentWell = '';
		completionLessonsLearned = '';
		completionError = null;
	}

	// Complete action with optional post-mortem
	async function completeWithPostMortem(skipPostMortem: boolean = false) {
		if (!action) return;

		isCompletingWithPostMortem = true;
		completionError = null;

		try {
			const postMortem = skipPostMortem
				? undefined
				: {
						lessonsLearned: completionLessonsLearned.trim() || undefined,
						wentWell: completionWentWell.trim() || undefined
					};

			await apiClient.completeAction(actionId, postMortem);
			action = {
				...action,
				status: 'done',
				lessons_learned: postMortem?.lessonsLearned || null,
				went_well: postMortem?.wentWell || null
			};
			showCompletionModal = false;
		} catch (err) {
			completionError = err instanceof Error ? err.message : 'Failed to complete action';
		} finally {
			isCompletingWithPostMortem = false;
		}
	}

	async function updateStatus(newStatus: ActionStatus) {
		if (!action || action.status === newStatus || isUpdatingStatus) return;

		try {
			isUpdatingStatus = true;
			// Use dedicated action status endpoints
			if (newStatus === 'in_progress' && action.status === 'todo') {
				await apiClient.startAction(actionId);
			} else if (newStatus === 'done') {
				// Show completion modal for post-mortem capture
				openCompletionModal();
				isUpdatingStatus = false;
				return;
			} else {
				await apiClient.updateActionStatus(actionId, newStatus);
			}
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

	// Handle project assignment change
	function handleProjectChange(projectId: string | null, _projectName: string | null) {
		if (action) {
			action = { ...action, project_id: projectId };
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

	// Load action dependencies
	async function loadDependencies() {
		try {
			dependencyLoading = true;
			dependencyError = null;
			dependencyData = await apiClient.getActionDependencies(actionId);
		} catch (err) {
			dependencyError = err instanceof Error ? err.message : 'Failed to load dependencies';
		} finally {
			dependencyLoading = false;
		}
	}

	// Add a new update
	async function handleAddUpdate(update: ActionUpdateCreate) {
		const created = await apiClient.addActionUpdate(actionId, update);
		// Add to the beginning of the list (most recent first)
		updates = [created, ...updates];
	}

	onMount(() => {
		loadAction();
		loadUpdates();
		loadDependencies();
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
					aria-label="Back to actions list"
				>
					<ArrowLeft class="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
				</button>
				<div class="flex-1 min-w-0 flex items-center gap-3">
					<h1 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 truncate">
						{#if isLoading}
							<span class="animate-pulse bg-neutral-200 dark:bg-neutral-700 rounded h-6 w-48 inline-block"></span>
						{:else if action}
							{action.title}
						{:else}
							Action Not Found
						{/if}
					</h1>
					{#if action?.session_id}
						<a
							href="/meeting/{action.session_id}"
							class="flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 bg-brand-50 dark:bg-brand-900/20 hover:bg-brand-100 dark:hover:bg-brand-900/30 rounded-lg transition-colors"
						>
							<ExternalLink class="w-4 h-4" />
							<span class="hidden sm:inline">Back to Meeting</span>
							<span class="sm:hidden">Meeting</span>
						</a>
					{/if}
					{#if action}
						<a
							href={getActionMentorUrl()}
							class="flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-lg transition-colors"
							aria-label="Ask mentor for help with this action"
						>
							<MessageCircle class="w-4 h-4" />
							<span class="hidden sm:inline">Ask Mentor</span>
							<span class="sm:hidden">Help</span>
						</a>
					{/if}
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
								{:else if action.status === 'replanned'}
									<Sparkles class="w-4 h-4" />
								{:else}
									<XCircle class="w-4 h-4" />
								{/if}
								<span class="text-sm font-medium">{statusConfig[action.status].label}</span>
							</div>
						</div>

						<!-- Status Change Buttons -->
						<div class="flex items-center gap-2">
							{#if !['done', 'cancelled', 'failed', 'abandoned', 'replanned'].includes(action.status)}
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
								<Button
									variant="brand"
									size="sm"
									onclick={() => updateStatus('done')}
									disabled={isUpdatingStatus}
								>
									<CheckCircle2 class="w-4 h-4 mr-1" />
									Complete
								</Button>
								<Button
									variant="ghost"
									size="sm"
									onclick={() => openCloseModal('failed')}
									disabled={isUpdatingStatus}
									class="text-error-600 dark:text-error-400 hover:bg-error-50 dark:hover:bg-error-900/20"
								>
									<XCircle class="w-4 h-4 mr-1" />
									Mark Failed
								</Button>
								<Button
									variant="ghost"
									size="sm"
									onclick={() => openCloseModal('abandoned')}
									disabled={isUpdatingStatus}
								>
									<XCircle class="w-4 h-4 mr-1" />
									Abandon
								</Button>
							{/if}

							{#if ['failed', 'abandoned'].includes(action.status)}
								<Button
									variant="brand"
									size="sm"
									onclick={handleCloneReplan}
									disabled={isCloneReplanning}
								>
									{#if isCloneReplanning}
										<Loader2 class="w-4 h-4 mr-1 animate-spin" />
									{:else}
										<Sparkles class="w-4 h-4 mr-1" />
									{/if}
									Replan Action
								</Button>
							{/if}

							<!-- Share Achievement (completed actions only) -->
							{#if achievementData}
								<ActionSocialShare achievement={achievementData} />
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

						<!-- Project -->
						<div class="flex items-center gap-2">
							<FolderKanban class="w-4 h-4 text-neutral-400" />
							<ProjectSelector
								actionId={action.id}
								currentProjectId={action.project_id}
								onchange={handleProjectChange}
							/>
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
					{@const effectiveDueDate = getEffectiveDueDate(action)}
					{@const dueDateStatus = getDueDateStatus(effectiveDueDate)}
					{@const hasTargetDates = action.target_start_date || action.target_end_date}
					{@const hasEstimatedDates = action.estimated_start_date || action.estimated_end_date}
					{@const hasActualDates = action.actual_start_date || action.actual_end_date}
					{@const startVariance = action.actual_start_date && action.target_start_date
						? Math.round((new Date(action.actual_start_date).getTime() - new Date(action.target_start_date).getTime()) / (1000 * 60 * 60 * 24))
						: null}
					{@const endVariance = action.actual_end_date && action.target_end_date
						? Math.round((new Date(action.actual_end_date).getTime() - new Date(action.target_end_date).getTime()) / (1000 * 60 * 60 * 24))
						: null}
					{@const daysRemaining = effectiveDueDate && action.status !== 'done' && action.status !== 'cancelled'
						? Math.ceil((new Date(effectiveDueDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
						: null}
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
						<!-- Header with status badge -->
						<div class="flex items-center justify-between mb-4">
							<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider">
								<CalendarDays class="w-4 h-4 text-brand-500" />
								Schedule
							</h2>
							<div class="flex items-center gap-2">
								{#if daysRemaining !== null}
									<span class={`text-sm font-medium ${daysRemaining < 0 ? 'text-error-600 dark:text-error-400' : daysRemaining <= 3 ? 'text-warning-600 dark:text-warning-400' : 'text-neutral-600 dark:text-neutral-400'}`}>
										{#if daysRemaining < 0}
											{Math.abs(daysRemaining)} days overdue
										{:else if daysRemaining === 0}
											Due today
										{:else}
											{daysRemaining} days left
										{/if}
									</span>
								{/if}
								{#if dueDateStatus === 'overdue' || dueDateStatus === 'due-soon'}
									<span class={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full border ${getDueDateBadgeClasses(dueDateStatus)}`}>
										{#if dueDateStatus === 'overdue'}
											<AlertTriangle class="w-3 h-3" />
										{:else}
											<Clock class="w-3 h-3" />
										{/if}
										{getDueDateLabel(dueDateStatus)}
									</span>
								{/if}
							</div>
						</div>

						<!-- Visual Timeline Progress -->
						{#if action}
							{@const progressSteps = [
								{ label: 'Start', done: !!action.actual_start_date, date: action.actual_start_date || action.estimated_start_date || action.target_start_date },
								{ label: 'In Progress', done: action.status === 'in_progress' || action.status === 'done', active: action.status === 'in_progress' },
								{ label: 'Complete', done: action.status === 'done', date: action.actual_end_date }
							]}
						<div class="mb-5 px-2">
							<div class="relative flex items-center justify-between">
								<!-- Progress line background -->
								<div class="absolute left-0 right-0 top-1/2 -tranneutral-y-1/2 h-1 bg-neutral-200 dark:bg-neutral-700 rounded-full"></div>
								<!-- Progress line fill -->
								<div
									class={`absolute left-0 top-1/2 -tranneutral-y-1/2 h-1 rounded-full transition-all ${action.status === 'done' ? 'bg-success-500' : action.status === 'cancelled' ? 'bg-neutral-400' : 'bg-brand-500'}`}
									style="width: {action.status === 'done' ? '100%' : action.status === 'in_progress' ? '50%' : action.actual_start_date ? '25%' : '0%'}"
								></div>
								<!-- Steps -->
								{#each progressSteps as step, i}
									<div class="relative flex flex-col items-center z-10">
										<div class={`w-4 h-4 rounded-full border-2 ${
											step.done
												? 'bg-success-500 border-success-500'
												: step.active
													? 'bg-brand-500 border-brand-500 ring-4 ring-brand-100 dark:ring-brand-900/50'
													: 'bg-white dark:bg-neutral-900 border-neutral-300 dark:border-neutral-600'
										}`}>
											{#if step.done}
												<CheckCircle2 class="w-3 h-3 text-white -mt-px -ml-px" />
											{/if}
										</div>
										<span class={`mt-1.5 text-xs font-medium ${step.done || step.active ? 'text-neutral-900 dark:text-neutral-100' : 'text-neutral-400 dark:text-neutral-500'}`}>
											{step.label}
										</span>
									</div>
								{/each}
							</div>
						</div>
						{/if}

						<!-- Duration Summary -->
						{#if action.estimated_duration_days}
							<div class="flex items-center gap-2 mb-4 px-3 py-2 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
								<Timer class="w-4 h-4 text-brand-500" />
								<span class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
									{action.estimated_duration_days} business days
								</span>
							</div>
						{/if}

						<!-- Compact Date Rows -->
						<div class="space-y-2">
							<!-- Target Dates Row -->
							{#if hasTargetDates}
								<div class="flex items-center gap-3 px-3 py-2 rounded-lg bg-warning-50/50 dark:bg-warning-900/10 border border-warning-200/50 dark:border-warning-800/30">
									<Calendar class="w-4 h-4 text-warning-600 dark:text-warning-400 flex-shrink-0" />
									<span class="text-xs font-medium text-warning-700 dark:text-warning-300 uppercase w-16">Target</span>
									<div class="flex-1 flex items-center gap-4 text-sm">
										{#if action.target_start_date}
											<span class="text-neutral-700 dark:text-neutral-300">{formatDate(action.target_start_date)}</span>
										{/if}
										{#if action.target_start_date && action.target_end_date}
											<span class="text-neutral-400">→</span>
										{/if}
										{#if action.target_end_date}
											<span class="text-neutral-700 dark:text-neutral-300">{formatDate(action.target_end_date)}</span>
										{/if}
									</div>
								</div>
							{/if}

							<!-- Estimated Dates Row (only if different from target) -->
							{#if hasEstimatedDates && (action.estimated_start_date !== action.target_start_date || action.estimated_end_date !== action.target_end_date)}
								<div class="flex items-center gap-3 px-3 py-2 rounded-lg bg-brand-50/50 dark:bg-brand-900/10 border border-brand-200/50 dark:border-brand-800/30">
									<CalendarDays class="w-4 h-4 text-brand-600 dark:text-brand-400 flex-shrink-0" />
									<span class="text-xs font-medium text-brand-700 dark:text-brand-300 uppercase w-16">Est.</span>
									<div class="flex-1 flex items-center gap-4 text-sm">
										{#if action.estimated_start_date}
											<span class="text-neutral-700 dark:text-neutral-300">{formatDate(action.estimated_start_date)}</span>
										{/if}
										{#if action.estimated_start_date && action.estimated_end_date}
											<span class="text-neutral-400">→</span>
										{/if}
										{#if action.estimated_end_date}
											<span class="text-neutral-700 dark:text-neutral-300">{formatDate(action.estimated_end_date)}</span>
										{/if}
									</div>
								</div>
							{/if}

							<!-- Actual Dates Row -->
							{#if hasActualDates}
								<div class="flex items-center gap-3 px-3 py-2 rounded-lg bg-success-50/50 dark:bg-success-900/10 border border-success-200/50 dark:border-success-800/30">
									<CalendarCheck class="w-4 h-4 text-success-600 dark:text-success-400 flex-shrink-0" />
									<span class="text-xs font-medium text-success-700 dark:text-success-300 uppercase w-16">Actual</span>
									<div class="flex-1 flex items-center gap-4 text-sm">
										{#if action.actual_start_date}
											<span class="text-neutral-700 dark:text-neutral-300">
												{formatDate(action.actual_start_date)}
												{#if startVariance !== null && Math.abs(startVariance) > 1}
													<span class={`ml-1 text-xs font-medium ${startVariance > 0 ? 'text-error-600 dark:text-error-400' : 'text-success-600 dark:text-success-400'}`}>
														({startVariance > 0 ? '+' : ''}{startVariance}d)
													</span>
												{/if}
											</span>
										{/if}
										{#if action.actual_start_date && action.actual_end_date}
											<span class="text-neutral-400">→</span>
										{/if}
										{#if action.actual_end_date}
											<span class="text-neutral-700 dark:text-neutral-300">
												{formatDate(action.actual_end_date)}
												{#if endVariance !== null && Math.abs(endVariance) > 1}
													<span class={`ml-1 text-xs font-medium ${endVariance > 0 ? 'text-error-600 dark:text-error-400' : 'text-success-600 dark:text-success-400'}`}>
														({endVariance > 0 ? '+' : ''}{endVariance}d)
													</span>
												{/if}
											</span>
										{/if}
									</div>
									{#if action.status === 'done'}
										<Trophy class="w-4 h-4 text-success-500" />
									{/if}
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

											<!-- AI-powered unblock suggestions -->
											<div class="mt-4">
												<UnblockSuggestions actionId={action.id} />
											</div>

											<!-- Escalate to meeting button -->
											<div class="mt-4 pt-4 border-t border-error-200 dark:border-error-800">
												<button
													onclick={escalateBlocker}
													disabled={isEscalating}
													class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
												>
													{#if isEscalating}
														<Loader2 class="w-4 h-4 animate-spin" />
														Starting meeting...
													{:else}
														<Users class="w-4 h-4" />
														Start Unblock Meeting
													{/if}
												</button>
												<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1.5">
													Get AI personas to deliberate on the best approach to unblock this action
												</p>
												{#if escalateError}
													<p class="text-xs text-error-500 dark:text-error-400 mt-1">{escalateError}</p>
												{/if}
											</div>
										</div>
									</div>
								</div>
							</div>
						{/if}

						<!-- Cancellation info if cancelled -->
						{#if action.status === 'cancelled' && action.cancellation_reason}
							<div class="mt-4 p-3 rounded-lg bg-neutral-100 dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700">
								<div class="flex items-start gap-2">
									<XCircle class="w-4 h-4 text-neutral-500 mt-0.5 flex-shrink-0" />
									<div class="flex-1">
										<div class="text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase">Cancelled</div>
										<div class="text-sm text-neutral-700 dark:text-neutral-300">{action.cancellation_reason}</div>
										{#if action.cancelled_at}
											<div class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
												On {formatDate(action.cancelled_at)}
											</div>
										{/if}

										<!-- Replanning suggestion -->
										<div class="mt-3 pt-3 border-t border-neutral-300 dark:border-neutral-600">
											<p class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
												Start a new deliberation to replan?
											</p>
											<Button
												size="sm"
												variant="secondary"
												onclick={openReplanningSuggestionModal}
												class="w-full"
											>
												Create Meeting to Replan
											</Button>
										</div>
									</div>
								</div>
							</div>
						{/if}

						<!-- Failed info -->
						{#if action.status === 'failed' && action.closure_reason}
							<div class="mt-4 p-3 rounded-lg bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800">
								<div class="flex items-start gap-2">
									<XCircle class="w-4 h-4 text-error-500 mt-0.5 flex-shrink-0" />
									<div class="flex-1">
										<div class="text-xs font-medium text-error-600 dark:text-error-400 uppercase">Failed</div>
										<div class="text-sm text-error-700 dark:text-error-300">{action.closure_reason}</div>
										{#if action.cancelled_at}
											<div class="text-xs text-error-500 dark:text-error-400 mt-1">
												On {formatDate(action.cancelled_at)}
											</div>
										{/if}

										<!-- Replan action -->
										<div class="mt-3 pt-3 border-t border-error-200 dark:border-error-700">
											<p class="text-sm text-error-600 dark:text-error-400 mb-2">
												Create a new action with a different approach
											</p>
											<Button
												size="sm"
												variant="brand"
												onclick={handleCloneReplan}
												disabled={isCloneReplanning}
												class="w-full"
											>
												{#if isCloneReplanning}
													<Loader2 class="w-4 h-4 mr-2 animate-spin" />
													Creating...
												{:else}
													<Sparkles class="w-4 h-4 mr-2" />
													Replan Action
												{/if}
											</Button>
										</div>
									</div>
								</div>
							</div>
						{/if}

						<!-- Abandoned info -->
						{#if action.status === 'abandoned' && action.closure_reason}
							<div class="mt-4 p-3 rounded-lg bg-neutral-100 dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700">
								<div class="flex items-start gap-2">
									<XCircle class="w-4 h-4 text-neutral-500 mt-0.5 flex-shrink-0" />
									<div class="flex-1">
										<div class="text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase">Abandoned</div>
										<div class="text-sm text-neutral-700 dark:text-neutral-300">{action.closure_reason}</div>
										{#if action.cancelled_at}
											<div class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
												On {formatDate(action.cancelled_at)}
											</div>
										{/if}

										<!-- Replan action -->
										<div class="mt-3 pt-3 border-t border-neutral-300 dark:border-neutral-600">
											<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
												Create a new action based on this one
											</p>
											<Button
												size="sm"
												variant="secondary"
												onclick={handleCloneReplan}
												disabled={isCloneReplanning}
												class="w-full"
											>
												{#if isCloneReplanning}
													<Loader2 class="w-4 h-4 mr-2 animate-spin" />
													Creating...
												{:else}
													<Sparkles class="w-4 h-4 mr-2" />
													Replan Action
												{/if}
											</Button>
										</div>
									</div>
								</div>
							</div>
						{/if}

						<!-- Replanned info -->
						{#if action.status === 'replanned' && action.replanned_to_id}
							<div class="mt-4 p-3 rounded-lg bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800">
								<div class="flex items-start gap-2">
									<Sparkles class="w-4 h-4 text-brand-500 mt-0.5 flex-shrink-0" />
									<div class="flex-1">
										<div class="text-xs font-medium text-brand-600 dark:text-brand-400 uppercase">Replanned</div>
										<div class="text-sm text-brand-700 dark:text-brand-300">
											This action was replaced with a new approach.
										</div>
										<a
											href="/actions/{action.replanned_to_id}"
											class="inline-flex items-center gap-1.5 mt-2 text-sm font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300"
										>
											<ExternalLink class="w-3.5 h-3.5" />
											View New Action
										</a>
									</div>
								</div>
							</div>
						{/if}

						<!-- Replanned from info -->
						{#if action.replanned_from_id}
							<div class="mt-4 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700">
								<div class="flex items-start gap-2">
									<History class="w-4 h-4 text-neutral-500 mt-0.5 flex-shrink-0" />
									<div class="flex-1">
										<div class="text-xs font-medium text-neutral-600 dark:text-neutral-400 uppercase">Replanned from</div>
										<a
											href="/actions/{action.replanned_from_id}"
											class="inline-flex items-center gap-1.5 mt-1 text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300"
										>
											<ExternalLink class="w-3.5 h-3.5" />
											View Original Action
										</a>
									</div>
								</div>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Reminder Settings (only for active actions) -->
				{#if !['done', 'cancelled', 'failed', 'abandoned', 'replanned'].includes(action.status)}
					<ReminderSettings actionId={action.id} />
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
				{#if (action.what_and_how?.length ?? 0) > 0}
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
						<h2 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-3">
							Steps to Complete
						</h2>
						<ul class="space-y-2">
							{#each action.what_and_how as step, i (i)}
								<li class="flex items-start gap-3 group">
									<span class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 text-sm font-medium flex items-center justify-center">
										{i + 1}
									</span>
									<span class="flex-1 text-neutral-700 dark:text-neutral-300 pt-0.5">{step}</span>
									<a
										href={getMentorHelpUrl(i + 1, step)}
										class="flex-shrink-0 flex items-center gap-1 px-2 py-1 text-xs font-medium text-neutral-500 hover:text-brand-600 dark:text-neutral-400 dark:hover:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded-md transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
										title="Get mentor help with this step"
									>
										<HelpCircle class="w-3.5 h-3.5" />
										<span class="hidden sm:inline">Help</span>
									</a>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Success Criteria -->
				{#if (action.success_criteria?.length ?? 0) > 0}
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
				{#if (action.kill_criteria?.length ?? 0) > 0}
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

				<!-- Post-Mortem (completed actions only) -->
				{#if action.status === 'done' && (action.went_well || action.lessons_learned)}
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
						<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-4">
							<Trophy class="w-4 h-4 text-success-500" />
							Reflections
						</h2>
						<div class="space-y-4">
							{#if action.went_well}
								<div class="p-4 rounded-lg bg-success-50/50 dark:bg-success-900/10 border border-success-200/50 dark:border-success-800/30">
									<div class="flex items-center gap-2 mb-2">
										<ThumbsUp class="w-4 h-4 text-success-600 dark:text-success-400" />
										<span class="text-sm font-medium text-success-700 dark:text-success-300">What went well</span>
									</div>
									<p class="text-sm text-success-800 dark:text-success-200 whitespace-pre-wrap">{action.went_well}</p>
								</div>
							{/if}
							{#if action.lessons_learned}
								<div class="p-4 rounded-lg bg-warning-50/50 dark:bg-warning-900/10 border border-warning-200/50 dark:border-warning-800/30">
									<div class="flex items-center gap-2 mb-2">
										<Lightbulb class="w-4 h-4 text-warning-600 dark:text-warning-400" />
										<span class="text-sm font-medium text-warning-700 dark:text-warning-300">Lessons learned</span>
									</div>
									<p class="text-sm text-warning-800 dark:text-warning-200 whitespace-pre-wrap">{action.lessons_learned}</p>
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<!-- Rating Prompt (completed actions only) -->
				{#if action.status === 'done'}
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
						<RatingPrompt
							entityType="action"
							entityId={actionId}
							prompt="Was this action helpful?"
						/>
					</div>
				{/if}

				<!-- Action Dependencies (structured) -->
				{#if dependencyData && dependencyData.dependencies.length > 0}
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
						<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-4">
							<Link2 class="w-4 h-4 text-brand-500" />
							Dependencies
						</h2>
						<DependencyGraph
							dependencies={dependencyData.dependencies}
							actionId={actionId}
							hasIncomplete={dependencyData.has_incomplete}
						/>
					</div>
				{:else if dependencyLoading}
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 shadow-sm border border-neutral-200 dark:border-neutral-800">
						<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wider mb-4">
							<Link2 class="w-4 h-4 text-brand-500" />
							Dependencies
						</h2>
						<div class="animate-pulse space-y-3">
							<div class="h-16 bg-neutral-100 dark:bg-neutral-800 rounded-lg"></div>
						</div>
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

<!-- Cancellation Modal -->
<CancellationModal
	bind:open={showCancellationModal}
	actionTitle={action?.title ?? ''}
	isSubmitting={isCancelling}
	error={cancellationError}
	oncancel={closeCancellationModal}
	onsubmit={submitCancellation}
/>

<!-- Close Action Modal (Failed/Abandoned) -->
{#if showCloseModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center">
		<!-- Backdrop -->
		<button
			type="button"
			class="absolute inset-0 bg-black/50 backdrop-blur-sm"
			onclick={closeCloseModal}
			aria-label="Close modal"
		></button>

		<!-- Modal Content -->
		<div class="relative bg-white dark:bg-neutral-900 rounded-xl shadow-xl max-w-lg w-full mx-4 overflow-hidden">
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3">
					<div class={`p-2 rounded-lg ${closeStatus === 'failed' ? 'bg-error-50 dark:bg-error-900/30' : 'bg-neutral-100 dark:bg-neutral-800'}`}>
						<XCircle class={`w-5 h-5 ${closeStatus === 'failed' ? 'text-error-600 dark:text-error-400' : 'text-neutral-600 dark:text-neutral-400'}`} />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
							{closeStatus === 'failed' ? 'Mark as Failed' : 'Abandon Action'}
						</h3>
						<p class="text-sm text-neutral-500 dark:text-neutral-400">
							{closeStatus === 'failed' ? 'This action could not be completed' : 'This action is no longer relevant'}
						</p>
					</div>
				</div>
				<button
					onclick={closeCloseModal}
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
						<div class="text-sm font-medium text-neutral-900 dark:text-neutral-100">{action.title}</div>
					</div>
				{/if}

				<label class="block">
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5 block">
						{closeStatus === 'failed' ? 'What prevented completion?' : 'Why is this being abandoned?'}
					</span>
					<textarea
						bind:value={closeReason}
						placeholder={closeStatus === 'failed'
							? 'Describe what blocked or prevented this action from being completed...'
							: 'Explain why this action is no longer needed or relevant...'}
						rows="4"
						class="w-full px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
					></textarea>
					<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1.5">
						After closing, you can create a new action from this one using "Replan Action".
					</p>
				</label>

				{#if closeError}
					<div class="mt-4 p-3 rounded-lg bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800">
						<p class="text-sm text-error-700 dark:text-error-300">{closeError}</p>
					</div>
				{/if}

				{#if cloneReplanError}
					<div class="mt-4 p-3 rounded-lg bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800">
						<p class="text-sm text-error-700 dark:text-error-300">{cloneReplanError}</p>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-end gap-3 px-6 py-4 bg-neutral-50 dark:bg-neutral-800/50">
				<Button variant="ghost" onclick={closeCloseModal} disabled={isClosing}>
					Cancel
				</Button>
				<Button
					variant={closeStatus === 'failed' ? 'danger' : 'secondary'}
					onclick={submitClose}
					disabled={isClosing || !closeReason.trim()}
				>
					{#if isClosing}
						<Loader2 class="w-4 h-4 mr-2 animate-spin" />
						Closing...
					{:else}
						<XCircle class="w-4 h-4 mr-2" />
						{closeStatus === 'failed' ? 'Mark as Failed' : 'Abandon Action'}
					{/if}
				</Button>
			</div>
		</div>
	</div>
{/if}

<!-- Replanning Suggestion Modal -->
<ReplanningSuggestionModal
	bind:open={showReplanningSuggestionModal}
	actionTitle={action?.title ?? ''}
	problemStatement={replanSuggestionContext?.problem_statement ?? ''}
	failureCategory={replanSuggestionContext?.failure_reason_category ?? 'unknown'}
	failureReason={replanSuggestionContext?.failure_reason_text ?? ''}
	relatedActions={replanSuggestionContext?.related_actions ?? []}
	isSubmitting={isCreatingReplanMeeting}
	error={replanningSuggestionError}
	oncancel={closeReplanningSuggestionModal}
	onsubmit={submitReplanningSuggestion}
/>

<!-- Completion Post-Mortem Modal -->
{#if showCompletionModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center">
		<!-- Backdrop -->
		<button
			type="button"
			class="absolute inset-0 bg-black/50 backdrop-blur-sm"
			onclick={closeCompletionModal}
			aria-label="Close modal"
		></button>

		<!-- Modal Content -->
		<div class="relative bg-white dark:bg-neutral-900 rounded-xl shadow-xl max-w-lg w-full mx-4 overflow-hidden">
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3">
					<div class="p-2 rounded-lg bg-success-50 dark:bg-success-900/30">
						<Trophy class="w-5 h-5 text-success-600 dark:text-success-400" />
					</div>
					<div>
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Complete Action</h3>
						<p class="text-sm text-neutral-500 dark:text-neutral-400">Capture your reflections (optional)</p>
					</div>
				</div>
				<button
					onclick={closeCompletionModal}
					class="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
					aria-label="Close"
				>
					<X class="w-5 h-5 text-neutral-500" />
				</button>
			</div>

			<!-- Body -->
			<div class="px-6 py-4 space-y-4">
				{#if action}
					<div class="p-3 rounded-lg bg-success-50/50 dark:bg-success-900/10 border border-success-200/50 dark:border-success-800/30">
						<div class="flex items-center gap-2">
							<CheckCircle2 class="w-4 h-4 text-success-600 dark:text-success-400" />
							<span class="text-sm font-medium text-success-900 dark:text-success-100">{action.title}</span>
						</div>
					</div>
				{/if}

				<label class="block">
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5 block">
						What went well?
					</span>
					<textarea
						bind:value={completionWentWell}
						placeholder="What aspects of this action worked particularly well? Any wins or positive outcomes..."
						rows="3"
						maxlength="500"
						class="w-full px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
					></textarea>
					<p class="text-xs text-neutral-400 dark:text-neutral-500 mt-1 text-right">{completionWentWell.length}/500</p>
				</label>

				<label class="block">
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5 block">
						Lessons learned?
					</span>
					<textarea
						bind:value={completionLessonsLearned}
						placeholder="What would you do differently next time? Any insights for future actions..."
						rows="3"
						maxlength="500"
						class="w-full px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
					></textarea>
					<p class="text-xs text-neutral-400 dark:text-neutral-500 mt-1 text-right">{completionLessonsLearned.length}/500</p>
				</label>

				{#if completionError}
					<div class="p-3 rounded-lg bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800">
						<p class="text-sm text-error-700 dark:text-error-300">{completionError}</p>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-between gap-3 px-6 py-4 bg-neutral-50 dark:bg-neutral-800/50">
				<Button
					variant="ghost"
					onclick={() => completeWithPostMortem(true)}
					disabled={isCompletingWithPostMortem}
				>
					Skip
				</Button>
				<div class="flex items-center gap-3">
					<Button variant="ghost" onclick={closeCompletionModal} disabled={isCompletingWithPostMortem}>
						Cancel
					</Button>
					<Button
						variant="brand"
						onclick={() => completeWithPostMortem(false)}
						disabled={isCompletingWithPostMortem}
					>
						{#if isCompletingWithPostMortem}
							<Loader2 class="w-4 h-4 mr-2 animate-spin" />
							Completing...
						{:else}
							<CheckCircle2 class="w-4 h-4 mr-2" />
							Complete Action
						{/if}
					</Button>
				</div>
			</div>
		</div>
	</div>
{/if}
