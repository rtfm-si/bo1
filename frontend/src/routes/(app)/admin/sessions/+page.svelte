<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Activity, RefreshCw, AlertTriangle, Skull, Clock, DollarSign, User } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import SessionDetailModal from '$lib/components/admin/SessionDetailModal.svelte';
	import { adminApi, type ActiveSessionInfo, type ActiveSessionsResponse } from '$lib/api/admin';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';

	// State
	let sessions = $state<ActiveSessionsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let refreshing = $state(false);
	let autoRefresh = $state(true);
	let refreshInterval: ReturnType<typeof setInterval> | null = null;

	// Modal state
	let selectedSessionId = $state<string | null>(null);
	let showDetailModal = $state(false);
	let showKillAllConfirm = $state(false);
	let killAllReason = $state('');
	let killingAll = $state(false);

	async function loadSessions() {
		try {
			if (!loading) refreshing = true;
			sessions = await adminApi.getActiveSessions(20);
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load sessions';
		} finally {
			loading = false;
			refreshing = false;
		}
	}

	function setupAutoRefresh() {
		if (refreshInterval) clearInterval(refreshInterval);
		if (autoRefresh) {
			refreshInterval = setInterval(loadSessions, 10000); // 10s polling
		}
	}

	function openSessionDetail(sessionId: string) {
		selectedSessionId = sessionId;
		showDetailModal = true;
	}

	function closeDetailModal() {
		showDetailModal = false;
		selectedSessionId = null;
	}

	async function handleKillAll() {
		if (!killAllReason.trim()) {
			return;
		}
		try {
			killingAll = true;
			await adminApi.killAllSessions(killAllReason);
			showKillAllConfirm = false;
			killAllReason = '';
			await loadSessions();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to kill sessions';
		} finally {
			killingAll = false;
		}
	}

	function formatDuration(seconds: number): string {
		if (seconds < 60) return `${Math.round(seconds)}s`;
		if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
		const hours = Math.floor(seconds / 3600);
		const mins = Math.floor((seconds % 3600) / 60);
		return `${hours}h ${mins}m`;
	}

	function formatCost(cost: number | null): string {
		if (cost === null) return '-';
		return `$${cost.toFixed(4)}`;
	}

	$effect(() => {
		setupAutoRefresh();
	});

	onMount(() => {
		loadSessions();
	});

	onDestroy(() => {
		if (refreshInterval) clearInterval(refreshInterval);
	});
</script>

<svelte:head>
	<title>Active Sessions - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="Active Sessions" icon={Activity}>
		{#snippet actions()}
			<label class="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
				<input
					type="checkbox"
					bind:checked={autoRefresh}
					class="rounded border-neutral-300 dark:border-neutral-600"
				/>
				Auto-refresh (10s)
			</label>
			<Button variant="secondary" size="sm" onclick={loadSessions} disabled={refreshing}>
				<RefreshCw class="w-4 h-4 {refreshing ? 'animate-spin' : ''}" />
				Refresh
			</Button>
			{#if sessions && sessions.active_count > 0}
				<Button variant="danger" size="sm" onclick={() => (showKillAllConfirm = true)}>
					<Skull class="w-4 h-4" />
					Kill All
				</Button>
			{/if}
		{/snippet}
	</AdminPageHeader>

	<!-- Main Content -->
	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-8">
		{#if error}
			<Alert variant="error" class="mb-6">
				{error}
			</Alert>
		{/if}

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
			</div>
		{:else if sessions}
			<!-- Stats Row -->
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Active Sessions</p>
							<p class="text-3xl font-semibold text-neutral-900 dark:text-white">{sessions.active_count}</p>
						</div>
						<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
							<Activity class="w-6 h-6 text-brand-600 dark:text-brand-400" />
						</div>
					</div>
				</div>
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Longest Running</p>
							<p class="text-3xl font-semibold text-neutral-900 dark:text-white">
								{sessions.longest_running[0] ? formatDuration(sessions.longest_running[0].duration_seconds) : '-'}
							</p>
						</div>
						<div class="p-3 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
							<Clock class="w-6 h-6 text-warning-600 dark:text-warning-400" />
						</div>
					</div>
				</div>
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Most Expensive</p>
							<p class="text-3xl font-semibold text-neutral-900 dark:text-white">
								{sessions.most_expensive[0] ? formatCost(sessions.most_expensive[0].cost) : '-'}
							</p>
						</div>
						<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
							<DollarSign class="w-6 h-6 text-success-600 dark:text-success-400" />
						</div>
					</div>
				</div>
			</div>

			{#if sessions.active_count === 0}
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
					<EmptyState title="No active sessions" description="Sessions will appear here when users start meetings." icon={Activity} />
				</div>
			{:else}
				<!-- Sessions Table -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					<table class="w-full">
						<thead class="bg-neutral-50 dark:bg-neutral-700">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Session</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">User</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Status</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Duration</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Cost</th>
								<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Actions</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each sessions.sessions as session (session.session_id)}
								<tr
									class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50 cursor-pointer transition-colors"
									onclick={() => openSessionDetail(session.session_id)}
								>
									<td class="px-6 py-4">
										<div class="text-sm font-mono text-neutral-900 dark:text-white truncate max-w-[200px]" title={session.session_id}>
											{session.session_id.slice(0, 8)}...
										</div>
									</td>
									<td class="px-6 py-4">
										<div class="flex items-center gap-2">
											<User class="w-4 h-4 text-neutral-400" />
											<span class="text-sm text-neutral-700 dark:text-neutral-300 truncate max-w-[150px]" title={session.user_id}>
												{session.user_id.slice(0, 12)}...
											</span>
										</div>
									</td>
									<td class="px-6 py-4">
										<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {
											session.status === 'running' ? 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-400' :
											session.status === 'active' ? 'bg-brand-100 text-brand-800 dark:bg-brand-900/30 dark:text-brand-400' :
											'bg-neutral-100 text-neutral-800 dark:bg-neutral-700 dark:text-neutral-300'
										}">
											{session.status}
											{#if session.phase}
												<span class="ml-1 text-neutral-500">({session.phase})</span>
											{/if}
										</span>
									</td>
									<td class="px-6 py-4">
										<span class="text-sm {session.duration_seconds > 600 ? 'text-warning-600 dark:text-warning-400 font-medium' : 'text-neutral-700 dark:text-neutral-300'}">
											{formatDuration(session.duration_seconds)}
										</span>
									</td>
									<td class="px-6 py-4">
										<span class="text-sm {(session.cost || 0) > 0.5 ? 'text-error-600 dark:text-error-400 font-medium' : 'text-neutral-700 dark:text-neutral-300'}">
											{formatCost(session.cost)}
										</span>
									</td>
									<td class="px-6 py-4 text-right">
										<Button
											variant="danger"
											size="sm"
											onclick={(e: MouseEvent) => { e.stopPropagation(); openSessionDetail(session.session_id); }}
										>
											Details
										</Button>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		{/if}
	</main>
</div>

<!-- Session Detail Modal -->
{#if showDetailModal && selectedSessionId}
	<SessionDetailModal
		sessionId={selectedSessionId}
		onclose={closeDetailModal}
		onkilled={loadSessions}
	/>
{/if}

<!-- Kill All Confirmation Modal -->
{#if showKillAllConfirm}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
		<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
			<div class="flex items-center gap-3 mb-4">
				<div class="p-2 bg-error-100 dark:bg-error-900/30 rounded-lg">
					<AlertTriangle class="w-6 h-6 text-error-600 dark:text-error-400" />
				</div>
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Kill All Sessions?</h2>
			</div>
			<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
				This will immediately terminate <strong>{sessions?.active_count}</strong> active sessions. This action cannot be undone.
			</p>
			<div class="mb-4">
				<label for="kill-reason" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
					Reason (required)
				</label>
				<input
					id="kill-reason"
					type="text"
					bind:value={killAllReason}
					placeholder="e.g., System maintenance"
					class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400"
				/>
			</div>
			<div class="flex justify-end gap-3">
				<Button variant="secondary" onclick={() => (showKillAllConfirm = false)}>
					Cancel
				</Button>
				<Button
					variant="danger"
					onclick={handleKillAll}
					disabled={!killAllReason.trim() || killingAll}
				>
					{killingAll ? 'Killing...' : 'Kill All Sessions'}
				</Button>
			</div>
		</div>
	</div>
{/if}
