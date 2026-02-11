<script lang="ts">
	/**
	 * InvitationManager - Manage workspace invitations
	 *
	 * Features:
	 * - Send invitations by email
	 * - View pending invitations
	 * - Revoke pending invitations
	 */
	import { Mail, UserPlus, Clock, Trash2, Shield, AlertCircle, CheckCircle } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';
	import { apiClient } from '$lib/api/client';
	import type { InvitationResponse, MemberRole } from '$lib/api/types';

	import { formatDate } from '$lib/utils/time-formatting';
	interface Props {
		workspaceId: string;
		canInvite?: boolean;
	}

	let { workspaceId, canInvite = true }: Props = $props();

	// State
	let invitations = $state<InvitationResponse[]>([]);
	let isLoading = $state(true);
	let isSending = $state(false);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);

	// Form state
	let emailInput = $state('');
	let selectedRole = $state<'admin' | 'member'>('member');

	// Load invitations
	async function loadInvitations() {
		try {
			const response = await apiClient.listWorkspaceInvitations(workspaceId);
			invitations = response.invitations;
			error = null;
		} catch (err) {
			console.error('Failed to load invitations:', err);
			error = 'Failed to load invitations';
		} finally {
			isLoading = false;
		}
	}

	// Send invitation
	async function handleSendInvitation(e: Event) {
		e.preventDefault();
		if (!emailInput.trim()) return;

		isSending = true;
		error = null;
		success = null;

		try {
			await apiClient.sendWorkspaceInvitation(workspaceId, emailInput.trim(), selectedRole);
			success = `Invitation sent to ${emailInput}`;
			emailInput = '';
			selectedRole = 'member';
			await loadInvitations();
		} catch (err: unknown) {
			console.error('Failed to send invitation:', err);
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'Failed to send invitation';
			}
		} finally {
			isSending = false;
		}
	}

	// Revoke invitation
	async function handleRevoke(invitationId: string) {
		if (!confirm('Are you sure you want to revoke this invitation?')) return;

		try {
			await apiClient.revokeInvitation(workspaceId, invitationId);
			invitations = invitations.filter((inv) => inv.id !== invitationId);
			success = 'Invitation revoked';
		} catch (err) {
			console.error('Failed to revoke invitation:', err);
			error = 'Failed to revoke invitation';
		}
	}


	// Days until expiry
	function daysUntilExpiry(expiresAt: string): number {
		const expires = new Date(expiresAt);
		const now = new Date();
		return Math.ceil((expires.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
	}

	// Role badge color
	function getRoleBadgeClass(role: MemberRole): string {
		switch (role) {
			case 'admin':
				return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300';
			case 'member':
			default:
				return 'bg-neutral-100 text-neutral-800 dark:bg-neutral-700 dark:text-neutral-300';
		}
	}

	// Load on mount
	$effect(() => {
		loadInvitations();
	});
</script>

<div class="space-y-6">
	<!-- Send Invitation Form -->
	{#if canInvite}
		<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
			<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-4 flex items-center gap-2">
				<UserPlus size={20} />
				Invite Team Member
			</h3>

			<form onsubmit={handleSendInvitation} class="space-y-4">
				<div class="flex gap-3">
					<div class="flex-1">
						<label for="email" class="sr-only">Email address</label>
						<div class="relative">
							<Mail
								size={18}
								class="absolute left-3 top-1/2 -tranneutral-y-1/2 text-neutral-400"
							/>
							<input
								id="email"
								type="email"
								placeholder="colleague@company.com"
								bind:value={emailInput}
								required
								disabled={isSending}
								class="w-full pl-10 pr-4 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
							/>
						</div>
					</div>

					<div>
						<label for="role" class="sr-only">Role</label>
						<select
							id="role"
							bind:value={selectedRole}
							disabled={isSending}
							class="h-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
						>
							<option value="member">Member</option>
							<option value="admin">Admin</option>
						</select>
					</div>

					<Button type="submit" disabled={isSending || !emailInput.trim()}>
						{isSending ? 'Sending...' : 'Send Invite'}
					</Button>
				</div>

				<p class="text-xs text-neutral-500 dark:text-neutral-400">
					Invitations expire after 7 days. The recipient will receive an email with a link to join.
				</p>
			</form>
		</div>
	{/if}

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

	<!-- Pending Invitations List -->
	<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
		<div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
			<h3 class="text-lg font-medium text-neutral-900 dark:text-white flex items-center gap-2">
				<Clock size={20} />
				Pending Invitations
				{#if invitations.length > 0}
					<span class="ml-auto text-sm font-normal text-neutral-500 dark:text-neutral-400">
						{invitations.length} pending
					</span>
				{/if}
			</h3>
		</div>

		{#if isLoading}
			<div class="p-8 text-center text-neutral-500 dark:text-neutral-400">
				Loading invitations...
			</div>
		{:else if invitations.length === 0}
			<div class="p-8 text-center text-neutral-500 dark:text-neutral-400">
				<Mail size={32} class="mx-auto mb-2 opacity-50" />
				<p>No pending invitations</p>
			</div>
		{:else}
			<ul class="divide-y divide-neutral-200 dark:divide-neutral-700">
				{#each invitations as invitation (invitation.id)}
					<li class="px-4 py-3 flex items-center gap-4">
						<!-- Email -->
						<div class="flex-1 min-w-0">
							<p class="text-sm font-medium text-neutral-900 dark:text-white truncate">
								{invitation.email}
							</p>
							<p class="text-xs text-neutral-500 dark:text-neutral-400">
								Sent {formatDate(invitation.created_at)}
								{#if invitation.inviter_name}
									by {invitation.inviter_name}
								{/if}
							</p>
						</div>

						<!-- Role Badge -->
						<span
							class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full {getRoleBadgeClass(invitation.role)}"
						>
							<Shield size={12} />
							{invitation.role.charAt(0).toUpperCase() + invitation.role.slice(1)}
						</span>

						<!-- Expiry -->
						<span
							class="text-xs whitespace-nowrap"
							class:text-warning-600={daysUntilExpiry(invitation.expires_at) <= 2}
							class:dark:text-warning-400={daysUntilExpiry(invitation.expires_at) <= 2}
							class:text-neutral-500={daysUntilExpiry(invitation.expires_at) > 2}
							class:dark:text-neutral-400={daysUntilExpiry(invitation.expires_at) > 2}
						>
							{#if daysUntilExpiry(invitation.expires_at) <= 0}
								Expired
							{:else if daysUntilExpiry(invitation.expires_at) === 1}
								Expires today
							{:else}
								{daysUntilExpiry(invitation.expires_at)}d left
							{/if}
						</span>

						<!-- Revoke Button -->
						{#if canInvite}
							<Button
								variant="ghost"
								size="sm"
								onclick={() => handleRevoke(invitation.id)}
								ariaLabel="Revoke invitation"
								class="text-neutral-500 hover:text-error-600 dark:text-neutral-400 dark:hover:text-error-400"
							>
								<Trash2 size={16} />
							</Button>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>
