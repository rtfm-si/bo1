<script lang="ts">
	/**
	 * ShareModal - Modal for creating and managing session share links
	 *
	 * Features:
	 * - TTL selector (7/30/90/365 days)
	 * - Create share link button
	 * - Copy URL to clipboard
	 * - List active shares with revoke
	 */
	import { untrack } from 'svelte';
	import { Copy, Check, Trash2, Link, Clock, AlertCircle } from 'lucide-svelte';
	import { Modal, Button, Alert } from '$lib/components/ui';
	import { apiClient, ApiClientError } from '$lib/api/client';

	interface Props {
		sessionId: string;
		open: boolean;
		onClose: () => void;
	}

	let { sessionId, open = $bindable(), onClose }: Props = $props();

	// State
	let ttlDays = $state(7);
	let isCreating = $state(false);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let copiedToken = $state<string | null>(null);
	let shares = $state<Array<{
		token: string;
		expires_at: string;
		created_at: string;
		is_active: boolean;
	}>>([]);

	const ttlOptions = [
		{ value: 7, label: '7 days' },
		{ value: 30, label: '30 days' },
		{ value: 90, label: '90 days' },
		{ value: 365, label: '1 year' },
	];

	async function loadShares() {
		isLoading = true;
		error = null;
		try {
			const response = await apiClient.listShares(sessionId);
			shares = response.shares.filter(s => s.is_active);
		} catch (err) {
			console.error('Failed to load shares:', err);
			error = err instanceof ApiClientError ? err.message : 'Failed to load shares';
		} finally {
			isLoading = false;
		}
	}

	async function createShare() {
		isCreating = true;
		error = null;
		try {
			const response = await apiClient.createShare(sessionId, ttlDays);
			shares = [...shares, {
				token: response.token,
				expires_at: response.expires_at,
				created_at: new Date().toISOString(),
				is_active: true,
			}];
		} catch (err) {
			console.error('Failed to create share:', err);
			error = err instanceof ApiClientError ? err.message : 'Failed to create share link';
		} finally {
			isCreating = false;
		}
	}

	async function revokeShare(token: string) {
		try {
			await apiClient.revokeShare(sessionId, token);
			shares = shares.filter(s => s.token !== token);
		} catch (err) {
			console.error('Failed to revoke share:', err);
			error = err instanceof ApiClientError ? err.message : 'Failed to revoke share';
		}
	}

	function getShareUrl(token: string): string {
		if (typeof window !== 'undefined') {
			return `${window.location.origin}/share/${token}`;
		}
		return `/share/${token}`;
	}

	async function copyToClipboard(token: string) {
		const url = getShareUrl(token);
		try {
			await navigator.clipboard.writeText(url);
			copiedToken = token;
			setTimeout(() => {
				if (copiedToken === token) copiedToken = null;
			}, 2000);
		} catch (err) {
			console.error('Failed to copy:', err);
		}
	}

	function formatExpiryDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString(undefined, {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
		});
	}

	function getDaysUntilExpiry(dateString: string): number {
		const now = new Date();
		const expiry = new Date(dateString);
		const diff = expiry.getTime() - now.getTime();
		return Math.ceil(diff / (1000 * 60 * 60 * 24));
	}

	$effect(() => {
		if (open) {
			untrack(() => {
				loadShares();
			});
		}
	});
</script>

<Modal {open} title="Share Meeting" size="md" onclose={onClose}>
	{#snippet children()}
		<div class="space-y-6">
			{#if error}
				<Alert variant="error">
					<AlertCircle size={16} />
					<span>{error}</span>
				</Alert>
			{/if}

			<!-- Create New Share -->
			<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 space-y-4">
				<h3 class="text-sm font-medium text-neutral-900 dark:text-neutral-100">
					Create Share Link
				</h3>

				<div class="flex flex-col sm:flex-row gap-3">
					<div class="flex-1">
						<label for="ttl-select" class="sr-only">Expiration</label>
						<select
							id="ttl-select"
							bind:value={ttlDays}
							class="w-full px-3 py-2 bg-white dark:bg-neutral-700 border border-neutral-300 dark:border-neutral-600 rounded-lg text-sm text-neutral-900 dark:text-neutral-100 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
						>
							{#each ttlOptions as option (option.value)}
								<option value={option.value}>{option.label}</option>
							{/each}
						</select>
					</div>

					<Button
						variant="brand"
						size="md"
						onclick={createShare}
						disabled={isCreating}
					>
						<Link size={16} />
						<span>{isCreating ? 'Creating...' : 'Create Link'}</span>
					</Button>
				</div>
			</div>

			<!-- Active Shares List -->
			<div>
				<h3 class="text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-3">
					Active Share Links
				</h3>

				{#if isLoading}
					<div class="text-center py-6 text-neutral-500 dark:text-neutral-400">
						Loading...
					</div>
				{:else if shares.length === 0}
					<div class="text-center py-6 text-neutral-500 dark:text-neutral-400 bg-neutral-50 dark:bg-neutral-800 rounded-lg">
						<p class="text-sm">No active share links</p>
						<p class="text-xs mt-1">Create one above to share this meeting</p>
					</div>
				{:else}
					<ul class="divide-y divide-neutral-200 dark:divide-neutral-700 border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden">
						{#each shares as share (share.token)}
							{@const daysLeft = getDaysUntilExpiry(share.expires_at)}
							<li class="p-3 bg-white dark:bg-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-750">
								<div class="flex items-center justify-between gap-3">
									<div class="flex-1 min-w-0">
										<p class="text-sm font-mono text-neutral-700 dark:text-neutral-300 truncate">
											{getShareUrl(share.token)}
										</p>
										<div class="flex items-center gap-2 mt-1">
											<Clock size={12} class="text-neutral-400" />
											<span class="text-xs text-neutral-500 dark:text-neutral-400">
												{#if daysLeft > 0}
													Expires in {daysLeft} day{daysLeft === 1 ? '' : 's'}
												{:else}
													Expired
												{/if}
												({formatExpiryDate(share.expires_at)})
											</span>
										</div>
									</div>

									<div class="flex items-center gap-1">
										<button
											type="button"
											class="p-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-600 dark:text-neutral-400 transition-colors"
											onclick={() => copyToClipboard(share.token)}
											aria-label="Copy link"
											title="Copy link"
										>
											{#if copiedToken === share.token}
												<Check size={16} class="text-success-600" />
											{:else}
												<Copy size={16} />
											{/if}
										</button>

										<button
											type="button"
											class="p-2 rounded-lg hover:bg-error-50 dark:hover:bg-error-900/20 text-neutral-600 dark:text-neutral-400 hover:text-error-600 dark:hover:text-error-400 transition-colors"
											onclick={() => revokeShare(share.token)}
											aria-label="Revoke share"
											title="Revoke share"
										>
											<Trash2 size={16} />
										</button>
									</div>
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			<!-- Info -->
			<p class="text-xs text-neutral-500 dark:text-neutral-400">
				Anyone with the link can view the meeting summary. They won't need to sign in.
			</p>
		</div>
	{/snippet}

	{#snippet footer()}
		<div class="flex justify-end">
			<Button variant="secondary" size="md" onclick={onClose}>
				Close
			</Button>
		</div>
	{/snippet}
</Modal>
