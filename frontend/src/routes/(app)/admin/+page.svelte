<script lang="ts">
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import { Button } from '$lib/components/ui';
	import { Users, List, TrendingUp, DollarSign, Clock } from 'lucide-svelte';

	let stats = $state({
		totalUsers: 0,
		totalMeetings: 0,
		totalCost: 0,
		whitelistCount: 0,
		waitlistPending: 0
	});
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			isLoading = true;
			// Fetch stats from API
			const [usersResponse, whitelistResponse, waitlistResponse] = await Promise.all([
				apiClient.listUsers({ page: 1, per_page: 1 }),
				apiClient.listWhitelist(),
				apiClient.listWaitlist({ status: 'pending' })
			]);

			stats = {
				totalUsers: usersResponse.total_count,
				totalMeetings: usersResponse.users[0]?.total_meetings || 0,
				totalCost: usersResponse.users.reduce((sum, u) => sum + (u.total_cost || 0), 0),
				whitelistCount: whitelistResponse.total_count,
				waitlistPending: waitlistResponse.pending_count
			};
		} catch (err) {
			console.error('Failed to load admin stats:', err);
			error = err instanceof Error ? err.message : 'Failed to load stats';
		} finally {
			isLoading = false;
		}
	});
</script>

<svelte:head>
	<title>Admin Dashboard - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/dashboard"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
						aria-label="Back to dashboard"
					>
						<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</a>
					<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
						Admin Dashboard
					</h1>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if isLoading}
			<!-- Loading State -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
				{#each Array(4) as _}
					<div class="animate-pulse bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
						<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-24 mb-4"></div>
						<div class="h-8 bg-neutral-200 dark:bg-neutral-700 rounded w-16"></div>
					</div>
				{/each}
			</div>
		{:else if error}
			<!-- Error State -->
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-6 mb-8">
				<p class="text-error-700 dark:text-error-300">{error}</p>
			</div>
		{:else}
			<!-- Stats Cards -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
				<!-- Total Users -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Total Users</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{stats.totalUsers}</p>
						</div>
						<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
							<Users class="w-6 h-6 text-brand-600 dark:text-brand-400" />
						</div>
					</div>
				</div>

				<!-- Total Meetings -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Total Meetings</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{stats.totalMeetings}</p>
						</div>
						<div class="p-3 bg-accent-100 dark:bg-accent-900/30 rounded-lg">
							<TrendingUp class="w-6 h-6 text-accent-600 dark:text-accent-400" />
						</div>
					</div>
				</div>

				<!-- Total Cost -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Total Cost</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">${stats.totalCost.toFixed(2)}</p>
						</div>
						<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
							<DollarSign class="w-6 h-6 text-success-600 dark:text-success-400" />
						</div>
					</div>
				</div>

				<!-- Waitlist Pending -->
				<a
					href="/admin/waitlist"
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-amber-300 dark:hover:border-amber-700 transition-all duration-200"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Waitlist</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{stats.waitlistPending}</p>
						</div>
						<div class="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
							<Clock class="w-6 h-6 text-amber-600 dark:text-amber-400" />
						</div>
					</div>
				</a>

				<!-- Whitelist Count -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Whitelist</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{stats.whitelistCount}</p>
						</div>
						<div class="p-3 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
							<List class="w-6 h-6 text-warning-600 dark:text-warning-400" />
						</div>
					</div>
				</div>
			</div>
		{/if}

		<!-- Quick Links -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
			<!-- Waitlist Card -->
			<a
				href="/admin/waitlist"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-amber-300 dark:hover:border-amber-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
						<Clock class="w-6 h-6 text-amber-600 dark:text-amber-400" />
					</div>
					<div>
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Waitlist</h2>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Approve beta access requests</p>
					</div>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-sm text-amber-600 dark:text-amber-400">
						{#if stats.waitlistPending > 0}
							{stats.waitlistPending} pending →
						{:else}
							View waitlist →
						{/if}
					</span>
				</div>
			</a>

			<!-- Users Card -->
			<a
				href="/admin/users"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
						<Users class="w-6 h-6 text-brand-600 dark:text-brand-400" />
					</div>
					<div>
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">User Management</h2>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">View and manage all users</p>
					</div>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-sm text-brand-600 dark:text-brand-400">View users →</span>
				</div>
			</a>

			<!-- Whitelist Card -->
			<a
				href="/admin/whitelist"
				class="block bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-200"
			>
				<div class="flex items-center gap-4 mb-3">
					<div class="p-3 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
						<List class="w-6 h-6 text-warning-600 dark:text-warning-400" />
					</div>
					<div>
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Beta Whitelist</h2>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Manage beta access</p>
					</div>
				</div>
				<div class="flex items-center justify-between">
					<span class="text-sm text-warning-600 dark:text-warning-400">Manage whitelist →</span>
				</div>
			</a>
		</div>
	</main>
</div>
