<script lang="ts">
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import { Button } from '$lib/components/ui';
	import { Check, Clock, Mail, UserCheck, AlertCircle } from 'lucide-svelte';

	interface WaitlistEntry {
		id: string;
		email: string;
		status: string;
		source: string | null;
		notes: string | null;
		created_at: string;
	}

	let entries = $state<WaitlistEntry[]>([]);
	let totalCount = $state(0);
	let pendingCount = $state(0);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let statusFilter = $state<string>('pending');
	let approvingEmail = $state<string | null>(null);
	let approveResult = $state<{ email: string; message: string; success: boolean } | null>(null);

	async function loadWaitlist() {
		try {
			isLoading = true;
			error = null;
			const response = await apiClient.listWaitlist({
				status: statusFilter || undefined
			});
			entries = response.entries;
			totalCount = response.total_count;
			pendingCount = response.pending_count;
		} catch (err) {
			console.error('Failed to load waitlist:', err);
			error = err instanceof Error ? err.message : 'Failed to load waitlist';
		} finally {
			isLoading = false;
		}
	}

	async function approveEntry(email: string) {
		try {
			approvingEmail = email;
			approveResult = null;
			const result = await apiClient.approveWaitlistEntry(email);
			approveResult = {
				email: result.email,
				message: result.message,
				success: true
			};
			// Reload list to reflect changes
			await loadWaitlist();
		} catch (err) {
			console.error('Failed to approve entry:', err);
			approveResult = {
				email,
				message: err instanceof Error ? err.message : 'Failed to approve',
				success: false
			};
		} finally {
			approvingEmail = null;
		}
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'pending':
				return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';
			case 'invited':
				return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
			case 'converted':
				return 'bg-brand-100 text-brand-800 dark:bg-brand-900/30 dark:text-brand-300';
			default:
				return 'bg-neutral-100 text-neutral-800 dark:bg-neutral-700 dark:text-neutral-300';
		}
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

		if (diffDays === 0) {
			return 'Today';
		} else if (diffDays === 1) {
			return 'Yesterday';
		} else if (diffDays < 7) {
			return `${diffDays} days ago`;
		} else {
			return date.toLocaleDateString();
		}
	}

	onMount(() => {
		loadWaitlist();
	});
</script>

<svelte:head>
	<title>Waitlist - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center gap-4">
				<a
					href="/admin"
					class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
					aria-label="Back to admin"
				>
					<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
					</svg>
				</a>
				<div>
					<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
						Waitlist
					</h1>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">
						{pendingCount} pending &bull; {totalCount} total
					</p>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Approval Result Toast -->
		{#if approveResult}
			<div
				class="mb-6 p-4 rounded-lg flex items-start gap-3 {approveResult.success ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' : 'bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800'}"
			>
				{#if approveResult.success}
					<Check class="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
				{:else}
					<AlertCircle class="w-5 h-5 text-error-600 dark:text-error-400 flex-shrink-0 mt-0.5" />
				{/if}
				<div class="flex-1">
					<p class="font-medium {approveResult.success ? 'text-green-800 dark:text-green-200' : 'text-error-800 dark:text-error-200'}">
						{approveResult.success ? 'Approved!' : 'Error'}
					</p>
					<p class="text-sm {approveResult.success ? 'text-green-700 dark:text-green-300' : 'text-error-700 dark:text-error-300'}">
						{approveResult.message}
					</p>
				</div>
				<button
					onclick={() => approveResult = null}
					class="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
		{/if}

		<!-- Filter Tabs -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-1 mb-6 inline-flex">
			<button
				onclick={() => { statusFilter = 'pending'; loadWaitlist(); }}
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors {statusFilter === 'pending' ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
			>
				Pending ({pendingCount})
			</button>
			<button
				onclick={() => { statusFilter = 'invited'; loadWaitlist(); }}
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors {statusFilter === 'invited' ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
			>
				Invited
			</button>
			<button
				onclick={() => { statusFilter = ''; loadWaitlist(); }}
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors {statusFilter === '' ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
			>
				All
			</button>
		</div>

		{#if isLoading}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
				<div class="animate-spin w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full mx-auto"></div>
				<p class="mt-2 text-neutral-600 dark:text-neutral-400">Loading...</p>
			</div>
		{:else if error}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
				<p class="text-error-600 dark:text-error-400">{error}</p>
				<Button onclick={loadWaitlist} variant="ghost" class="mt-2">Retry</Button>
			</div>
		{:else if entries.length === 0}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
				<Mail class="w-12 h-12 text-neutral-400 mx-auto mb-2" />
				<p class="text-neutral-600 dark:text-neutral-400">
					{#if statusFilter === 'pending'}
						No pending requests
					{:else if statusFilter === 'invited'}
						No invited users yet
					{:else}
						Waitlist is empty
					{/if}
				</p>
			</div>
		{:else}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
				<div class="divide-y divide-neutral-200 dark:divide-neutral-700">
					{#each entries as entry (entry.id)}
						<div class="px-6 py-4 flex items-center justify-between hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-3">
									<p class="font-medium text-neutral-900 dark:text-white truncate">
										{entry.email}
									</p>
									<span class="px-2 py-0.5 text-xs font-medium rounded-full {getStatusColor(entry.status)}">
										{entry.status}
									</span>
								</div>
								<div class="flex items-center gap-4 mt-1 text-sm text-neutral-500 dark:text-neutral-400">
									<span class="flex items-center gap-1">
										<Clock class="w-3.5 h-3.5" />
										{formatDate(entry.created_at)}
									</span>
									{#if entry.source}
										<span>from {entry.source}</span>
									{/if}
								</div>
							</div>
							<div class="flex items-center gap-2 ml-4">
								{#if entry.status === 'pending'}
									<Button
										onclick={() => approveEntry(entry.email)}
										variant="brand"
										size="sm"
										disabled={approvingEmail === entry.email}
									>
										{#if approvingEmail === entry.email}
											<div class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></div>
											Approving...
										{:else}
											<UserCheck class="w-4 h-4 mr-2" />
											Approve
										{/if}
									</Button>
								{:else if entry.status === 'invited'}
									<span class="flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
										<Check class="w-4 h-4" />
										Approved
									</span>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</main>
</div>
