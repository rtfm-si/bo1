<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user, isAuthenticated } from '$lib/stores/auth';

	interface Session {
		id: string;
		problem_statement: string;
		status: 'active' | 'paused' | 'completed' | 'failed' | 'killed';
		phase: string;
		created_at: string;
		completed_at?: string;
		total_cost: number;
		round_number: number;
	}

	let sessions: Session[] = [];
	let isLoading = true;
	let error: string | null = null;

	onMount(async () => {
		// Check if authenticated
		const unsubscribe = isAuthenticated.subscribe((authenticated) => {
			if (!authenticated) {
				goto('/login');
			}
		});

		await loadSessions();

		return unsubscribe;
	});

	async function loadSessions() {
		try {
			isLoading = true;
			error = null;

			const response = await fetch('/api/v1/sessions', {
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error('Failed to load sessions');
			}

			const data = await response.json();
			sessions = data.sessions || [];
		} catch (err) {
			console.error('Failed to load sessions:', err);
			error = err instanceof Error ? err.message : 'Failed to load sessions';
		} finally {
			isLoading = false;
		}
	}

	function getStatusColor(status: string): string {
		const colors = {
			active: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300',
			paused: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300',
			completed: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300',
			failed: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300',
			killed: 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-300'
		};
		return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800';
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

<div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
	<!-- Header -->
	<header class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-2xl font-bold text-slate-900 dark:text-white">
						Board of One
					</h1>
					<p class="text-sm text-slate-600 dark:text-slate-400">
						Welcome back, {$user?.email || 'User'}
					</p>
				</div>
				<a
					href="/meeting/new"
					class="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200 shadow-sm hover:shadow-md"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
					</svg>
					Start New Meeting
				</a>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if isLoading}
			<!-- Loading State -->
			<div class="flex items-center justify-center py-12">
				<svg class="animate-spin h-8 w-8 text-blue-600 dark:text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
			</div>
		{:else if error}
			<!-- Error State -->
			<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
				<div class="flex items-center gap-3">
					<svg class="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<div>
						<h3 class="text-lg font-semibold text-red-900 dark:text-red-200">Failed to load sessions</h3>
						<p class="text-sm text-red-700 dark:text-red-300">{error}</p>
					</div>
				</div>
				<button
					on:click={loadSessions}
					class="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors duration-200"
				>
					Retry
				</button>
			</div>
		{:else if sessions.length === 0}
			<!-- Empty State -->
			<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-12 text-center">
				<svg class="w-16 h-16 mx-auto text-slate-400 dark:text-slate-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
				</svg>
				<h2 class="text-2xl font-semibold text-slate-900 dark:text-white mb-2">
					No meetings yet
				</h2>
				<p class="text-slate-600 dark:text-slate-400 mb-6 max-w-md mx-auto">
					Get started by creating your first strategic decision meeting. Our AI board will analyze your problem from multiple expert perspectives.
				</p>
				<a
					href="/meeting/new"
					class="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200"
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
				<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-4">
					Your Meetings ({sessions.length})
				</h2>

				{#each sessions as session}
					<a
						href="/meeting/{session.id}"
						class="block bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-6 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-700 transition-all duration-200"
					>
						<div class="flex items-start justify-between gap-4">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-3 mb-2">
									<span class="px-2.5 py-1 text-xs font-medium rounded-full {getStatusColor(session.status)}">
										{session.status}
									</span>
									<span class="text-xs text-slate-500 dark:text-slate-400">
										{formatDate(session.created_at)}
									</span>
									{#if session.status === 'active'}
										<span class="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
											<span class="inline-block w-2 h-2 bg-blue-600 dark:bg-blue-400 rounded-full animate-pulse"></span>
											Round {session.round_number}
										</span>
									{/if}
								</div>

								<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-2">
									{truncateProblem(session.problem_statement)}
								</h3>

								<div class="flex items-center gap-4 text-sm text-slate-600 dark:text-slate-400">
									<span class="flex items-center gap-1">
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
										</svg>
										{session.phase.replace(/_/g, ' ')}
									</span>
									<span class="flex items-center gap-1">
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
										</svg>
										${session.total_cost.toFixed(2)}
									</span>
								</div>
							</div>

							<svg class="w-5 h-5 text-slate-400 dark:text-slate-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
							</svg>
						</div>
					</a>
				{/each}
			</div>
		{/if}
	</main>
</div>
