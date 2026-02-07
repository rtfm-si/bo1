<script lang="ts">
	import { onMount } from 'svelte';
	import { MessageSquare, Database, FolderKanban, CheckSquare, Loader2, AlertCircle } from 'lucide-svelte';
	import { apiClient } from '$lib/api/client';
	import { StatCard, StatCardRow } from '$lib/components/ui';
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
			<StatCard label="Mentor Sessions" icon={MessageSquare} iconColorClass="text-purple-600 dark:text-purple-400" iconBgClass="bg-purple-100 dark:bg-purple-900/30">
				<StatCardRow label="Total" value={data.mentor_sessions.total_sessions.toLocaleString()} prominent />
				<StatCardRow label="Today" value={data.mentor_sessions.sessions_today} />
				<StatCardRow label="This Week" value={data.mentor_sessions.sessions_this_week} />
				<StatCardRow label="This Month" value={data.mentor_sessions.sessions_this_month} />
			</StatCard>

			<StatCard label="Data Analyses" icon={Database} iconColorClass="text-info-600 dark:text-info-400" iconBgClass="bg-info-100 dark:bg-info-900/30">
				<StatCardRow label="Total" value={data.data_analyses.total_analyses.toLocaleString()} prominent />
				<StatCardRow label="Today" value={data.data_analyses.analyses_today} />
				<StatCardRow label="This Week" value={data.data_analyses.analyses_this_week} />
				<StatCardRow label="This Month" value={data.data_analyses.analyses_this_month} />
			</StatCard>

			<StatCard label="Projects" icon={FolderKanban} iconColorClass="text-success-600 dark:text-success-400" iconBgClass="bg-success-100 dark:bg-success-900/30">
				<StatCardRow label="Total" value={data.projects.total_projects.toLocaleString()} prominent />
				<StatCardRow label="Active" value={data.projects.active} valueColorClass="text-success-600 dark:text-success-400" />
				<StatCardRow label="Paused" value={data.projects.paused} valueColorClass="text-warning-600 dark:text-warning-400" />
				<StatCardRow label="Completed" value={data.projects.completed} valueColorClass="text-info-600 dark:text-info-400" />
				<StatCardRow label="Archived" value={data.projects.archived} valueColorClass="text-neutral-500" />
			</StatCard>

			<StatCard label="Actions" icon={CheckSquare} iconColorClass="text-orange-600 dark:text-orange-400" iconBgClass="bg-orange-100 dark:bg-orange-900/30">
				<StatCardRow label="Total" value={data.actions.total_actions.toLocaleString()} prominent />
				<StatCardRow label="Pending" value={data.actions.pending} />
				<StatCardRow label="In Progress" value={data.actions.in_progress} valueColorClass="text-brand-600 dark:text-brand-400" />
				<StatCardRow label="Completed" value={data.actions.completed} valueColorClass="text-success-600 dark:text-success-400" />
				<StatCardRow label="Cancelled" value={data.actions.cancelled} valueColorClass="text-error-600 dark:text-error-400" />
			</StatCard>
		</div>
	{/if}
</div>
