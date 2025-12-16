<script lang="ts">
	/**
	 * Reports > Meetings Page - Shows completed meeting reports only
	 *
	 * Read-only view of completed sessions for the Reports section.
	 * For managing all sessions (including active), use Board > Meetings.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { SessionResponse } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { getSessionStatusColor } from '$lib/utils/colors';
	import { formatCompactRelativeTime } from '$lib/utils/time-formatting';
	import { toast } from '$lib/stores/toast';

	let isLoading = $state(true);
	let sessions = $state<SessionResponse[]>([]);

	async function fetchSessions() {
		isLoading = true;
		try {
			const response = await apiClient.listSessions({ status: 'completed' });
			sessions = response.sessions || [];
		} catch (err) {
			console.error('Failed to fetch sessions:', err);
			toast.error(err instanceof Error ? err.message : 'Failed to load meeting reports');
		} finally {
			isLoading = false;
		}
	}

	onMount(() => {
		fetchSessions();
	});

	function truncateProblem(problem: string, maxLength: number = 80): string {
		if (problem.length <= maxLength) return problem;
		return problem.substring(0, maxLength) + '...';
	}
</script>

<svelte:head>
	<title>Meeting Reports - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Header -->
		<div class="flex items-center justify-between mb-6">
			<div>
				<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">Meeting Reports</h1>
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
					Completed meeting summaries and decisions
				</p>
			</div>
		</div>

		{#if isLoading}
			<div class="space-y-4">
				{#each Array(3) as _, i (i)}
					<ShimmerSkeleton type="card" />
				{/each}
			</div>
		{:else if sessions.length === 0}
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-12 text-center">
				<svg class="w-16 h-16 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
				</svg>
				<h2 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-2">No completed meeting reports yet</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-md mx-auto">
					Completed meetings will appear here as reports. Start a new meeting from the Board section.
				</p>
				<a
					href="/meeting"
					class="inline-flex items-center gap-2 text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 font-medium"
				>
					Go to Board > Meetings
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</a>
			</div>
		{:else}
			<div class="space-y-4">
				{#each sessions as session (session.id)}
					<a
						href="/meeting/{session.id}"
						class="block bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-200"
					>
						<div class="flex items-start justify-between gap-4">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-3 mb-2">
									<span class="px-2.5 py-1 text-xs font-medium rounded-full {getSessionStatusColor(session.status)}">
										{session.status}
									</span>
									<span class="text-xs text-neutral-500 dark:text-neutral-400">
										Completed {formatCompactRelativeTime(session.created_at)}
									</span>
								</div>

								<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
									{truncateProblem(session.problem_statement)}
								</h3>

								<div class="flex items-center gap-4 text-sm text-neutral-600 dark:text-neutral-400">
									{#if session.expert_count}
										<span class="flex items-center gap-1.5">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
											</svg>
											{session.expert_count} experts
										</span>
									{/if}
									{#if session.contribution_count}
										<span class="flex items-center gap-1.5">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
											</svg>
											{session.contribution_count} insights
										</span>
									{/if}
									{#if session.task_count}
										<span class="flex items-center gap-1.5">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
											</svg>
											{session.task_count} actions
										</span>
									{/if}
								</div>
							</div>

							<div class="flex items-center gap-2 flex-shrink-0">
								<svg class="w-5 h-5 text-neutral-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
								</svg>
							</div>
						</div>
					</a>
				{/each}
			</div>
		{/if}
	</main>
</div>
