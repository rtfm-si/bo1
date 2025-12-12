<script lang="ts">
	import { onMount } from 'svelte';
	import { History, RefreshCw, Skull, User, DollarSign, Calendar } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { adminApi, type SessionKillsResponse, type SessionKill } from '$lib/api/admin';

	// State
	let kills = $state<SessionKillsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let page = $state(0);
	const pageSize = 20;

	async function loadKills() {
		try {
			loading = true;
			kills = await adminApi.getKillHistory({ limit: pageSize, offset: page * pageSize });
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load kill history';
		} finally {
			loading = false;
		}
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatCost(cost: number | null): string {
		if (cost === null) return '-';
		return `$${cost.toFixed(4)}`;
	}

	function nextPage() {
		if (kills && (page + 1) * pageSize < kills.total) {
			page++;
			loadKills();
		}
	}

	function prevPage() {
		if (page > 0) {
			page--;
			loadKills();
		}
	}

	onMount(() => {
		loadKills();
	});
</script>

<svelte:head>
	<title>Kill History - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/admin"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
						aria-label="Back to admin"
					>
						<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</a>
					<div class="flex items-center gap-3">
						<History class="w-6 h-6 text-error-600 dark:text-error-400" />
						<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">Kill History</h1>
					</div>
				</div>
				<Button variant="secondary" size="sm" onclick={loadKills}>
					<RefreshCw class="w-4 h-4" />
					Refresh
				</Button>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if error}
			<Alert variant="error" class="mb-6">{error}</Alert>
		{/if}

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
			</div>
		{:else if kills}
			{#if kills.kills.length === 0}
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-12 border border-neutral-200 dark:border-neutral-700 text-center">
					<History class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
					<p class="text-lg text-neutral-600 dark:text-neutral-400">No kill history</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-500 mt-1">Session terminations will appear here</p>
				</div>
			{:else}
				<!-- Stats -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 mb-6">
					<div class="flex items-center gap-4">
						<div class="p-3 bg-error-100 dark:bg-error-900/30 rounded-lg">
							<Skull class="w-6 h-6 text-error-600 dark:text-error-400" />
						</div>
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400">Total Sessions Killed</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{kills.total}</p>
						</div>
					</div>
				</div>

				<!-- Kill History Table -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					<table class="w-full">
						<thead class="bg-neutral-50 dark:bg-neutral-700">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Time</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Session</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Killed By</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Reason</th>
								<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Cost at Kill</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each kills.kills as kill (kill.id)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors">
									<td class="px-6 py-4">
										<div class="flex items-center gap-2">
											<Calendar class="w-4 h-4 text-neutral-400" />
											<span class="text-sm text-neutral-700 dark:text-neutral-300">{formatDate(kill.created_at)}</span>
										</div>
									</td>
									<td class="px-6 py-4">
										{#if kill.session_id}
											<span class="text-sm font-mono text-neutral-900 dark:text-white truncate max-w-[150px] inline-block" title={kill.session_id}>
												{kill.session_id.slice(0, 8)}...
											</span>
										{:else}
											<span class="text-sm text-neutral-500 italic">Deleted</span>
										{/if}
									</td>
									<td class="px-6 py-4">
										<div class="flex items-center gap-2">
											<User class="w-4 h-4 text-neutral-400" />
											<span class="text-sm {kill.killed_by === 'system' ? 'text-amber-600 dark:text-amber-400 font-medium' : 'text-neutral-700 dark:text-neutral-300'}">
												{kill.killed_by}
											</span>
										</div>
									</td>
									<td class="px-6 py-4">
										<span class="text-sm text-neutral-600 dark:text-neutral-400 truncate max-w-[200px] inline-block" title={kill.reason}>
											{kill.reason}
										</span>
									</td>
									<td class="px-6 py-4 text-right">
										<div class="flex items-center justify-end gap-1">
											<DollarSign class="w-4 h-4 text-neutral-400" />
											<span class="text-sm text-neutral-700 dark:text-neutral-300">{formatCost(kill.cost_at_kill)}</span>
										</div>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>

					<!-- Pagination -->
					{#if kills.total > pageSize}
						<div class="px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
							<p class="text-sm text-neutral-600 dark:text-neutral-400">
								Showing {page * pageSize + 1} - {Math.min((page + 1) * pageSize, kills.total)} of {kills.total}
							</p>
							<div class="flex items-center gap-2">
								<Button variant="secondary" size="sm" onclick={prevPage} disabled={page === 0}>
									Previous
								</Button>
								<Button variant="secondary" size="sm" onclick={nextPage} disabled={(page + 1) * pageSize >= kills.total}>
									Next
								</Button>
							</div>
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</main>
</div>
