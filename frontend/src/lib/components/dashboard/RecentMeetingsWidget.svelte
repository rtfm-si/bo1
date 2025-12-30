<script lang="ts">
	/**
	 * Recent Meetings Widget - Dashboard widget showing last 5 meetings
	 *
	 * Displays meetings with status indicators, phase info, and quick actions.
	 * Different row styles for completed (green), active (blue pulse), and failed (amber with retry).
	 */

	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import type { SessionResponse } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';
	import { RotateCcw, Trash2 } from 'lucide-svelte';
	import { formatCompactRelativeTime } from '$lib/utils/time-formatting';
	import { toast } from '$lib/stores/toast';

	// Props
	interface Props {
		sessions: SessionResponse[];
		class?: string;
		onDelete?: () => void;
	}
	let { sessions, class: className = '', onDelete }: Props = $props();

	// State
	let retryingSessionIds = $state<Set<string>>(new Set());
	let deletingSessionId = $state<string | null>(null);

	// Limit to 5 most recent (already sorted by created_at desc from API)
	const recentSessions = $derived(sessions.slice(0, 5));

	// Total count for "View all" link
	const totalCount = $derived(sessions.length);

	/**
	 * Get status indicator styling based on session status
	 */
	function getStatusStyle(status: string): { bg: string; dot: string; text: string } {
		switch (status) {
			case 'completed':
				return {
					bg: 'bg-success-50 dark:bg-success-900/20',
					dot: 'bg-success-500',
					text: 'text-success-700 dark:text-success-300'
				};
			case 'active':
				return {
					bg: 'bg-brand-50 dark:bg-brand-900/20',
					dot: 'bg-brand-500 animate-pulse',
					text: 'text-brand-700 dark:text-brand-300'
				};
			case 'failed':
			case 'killed':
				return {
					bg: 'bg-amber-50 dark:bg-amber-900/20',
					dot: 'bg-amber-500',
					text: 'text-amber-700 dark:text-amber-300'
				};
			default:
				return {
					bg: 'bg-neutral-50 dark:bg-neutral-800',
					dot: 'bg-neutral-400',
					text: 'text-neutral-600 dark:text-neutral-400'
				};
		}
	}

	/**
	 * Humanize phase names for display
	 */
	function humanizePhase(phase: string | null | undefined, status: string): string {
		if (status === 'completed') return 'Completed';
		if (status === 'failed' || status === 'killed') return 'Failed';
		if (!phase) return 'Starting';

		const phaseMap: Record<string, string> = {
			decomposition: 'Analyzing',
			decompose: 'Analyzing',
			problem_decomposition: 'Analyzing',
			selection: 'Selecting Experts',
			exploration: 'Exploring',
			challenge: 'Deep Analysis',
			convergence: 'Converging',
			voting: 'Voting',
			synthesis: 'Synthesizing',
			meta_synthesis: 'Finalizing',
		};

		return phaseMap[phase.toLowerCase()] || phase.replace(/_/g, ' ');
	}

	/**
	 * Truncate problem statement for compact display
	 */
	function truncate(text: string, maxLength: number = 60): string {
		if (text.length <= maxLength) return text;
		return text.substring(0, maxLength) + '...';
	}

	/**
	 * Retry a failed session
	 */
	async function handleRetry(sessionId: string, event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();

		if (retryingSessionIds.has(sessionId)) return;

		retryingSessionIds = new Set([...retryingSessionIds, sessionId]);

		try {
			await apiClient.retrySession(sessionId);
			goto(`/meeting/${sessionId}`);
		} catch (error) {
			console.error('Failed to retry session:', error);
			toast.error('Failed to retry meeting');
			retryingSessionIds = new Set([...retryingSessionIds].filter(id => id !== sessionId));
		}
	}

	/**
	 * Delete a session
	 */
	async function handleDelete(sessionId: string, event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();

		if (!confirm('Are you sure you want to delete this meeting? This cannot be undone.')) {
			return;
		}

		deletingSessionId = sessionId;

		try {
			await apiClient.deleteSession(sessionId);
			toast.success('Meeting deleted');
			onDelete?.();
		} catch (error) {
			console.error('Failed to delete session:', error);
			toast.error('Failed to delete meeting');
		} finally {
			deletingSessionId = null;
		}
	}
</script>

<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 {className}">
	<!-- Header -->
	<div class="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
		<div class="flex items-center gap-2">
			<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
			</svg>
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Recent Meetings</h2>
			{#if totalCount > 0}
				<span class="px-2 py-0.5 text-xs font-medium bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 rounded-full">
					{totalCount}
				</span>
			{/if}
		</div>
		{#if totalCount > 5}
			<a
				href="/meeting"
				class="text-sm text-brand-600 dark:text-brand-400 hover:underline flex items-center gap-1"
			>
				View all
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
				</svg>
			</a>
		{/if}
	</div>

	<!-- Content -->
	{#if recentSessions.length === 0}
		<!-- Empty state -->
		<div class="px-4 py-8 text-center">
			<svg class="w-12 h-12 mx-auto text-neutral-300 dark:text-neutral-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
			</svg>
			<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-3">No meetings yet</p>
			<a href="/meeting/new">
				<Button variant="brand" size="sm">
					<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
					</svg>
					Start Your First Meeting
				</Button>
			</a>
		</div>
	{:else}
		<!-- Meetings list -->
		<div class="divide-y divide-neutral-200 dark:divide-neutral-700">
			{#each recentSessions as session (session.id)}
				{@const statusStyle = getStatusStyle(session.status)}
				{@const isFailed = session.status === 'failed' || session.status === 'killed'}
				{@const isActive = session.status === 'active'}

				<a
					href="/meeting/{session.id}"
					class="flex items-center gap-3 px-4 py-3 hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors group {isFailed ? 'bg-amber-50/50 dark:bg-amber-900/10' : ''}"
				>
					<!-- Status indicator -->
					<div class="flex-shrink-0">
						<span class="flex items-center justify-center w-3 h-3 rounded-full {statusStyle.dot}"></span>
					</div>

					<!-- Content -->
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 mb-0.5">
							<span class="font-medium text-sm text-neutral-900 dark:text-white truncate" title={session.problem_statement}>
								{truncate(session.problem_statement)}
							</span>
						</div>
						<div class="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
							<span class={statusStyle.text}>
								{humanizePhase(session.phase, session.status)}
							</span>
							<span>·</span>
							<span title={session.created_at}>
								{formatCompactRelativeTime(session.created_at)}
							</span>
							{#if session.expert_count && session.expert_count > 0}
								<span>·</span>
								<span>{session.expert_count} experts</span>
							{/if}
						</div>
					</div>

					<!-- Actions -->
					<div class="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
						{#if isFailed}
							<Button
								variant="brand"
								size="sm"
								onclick={(e) => handleRetry(session.id, e)}
								disabled={retryingSessionIds.has(session.id)}
							>
								{#if retryingSessionIds.has(session.id)}
									<span class="animate-spin mr-1">⏳</span>
									Retrying...
								{:else}
									<RotateCcw size={14} class="mr-1" />
									Retry
								{/if}
							</Button>
						{/if}

						<button
							onclick={(e) => handleDelete(session.id, e)}
							class="p-1.5 rounded-md text-neutral-400 hover:text-error-600 hover:bg-error-50 dark:hover:text-error-400 dark:hover:bg-error-900/20 transition-colors disabled:opacity-50"
							title="Delete meeting"
							disabled={deletingSessionId !== null}
						>
							{#if deletingSessionId === session.id}
								<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
							{:else}
								<Trash2 size={14} />
							{/if}
						</button>
					</div>

					<!-- Arrow (visible when not hovering) -->
					<svg class="w-4 h-4 text-neutral-400 dark:text-neutral-500 flex-shrink-0 group-hover:opacity-0 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</a>
			{/each}
		</div>
	{/if}

	<!-- Footer with "View all" link (when <= 5 sessions) -->
	{#if totalCount > 0 && totalCount <= 5}
		<div class="px-4 py-3 border-t border-neutral-200 dark:border-neutral-700 text-center">
			<a
				href="/meeting"
				class="text-sm text-brand-600 dark:text-brand-400 hover:underline inline-flex items-center gap-1"
			>
				View all {totalCount} meeting{totalCount !== 1 ? 's' : ''}
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
				</svg>
			</a>
		</div>
	{/if}
</div>
