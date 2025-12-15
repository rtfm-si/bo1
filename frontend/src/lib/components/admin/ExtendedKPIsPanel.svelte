<script lang="ts">
	import { onMount } from 'svelte';
	import { MessageSquare, Database, FolderKanban, CheckSquare, Loader2, AlertCircle } from 'lucide-svelte';
	import { apiClient } from '$lib/api/client';
	import type { ExtendedKPIsResponse } from '$lib/api/types';

	let data = $state<ExtendedKPIsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function loadKPIs() {
		loading = true;
		error = null;
		try {
			data = await apiClient.getExtendedKPIs();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load extended KPIs';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadKPIs();
	});
</script>

<div class="mb-8">
	<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Extended KPIs</h2>

	{#if loading}
		<div class="flex items-center justify-center py-8">
			<Loader2 class="w-6 h-6 text-neutral-400 animate-spin" />
			<span class="ml-2 text-neutral-600 dark:text-neutral-400">Loading KPIs...</span>
		</div>
	{:else if error}
		<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4">
			<div class="flex items-center gap-2 text-error-700 dark:text-error-400">
				<AlertCircle class="w-5 h-5" />
				<span>{error}</span>
			</div>
			<button
				onclick={() => loadKPIs()}
				class="mt-2 text-sm text-error-600 dark:text-error-400 hover:underline"
			>
				Retry
			</button>
		</div>
	{:else if data}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
			<!-- Mentor Sessions -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3 mb-4">
					<div class="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
						<MessageSquare class="w-6 h-6 text-purple-600 dark:text-purple-400" />
					</div>
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Mentor Sessions</h3>
				</div>
				<div class="space-y-2">
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Total</span>
						<span class="text-lg font-semibold text-neutral-900 dark:text-white">{data.mentor_sessions.total_sessions.toLocaleString()}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Today</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">{data.mentor_sessions.sessions_today}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">This Week</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">{data.mentor_sessions.sessions_this_week}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">This Month</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">{data.mentor_sessions.sessions_this_month}</span>
					</div>
				</div>
			</div>

			<!-- Data Analyses -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3 mb-4">
					<div class="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
						<Database class="w-6 h-6 text-blue-600 dark:text-blue-400" />
					</div>
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Data Analyses</h3>
				</div>
				<div class="space-y-2">
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Total</span>
						<span class="text-lg font-semibold text-neutral-900 dark:text-white">{data.data_analyses.total_analyses.toLocaleString()}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Today</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">{data.data_analyses.analyses_today}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">This Week</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">{data.data_analyses.analyses_this_week}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">This Month</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">{data.data_analyses.analyses_this_month}</span>
					</div>
				</div>
			</div>

			<!-- Projects -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3 mb-4">
					<div class="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
						<FolderKanban class="w-6 h-6 text-green-600 dark:text-green-400" />
					</div>
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Projects</h3>
				</div>
				<div class="space-y-2">
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Total</span>
						<span class="text-lg font-semibold text-neutral-900 dark:text-white">{data.projects.total_projects.toLocaleString()}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Active</span>
						<span class="text-sm font-medium text-success-600 dark:text-success-400">{data.projects.active}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Paused</span>
						<span class="text-sm font-medium text-warning-600 dark:text-warning-400">{data.projects.paused}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Completed</span>
						<span class="text-sm font-medium text-info-600 dark:text-info-400">{data.projects.completed}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Archived</span>
						<span class="text-sm font-medium text-neutral-500">{data.projects.archived}</span>
					</div>
				</div>
			</div>

			<!-- Actions -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3 mb-4">
					<div class="p-3 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
						<CheckSquare class="w-6 h-6 text-orange-600 dark:text-orange-400" />
					</div>
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Actions</h3>
				</div>
				<div class="space-y-2">
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Total</span>
						<span class="text-lg font-semibold text-neutral-900 dark:text-white">{data.actions.total_actions.toLocaleString()}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Pending</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">{data.actions.pending}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">In Progress</span>
						<span class="text-sm font-medium text-brand-600 dark:text-brand-400">{data.actions.in_progress}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Completed</span>
						<span class="text-sm font-medium text-success-600 dark:text-success-400">{data.actions.completed}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Cancelled</span>
						<span class="text-sm font-medium text-error-600 dark:text-error-400">{data.actions.cancelled}</span>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
