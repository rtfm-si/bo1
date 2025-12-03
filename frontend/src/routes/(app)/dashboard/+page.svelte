<script lang="ts">
	import { onMount } from 'svelte';
	import { user } from '$lib/stores/auth';
	import Header from '$lib/components/Header.svelte';
	import { apiClient } from '$lib/api/client';
	import type { SessionResponse } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { getSessionStatusColor } from '$lib/utils/persona-colors';

	// Use data fetch utility for sessions
	const sessionsData = useDataFetch(() => apiClient.listSessions());

	// Derived state for template compatibility
	const sessions = $derived<SessionResponse[]>(sessionsData.data?.sessions || []);
	const isLoading = $derived(sessionsData.isLoading);
	const error = $derived(sessionsData.error);

	// Check if user is admin for cost display
	const isAdmin = $derived($user?.is_admin ?? false);

	onMount(() => {
		console.log('[Dashboard] onMount - user is authenticated, loading sessions');
		console.log('[Dashboard] User from auth store:', $user);
		// Auth is already verified by parent layout, safe to load sessions
		sessionsData.fetch();
	});

	async function loadSessions() {
		console.log('[Dashboard] Loading sessions...');
		await sessionsData.fetch();
		console.log('[Dashboard] Sessions loaded:', sessionsData.data);
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMins / 60);
		const diffDays = Math.floor(diffHours / 24);

		if (diffMins < 1) return 'just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays < 7) return `${diffDays}d ago`;

		return date.toLocaleDateString();
	}

	function truncateProblem(problem: string, maxLength: number = 80): string {
		if (problem.length <= maxLength) return problem;
		return problem.substring(0, maxLength) + '...';
	}

	/**
	 * Humanize phase names for user-friendly display
	 * Phases: decomposition, selection, exploration, challenge, convergence, voting, synthesis
	 */
	function humanizePhase(phase: string | null): string {
		if (!phase) return 'Starting';

		const phaseMap: Record<string, string> = {
			// Main deliberation phases
			decomposition: 'Analyzing',
			decompose: 'Analyzing',
			problem_decomposition: 'Analyzing', // Legacy DB default
			selection: 'Selecting Experts',
			exploration: 'Exploring Ideas',
			challenge: 'Deep Analysis',
			convergence: 'Building Consensus',
			voting: 'Collecting Votes',
			synthesis: 'Synthesizing',
			meta_synthesis: 'Final Synthesis',
			// Status-like phases
			complete: 'Completed',
			completed: 'Completed',
			failed: 'Failed',
			killed: 'Stopped',
		};

		return phaseMap[phase.toLowerCase()] || phase.replace(/_/g, ' ');
	}

	async function handleDelete(sessionId: string, event: MouseEvent) {
		event.preventDefault(); // Prevent navigation
		event.stopPropagation(); // Stop event bubbling

		if (!confirm('Are you sure you want to delete this meeting? This cannot be undone.')) {
			return;
		}

		try {
			await apiClient.deleteSession(sessionId);
			// Refresh sessions list after successful delete
			await sessionsData.fetch();
		} catch (err) {
			console.error('Failed to delete session:', err);
			// Error will be reflected in sessionsData.error
		}
	}
</script>

<svelte:head>
	<title>Dashboard - Board of One</title>
</svelte:head>

<Header transparent={false} showCTA={true} />

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800 pt-16">

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if isLoading}
			<!-- Loading State -->
			<div class="space-y-4">
				{#each Array(3) as _, i}
					<ShimmerSkeleton type="card" />
				{/each}
			</div>
		{:else if error}
			<!-- Error State -->
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-6">
				<div class="flex items-center gap-3">
					<svg class="w-6 h-6 text-error-600 dark:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<div>
						<h3 class="text-lg font-semibold text-error-900 dark:text-error-200">Error Loading Sessions</h3>
						<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
					</div>
				</div>
				<div class="mt-4">
					<Button variant="danger" size="md" onclick={loadSessions}>
						{#snippet children()}
							Retry
						{/snippet}
					</Button>
				</div>
			</div>
		{:else if sessions.length === 0}
			<!-- Empty State -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-12 text-center">
				<svg class="w-16 h-16 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
				</svg>
				<h2 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-2">
					No meetings yet
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-md mx-auto">
					Get started by creating your first strategic decision meeting. Our AI board will analyze your decision from multiple expert perspectives.
				</p>
				<a href="/meeting/new">
					<Button variant="brand" size="lg">
						{#snippet children()}
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
							</svg>
							Start Your First Meeting
						{/snippet}
					</Button>
				</a>
			</div>
		{:else}
			<!-- Sessions List -->
			<div class="space-y-4">
				<h2 class="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
					Your Meetings ({sessions.length})
				</h2>

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
									<span class="text-xs text-neutral-500 dark:text-neutral-400" title="Created">
										Created {formatDate(session.created_at)}
									</span>
									{#if session.last_activity_at}
										<span class="text-xs text-neutral-500 dark:text-neutral-400" title="Last activity">
											<span class="inline-block w-1.5 h-1.5 bg-neutral-400 dark:bg-neutral-500 rounded-full mr-1"></span>
											Activity {formatDate(session.last_activity_at)}
										</span>
									{/if}
									{#if session.status === 'active'}
										<span class="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
											<span class="inline-block w-2 h-2 bg-brand-600 dark:bg-brand-400 rounded-full animate-pulse"></span>
											Active
										</span>
									{/if}
								</div>

								<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
									{truncateProblem(session.problem_statement)}
								</h3>

								<div class="flex items-center gap-4 text-sm text-neutral-600 dark:text-neutral-400">
									{#if session.status !== 'completed'}
										<span class="flex items-center gap-1.5">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
											{humanizePhase(session.phase)}
										</span>
									{/if}
									{#if session.expert_count}
										<span class="flex items-center gap-1.5" title="Experts consulted">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
											</svg>
											{session.expert_count} experts
										</span>
									{/if}
									{#if session.contribution_count}
										<span class="flex items-center gap-1.5" title="Total contributions">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
											</svg>
											{session.contribution_count} insights
										</span>
									{/if}
									{#if session.task_count}
										<span class="flex items-center gap-1.5" title="Action items">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
											</svg>
											{session.task_count} actions
										</span>
									{/if}
									{#if isAdmin && session.cost != null}
										<span class="flex items-center gap-1.5 text-neutral-500 dark:text-neutral-500" title="Meeting cost (admin only)">
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
											${session.cost.toFixed(4)}
										</span>
									{/if}
								</div>
							</div>

							<div class="flex items-center gap-2 flex-shrink-0">
								<button
									onclick={(e) => handleDelete(session.id, e)}
									class="p-2 hover:bg-error-50 dark:hover:bg-error-900/20 rounded-lg transition-colors duration-200 group"
									title="Delete meeting"
									aria-label="Delete meeting"
								>
									<svg class="w-5 h-5 text-neutral-400 dark:text-neutral-500 group-hover:text-error-600 dark:group-hover:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
									</svg>
								</button>

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
