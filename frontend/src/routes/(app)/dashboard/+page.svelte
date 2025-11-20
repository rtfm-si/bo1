<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user, isAuthenticated } from '$lib/stores/auth';
	import Header from '$lib/components/Header.svelte';
	import { apiClient } from '$lib/api/client';

	interface Session {
		id: string;
		problem_statement: string;
		status: 'active' | 'paused' | 'completed' | 'failed' | 'killed';
		phase: string | null;
		created_at: string;
		completed_at?: string;
		round_number: number;
	}

	let sessions: Session[] = $state([]);
	let isLoading = $state(true);
	let error: string | null = $state(null);

	onMount(async () => {
		// Wait for auth to be initialized before loading sessions
		const unsubscribe = isAuthenticated.subscribe(async (authenticated) => {
			if (authenticated) {
				// User is authenticated - load sessions
				await loadSessions();
			} else if (authenticated === false) {
				// User is NOT authenticated - redirect to login
				goto('/login');
			}
			// If undefined, auth is still loading - do nothing
		});

		return unsubscribe;
	});

	async function loadSessions() {
		try {
			isLoading = true;
			error = null;

			console.log('[Dashboard] Loading sessions...');
			console.log('[Dashboard] User from auth store:', $user);
			console.log('[Dashboard] Is authenticated:', $isAuthenticated);

			const data = await apiClient.listSessions();
			console.log('[Dashboard] Sessions loaded:', data);
			sessions = data.sessions || [];
		} catch (err) {
			console.error('[Dashboard] Failed to load sessions:', err);
			error = err instanceof Error ? err.message : 'Failed to load sessions';
		} finally {
			isLoading = false;
		}
	}

	function getStatusColor(status: string): string {
		const colors = {
			active: 'bg-info-100 text-info-800 dark:bg-info-900/20 dark:text-info-300',
			paused: 'bg-warning-100 text-warning-800 dark:bg-warning-900/20 dark:text-warning-300',
			completed: 'bg-success-100 text-success-800 dark:bg-success-900/20 dark:text-success-300',
			failed: 'bg-error-100 text-error-800 dark:bg-error-900/20 dark:text-error-300',
			killed: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-900/20 dark:text-neutral-300'
		};
		return colors[status as keyof typeof colors] || 'bg-neutral-100 text-neutral-800';
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
			<div class="flex items-center justify-center py-12">
				<svg class="animate-spin h-8 w-8 text-brand-600 dark:text-brand-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
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
				<button
					onclick={loadSessions}
					class="mt-4 px-4 py-2 bg-error-600 hover:bg-error-700 text-white rounded-lg transition-colors duration-200"
				>
					Retry
				</button>
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
					Get started by creating your first strategic decision meeting. Our AI board will analyze your problem from multiple expert perspectives.
				</p>
				<a
					href="/meeting/new"
					class="inline-flex items-center gap-2 px-6 py-3 bg-brand-600 hover:bg-brand-700 text-white font-medium rounded-lg transition-colors duration-200"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
					</svg>
					Start Your First Meeting
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
									<span class="px-2.5 py-1 text-xs font-medium rounded-full {getStatusColor(session.status)}">
										{session.status}
									</span>
									<span class="text-xs text-neutral-500 dark:text-neutral-400">
										{formatDate(session.created_at)}
									</span>
									{#if session.status === 'active'}
										<span class="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
											<span class="inline-block w-2 h-2 bg-brand-600 dark:bg-brand-400 rounded-full animate-pulse"></span>
											Round {session.round_number}
										</span>
									{/if}
								</div>

								<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
									{truncateProblem(session.problem_statement)}
								</h3>

								<div class="flex items-center gap-4 text-sm text-neutral-600 dark:text-neutral-400">
									<span class="flex items-center gap-1">
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
										</svg>
										{session.phase ? session.phase.replace(/_/g, ' ') : 'Initializing'}
									</span>
									<span class="flex items-center gap-1">
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
										</svg>
										Round {session.round_number}
									</span>
								</div>
							</div>

							<svg class="w-5 h-5 text-neutral-400 dark:text-neutral-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
							</svg>
						</div>
					</a>
				{/each}
			</div>
		{/if}
	</main>
</div>
