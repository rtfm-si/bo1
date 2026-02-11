<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { enhance } from '$app/forms';
	import { Button, Spinner } from '$lib/components/ui';
	import { Check, Clock, Mail, UserCheck, AlertCircle } from 'lucide-svelte';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';

	import { formatDate } from '$lib/utils/time-formatting';
	interface WaitlistEntry {
		id: string;
		email: string;
		status: string;
		source: string | null;
		notes: string | null;
		created_at: string;
	}

	let { data, form } = $props();

	let entries = $state<WaitlistEntry[]>([]);
	let totalCount = $state(0);
	let pendingCount = $state(0);
	let statusFilter = $state<string>('pending');
	let approvingEmail = $state<string | null>(null);
	let approveResult = $state<{ email: string; message: string; success: boolean } | null>(null);

	// Update local state when data changes
	$effect(() => {
		entries = data.entries || [];
		totalCount = data.totalCount || 0;
		pendingCount = data.pendingCount || 0;
		statusFilter = data.statusFilter || 'pending';

		// Show approve result if form action succeeded
		if (form?.success) {
			approveResult = {
				email: form.email,
				message: form.message,
				success: true
			};
		} else if (form?.error) {
			approveResult = {
				email: '',
				message: form.error,
				success: false
			};
		}
	});

	function changeFilter(newStatus: string) {
		const url = new URL($page.url);
		if (newStatus) {
			url.searchParams.set('status', newStatus);
		} else {
			url.searchParams.delete('status');
		}
		goto(url.toString());
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'pending':
				return 'bg-warning-100 text-warning-800 dark:bg-warning-900/30 dark:text-warning-300';
			case 'invited':
				return 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-300';
			case 'converted':
				return 'bg-brand-100 text-brand-800 dark:bg-brand-900/30 dark:text-brand-300';
			default:
				return 'bg-neutral-100 text-neutral-800 dark:bg-neutral-700 dark:text-neutral-300';
		}
	}

</script>

<svelte:head>
	<title>Waitlist - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="Waitlist">
		{#snippet badge()}
			<span class="text-sm text-neutral-500 dark:text-neutral-400">
				{pendingCount} pending &bull; {totalCount} total
			</span>
		{/snippet}
	</AdminPageHeader>

	<!-- Main Content -->
	<main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Approval Result Toast -->
		{#if approveResult}
			<div
				class="mb-6 p-4 rounded-lg flex items-start gap-3 {approveResult.success ? 'bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800' : 'bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800'}"
			>
				{#if approveResult.success}
					<Check class="w-5 h-5 text-success-600 dark:text-success-400 flex-shrink-0 mt-0.5" />
				{:else}
					<AlertCircle class="w-5 h-5 text-error-600 dark:text-error-400 flex-shrink-0 mt-0.5" />
				{/if}
				<div class="flex-1">
					<p class="font-medium {approveResult.success ? 'text-success-800 dark:text-success-200' : 'text-error-800 dark:text-error-200'}">
						{approveResult.success ? 'Approved!' : 'Error'}
					</p>
					<p class="text-sm {approveResult.success ? 'text-success-700 dark:text-success-300' : 'text-error-700 dark:text-error-300'}">
						{approveResult.message}
					</p>
				</div>
				<button
					onclick={() => approveResult = null}
					class="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
					aria-label="Dismiss notification"
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
				onclick={() => changeFilter('pending')}
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors {statusFilter === 'pending' ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
			>
				Pending ({pendingCount})
			</button>
			<button
				onclick={() => changeFilter('invited')}
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors {statusFilter === 'invited' ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
			>
				Invited
			</button>
			<button
				onclick={() => changeFilter('')}
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors {statusFilter === '' ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'}"
			>
				All
			</button>
		</div>

		{#if entries.length === 0}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
				<EmptyState
					title={statusFilter === 'pending'
						? 'No pending requests'
						: statusFilter === 'invited'
							? 'No invited users yet'
							: 'Waitlist is empty'}
					icon={Mail}
				/>
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
									<form
										method="POST"
										action="?/approve"
										use:enhance={() => {
											approvingEmail = entry.email;
											return async ({ update }) => {
												approvingEmail = null;
												await update();
											};
										}}
									>
										<input type="hidden" name="email" value={entry.email} />
										<Button
											type="submit"
											variant="brand"
											size="sm"
											disabled={approvingEmail === entry.email}
										>
											{#snippet children()}
												{#if approvingEmail === entry.email}
													<Spinner size="xs" variant="neutral" ariaLabel="Approving" />
													Approving...
												{:else}
													<UserCheck class="w-4 h-4 mr-2" />
													Approve
												{/if}
											{/snippet}
										</Button>
									</form>
								{:else if entry.status === 'invited'}
									<span class="flex items-center gap-1 text-sm text-success-600 dark:text-success-400">
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
