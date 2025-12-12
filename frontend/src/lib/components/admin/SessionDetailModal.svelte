<script lang="ts">
	import { onMount } from 'svelte';
	import { X, Skull, RefreshCw, Clock, DollarSign, User, Activity } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { adminApi, type FullSessionResponse } from '$lib/api/admin';

	interface Props {
		sessionId: string;
		onclose: () => void;
		onkilled: () => void;
	}

	let { sessionId, onclose, onkilled }: Props = $props();

	let session = $state<FullSessionResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let killing = $state(false);
	let showKillConfirm = $state(false);
	let killReason = $state('');

	async function loadSession() {
		try {
			loading = true;
			session = await adminApi.getSessionFull(sessionId);
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load session';
		} finally {
			loading = false;
		}
	}

	async function handleKill() {
		if (!killReason.trim()) return;
		try {
			killing = true;
			await adminApi.killSession(sessionId, killReason);
			onkilled();
			onclose();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to kill session';
		} finally {
			killing = false;
		}
	}

	function formatDuration(startedAt: string | undefined): string {
		if (!startedAt) return '-';
		const start = new Date(startedAt);
		const now = new Date();
		const seconds = (now.getTime() - start.getTime()) / 1000;
		if (seconds < 60) return `${Math.round(seconds)}s`;
		if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
		const hours = Math.floor(seconds / 3600);
		const mins = Math.floor((seconds % 3600) / 60);
		return `${hours}h ${mins}m`;
	}

	function formatCost(cost: unknown): string {
		if (typeof cost !== 'number') return '-';
		return `$${cost.toFixed(4)}`;
	}

	onMount(() => {
		loadSession();
	});
</script>

<!-- Modal Backdrop -->
<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
	onclick={onclose}
	onkeydown={(e) => e.key === 'Escape' && onclose()}
	role="dialog"
	aria-modal="true"
	tabindex="-1"
>
	<!-- Modal Content -->
	<div
		class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col"
		onclick={(e) => e.stopPropagation()}
		onkeydown={(e) => e.stopPropagation()}
		role="document"
	>
		<!-- Header -->
		<div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
			<div class="flex items-center gap-3">
				<Activity class="w-5 h-5 text-brand-600 dark:text-brand-400" />
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Session Details</h2>
			</div>
			<button
				onclick={onclose}
				class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
				aria-label="Close"
			>
				<X class="w-5 h-5 text-neutral-500" />
			</button>
		</div>

		<!-- Body -->
		<div class="flex-1 overflow-y-auto p-6">
			{#if error}
				<Alert variant="error" class="mb-4">{error}</Alert>
			{/if}

			{#if loading}
				<div class="flex items-center justify-center py-12">
					<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
				</div>
			{:else if session}
				<!-- Session Info Grid -->
				<div class="grid grid-cols-2 gap-4 mb-6">
					<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-4">
						<p class="text-xs text-neutral-500 dark:text-neutral-400 uppercase mb-1">Session ID</p>
						<p class="text-sm font-mono text-neutral-900 dark:text-white break-all">{session.session_id}</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-4">
						<p class="text-xs text-neutral-500 dark:text-neutral-400 uppercase mb-1">Status</p>
						<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {
							session.is_active ? 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-400' :
							'bg-neutral-100 text-neutral-800 dark:bg-neutral-600 dark:text-neutral-300'
						}">
							{session.is_active ? 'Active' : 'Inactive'}
						</span>
					</div>
				</div>

				<!-- Metadata -->
				<div class="mb-6">
					<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">Metadata</h3>
					<div class="grid grid-cols-2 gap-3">
						<div class="flex items-center gap-2 text-sm">
							<User class="w-4 h-4 text-neutral-400" />
							<span class="text-neutral-600 dark:text-neutral-400">User:</span>
							<span class="text-neutral-900 dark:text-white truncate">{session.metadata.user_id || '-'}</span>
						</div>
						<div class="flex items-center gap-2 text-sm">
							<Activity class="w-4 h-4 text-neutral-400" />
							<span class="text-neutral-600 dark:text-neutral-400">Phase:</span>
							<span class="text-neutral-900 dark:text-white">{session.metadata.phase || '-'}</span>
						</div>
						<div class="flex items-center gap-2 text-sm">
							<Clock class="w-4 h-4 text-neutral-400" />
							<span class="text-neutral-600 dark:text-neutral-400">Duration:</span>
							<span class="text-neutral-900 dark:text-white">{formatDuration(session.metadata.started_at as string | undefined)}</span>
						</div>
						<div class="flex items-center gap-2 text-sm">
							<DollarSign class="w-4 h-4 text-neutral-400" />
							<span class="text-neutral-600 dark:text-neutral-400">Cost:</span>
							<span class="text-neutral-900 dark:text-white">{formatCost(session.metadata.cost)}</span>
						</div>
					</div>
				</div>

				<!-- Problem Statement -->
				{#if session.metadata.problem_statement}
					<div class="mb-6">
						<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Problem Statement</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400 bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-3">
							{session.metadata.problem_statement}
						</p>
					</div>
				{/if}

				<!-- State Summary -->
				{#if session.state}
					<div class="mb-6">
						<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">State</h3>
						<details class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg">
							<summary class="px-3 py-2 cursor-pointer text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white">
								View raw state ({Object.keys(session.state).length} keys)
							</summary>
							<pre class="px-3 py-2 text-xs font-mono text-neutral-700 dark:text-neutral-300 overflow-x-auto max-h-48">{JSON.stringify(session.state, null, 2)}</pre>
						</details>
					</div>
				{/if}
			{/if}
		</div>

		<!-- Footer -->
		<div class="flex items-center justify-between px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
			<Button variant="secondary" onclick={onclose}>Close</Button>
			{#if session?.is_active}
				{#if showKillConfirm}
					<div class="flex items-center gap-2">
						<input
							type="text"
							bind:value={killReason}
							placeholder="Reason for killing..."
							class="px-3 py-1.5 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
						/>
						<Button variant="secondary" size="sm" onclick={() => (showKillConfirm = false)}>Cancel</Button>
						<Button variant="danger" size="sm" onclick={handleKill} disabled={!killReason.trim() || killing}>
							{killing ? 'Killing...' : 'Confirm Kill'}
						</Button>
					</div>
				{:else}
					<Button variant="danger" onclick={() => (showKillConfirm = true)}>
						<Skull class="w-4 h-4" />
						Kill Session
					</Button>
				{/if}
			{/if}
		</div>
	</div>
</div>
