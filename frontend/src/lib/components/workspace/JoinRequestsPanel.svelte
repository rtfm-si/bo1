<script lang="ts">
	/**
	 * JoinRequestsPanel - Admin panel for reviewing join requests
	 *
	 * Features:
	 * - View pending join requests
	 * - Approve or reject requests
	 * - Optional rejection reason
	 */
	import { UserPlus, Check, X, Clock, AlertCircle, CheckCircle, MessageSquare } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';
	import { apiClient } from '$lib/api/client';
	import type { JoinRequestResponse } from '$lib/api/types';

	import { formatDate } from '$lib/utils/time-formatting';
	interface Props {
		workspaceId: string;
		onRequestProcessed?: () => void;
	}

	let { workspaceId, onRequestProcessed }: Props = $props();

	// State
	let requests = $state<JoinRequestResponse[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);
	let processingId = $state<string | null>(null);

	// Rejection modal state
	let showRejectModal = $state(false);
	let rejectingRequest = $state<JoinRequestResponse | null>(null);
	let rejectionReason = $state('');

	// Load pending requests
	async function loadRequests() {
		try {
			const response = await apiClient.listJoinRequests(workspaceId);
			requests = response.requests;
			error = null;
		} catch (err) {
			console.error('Failed to load join requests:', err);
			error = 'Failed to load join requests';
		} finally {
			isLoading = false;
		}
	}

	// Approve request
	async function handleApprove(requestId: string) {
		if (processingId) return;

		processingId = requestId;
		error = null;
		success = null;

		try {
			await apiClient.approveJoinRequest(workspaceId, requestId);
			requests = requests.filter((r) => r.id !== requestId);
			success = 'Request approved. User has been added to the workspace.';
			onRequestProcessed?.();
		} catch (err: unknown) {
			console.error('Failed to approve request:', err);
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to approve request';
			}
		} finally {
			processingId = null;
		}
	}

	// Open reject modal
	function openRejectModal(request: JoinRequestResponse) {
		rejectingRequest = request;
		rejectionReason = '';
		showRejectModal = true;
	}

	// Close reject modal
	function closeRejectModal() {
		showRejectModal = false;
		rejectingRequest = null;
		rejectionReason = '';
	}

	// Confirm rejection
	async function handleReject() {
		if (!rejectingRequest || processingId) return;

		processingId = rejectingRequest.id;
		error = null;
		success = null;

		try {
			await apiClient.rejectJoinRequest(
				workspaceId,
				rejectingRequest.id,
				rejectionReason.trim() || undefined
			);
			requests = requests.filter((r) => r.id !== rejectingRequest!.id);
			success = 'Request rejected.';
			closeRejectModal();
			onRequestProcessed?.();
		} catch (err: unknown) {
			console.error('Failed to reject request:', err);
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to reject request';
			}
		} finally {
			processingId = null;
		}
	}


	// Load on mount
	$effect(() => {
		loadRequests();
	});
</script>

<div class="space-y-4">
	<!-- Success/Error Messages -->
	{#if success}
		<div class="flex items-center gap-2 p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-md">
			<CheckCircle size={18} class="text-success-600 dark:text-success-400" />
			<span class="text-sm text-success-700 dark:text-success-300">{success}</span>
		</div>
	{/if}

	{#if error}
		<div class="flex items-center gap-2 p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-md">
			<AlertCircle size={18} class="text-error-600 dark:text-error-400" />
			<span class="text-sm text-error-700 dark:text-error-300">{error}</span>
		</div>
	{/if}

	<!-- Pending Requests List -->
	<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
		<div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
			<h3 class="text-lg font-medium text-neutral-900 dark:text-white flex items-center gap-2">
				<UserPlus size={20} />
				Pending Join Requests
				{#if requests.length > 0}
					<span class="ml-2 px-2 py-0.5 text-xs font-medium bg-warning-100 text-warning-800 dark:bg-warning-900/30 dark:text-warning-300 rounded-full">
						{requests.length}
					</span>
				{/if}
			</h3>
		</div>

		{#if isLoading}
			<div class="p-8 text-center text-neutral-500 dark:text-neutral-400">
				Loading requests...
			</div>
		{:else if requests.length === 0}
			<div class="p-8 text-center text-neutral-500 dark:text-neutral-400">
				<Clock size={32} class="mx-auto mb-2 opacity-50" />
				<p>No pending join requests</p>
			</div>
		{:else}
			<ul class="divide-y divide-neutral-200 dark:divide-neutral-700">
				{#each requests as request (request.id)}
					<li class="p-4">
						<div class="flex items-start justify-between gap-4">
							<div class="flex-1 min-w-0">
								<p class="text-sm font-medium text-neutral-900 dark:text-white">
									{request.user_email || 'Unknown user'}
								</p>
								<p class="text-xs text-neutral-500 dark:text-neutral-400 flex items-center gap-1">
									<Clock size={12} />
									Requested {formatDate(request.created_at)}
								</p>

								{#if request.message}
									<div class="mt-2 p-2 bg-neutral-50 dark:bg-neutral-700/50 rounded text-sm text-neutral-700 dark:text-neutral-300">
										<div class="flex items-start gap-2">
											<MessageSquare size={14} class="mt-0.5 text-neutral-400 shrink-0" />
											<p class="line-clamp-2">{request.message}</p>
										</div>
									</div>
								{/if}
							</div>

							<!-- Action Buttons -->
							<div class="flex items-center gap-2 shrink-0">
								<Button
									variant="ghost"
									size="sm"
									onclick={() => openRejectModal(request)}
									disabled={processingId === request.id}
									class="text-error-600 hover:text-error-700 hover:bg-error-50 dark:text-error-400 dark:hover:text-error-300 dark:hover:bg-error-900/20"
								>
									<X size={16} class="mr-1" />
									Reject
								</Button>
								<Button
									size="sm"
									onclick={() => handleApprove(request.id)}
									disabled={processingId === request.id}
								>
									{#if processingId === request.id}
										Processing...
									{:else}
										<Check size={16} class="mr-1" />
										Approve
									{/if}
								</Button>
							</div>
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>

<!-- Reject Modal -->
{#if showRejectModal && rejectingRequest}
	<div
		class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
		onclick={closeRejectModal}
		role="presentation"
	>
		<!-- svelte-ignore a11y_click_events_have_key_events a11y_interactive_supports_focus -->
		<div
			class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">
					Reject Join Request
				</h3>
			</div>

			<div class="p-6 space-y-4">
				<p class="text-sm text-neutral-600 dark:text-neutral-400">
					Are you sure you want to reject the request from
					<strong class="text-neutral-900 dark:text-white">{rejectingRequest.user_email}</strong>?
				</p>

				<div>
					<label
						for="reject-reason"
						class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
					>
						Reason (optional)
					</label>
					<textarea
						id="reject-reason"
						bind:value={rejectionReason}
						placeholder="Let them know why their request was declined..."
						maxlength={500}
						rows={2}
						disabled={!!processingId}
						class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50 resize-none"
					></textarea>
					<p class="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
						This will be included in the notification email.
					</p>
				</div>

				<div class="flex justify-end gap-3 pt-2">
					<Button variant="ghost" onclick={closeRejectModal} disabled={!!processingId}>
						Cancel
					</Button>
					<Button
						variant="danger"
						onclick={handleReject}
						disabled={!!processingId}
					>
						{processingId ? 'Rejecting...' : 'Reject Request'}
					</Button>
				</div>
			</div>
		</div>
	</div>
{/if}
