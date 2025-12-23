<script lang="ts">
	/**
	 * Workspace invitation accept page
	 * Shows invitation details and accept/decline options
	 */
	import { goto } from '$app/navigation';
	import { Users, Clock, Shield, CheckCircle, XCircle, AlertTriangle } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';
	import { apiClient } from '$lib/api/client';
	import type { InvitationResponse } from '$lib/api/types';

	interface Props {
		data: {
			invitation: InvitationResponse | null;
			token: string;
			error?: string;
		};
	}

	let { data }: Props = $props();

	let invitation = $state<InvitationResponse | null>(null);
	let error = $state<string | undefined>(undefined);
	let isAccepting = $state(false);

	// Sync state when data prop changes
	$effect(() => {
		invitation = data.invitation;
		error = data.error;
	});
	let isDeclining = $state(false);
	let actionResult = $state<'accepted' | 'declined' | null>(null);
	let actionError = $state<string | null>(null);

	// Format date for display
	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString(undefined, {
			weekday: 'long',
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}

	// Check if invitation is expired
	const isExpired = $derived.by(() => {
		if (!invitation) return true;
		return new Date(invitation.expires_at) < new Date();
	});

	// Days until expiry
	const daysUntilExpiry = $derived.by(() => {
		if (!invitation) return 0;
		const expires = new Date(invitation.expires_at);
		const now = new Date();
		return Math.ceil((expires.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
	});

	// Role display
	const roleDisplay = $derived.by(() => {
		if (!invitation) return '';
		return invitation.role.charAt(0).toUpperCase() + invitation.role.slice(1);
	});

	async function handleAccept() {
		if (!data.token) return;
		isAccepting = true;
		actionError = null;

		try {
			await apiClient.acceptInvitation(data.token);
			actionResult = 'accepted';
			// Redirect to dashboard after short delay
			setTimeout(() => {
				goto('/dashboard');
			}, 2000);
		} catch (err: unknown) {
			console.error('Failed to accept invitation:', err);
			if (err instanceof Error) {
				actionError = err.message;
			} else {
				actionError = 'Failed to accept invitation. Please try again.';
			}
		} finally {
			isAccepting = false;
		}
	}

	async function handleDecline() {
		if (!data.token) return;
		isDeclining = true;
		actionError = null;

		try {
			await apiClient.declineInvitation(data.token);
			actionResult = 'declined';
		} catch (err: unknown) {
			console.error('Failed to decline invitation:', err);
			if (err instanceof Error) {
				actionError = err.message;
			} else {
				actionError = 'Failed to decline invitation.';
			}
		} finally {
			isDeclining = false;
		}
	}
</script>

<svelte:head>
	<title>
		{invitation ? `Join ${invitation.workspace_name}` : 'Workspace Invitation'} | Board of One
	</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center p-4 bg-neutral-50 dark:bg-neutral-900">
	<div class="w-full max-w-md">
		<!-- Error State -->
		{#if error || !invitation}
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
				<div class="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
					<AlertTriangle class="w-8 h-8 text-red-600 dark:text-red-400" />
				</div>
				<h1 class="text-xl font-semibold text-neutral-900 dark:text-white mb-2">
					Invitation Not Found
				</h1>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6">
					{error || 'This invitation link may be invalid, expired, or already used.'}
				</p>
				<a href="/login" class="inline-flex items-center justify-center px-4 py-2 font-medium rounded-md bg-brand-600 text-white hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600">Go to Login</a>
			</div>

		<!-- Already Accepted -->
		{:else if actionResult === 'accepted'}
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
				<div class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 dark:bg-green-900/20 flex items-center justify-center">
					<CheckCircle class="w-8 h-8 text-green-600 dark:text-green-400" />
				</div>
				<h1 class="text-xl font-semibold text-neutral-900 dark:text-white mb-2">
					Welcome to {invitation.workspace_name}!
				</h1>
				<p class="text-neutral-600 dark:text-neutral-400 mb-2">
					You've joined the workspace as a {roleDisplay}.
				</p>
				<p class="text-sm text-neutral-500 dark:text-neutral-500">
					Redirecting to dashboard...
				</p>
			</div>

		<!-- Declined -->
		{:else if actionResult === 'declined'}
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
				<div class="w-16 h-16 mx-auto mb-4 rounded-full bg-neutral-100 dark:bg-neutral-700 flex items-center justify-center">
					<XCircle class="w-8 h-8 text-neutral-600 dark:text-neutral-400" />
				</div>
				<h1 class="text-xl font-semibold text-neutral-900 dark:text-white mb-2">
					Invitation Declined
				</h1>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6">
					You've declined the invitation to join {invitation.workspace_name}.
				</p>
				<a href="/dashboard" class="inline-flex items-center justify-center px-4 py-2 font-medium rounded-md bg-brand-600 text-white hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600">Go to Dashboard</a>
			</div>

		<!-- Expired -->
		{:else if isExpired}
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
				<div class="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-100 dark:bg-amber-900/20 flex items-center justify-center">
					<Clock class="w-8 h-8 text-amber-600 dark:text-amber-400" />
				</div>
				<h1 class="text-xl font-semibold text-neutral-900 dark:text-white mb-2">
					Invitation Expired
				</h1>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6">
					This invitation to join {invitation.workspace_name} has expired.
					Please ask for a new invitation.
				</p>
				<a href="/dashboard" class="inline-flex items-center justify-center px-4 py-2 font-medium rounded-md bg-brand-600 text-white hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600">Go to Dashboard</a>
			</div>

		<!-- Already Processed -->
		{:else if invitation.status !== 'pending'}
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
				<div class="w-16 h-16 mx-auto mb-4 rounded-full bg-neutral-100 dark:bg-neutral-700 flex items-center justify-center">
					<AlertTriangle class="w-8 h-8 text-neutral-600 dark:text-neutral-400" />
				</div>
				<h1 class="text-xl font-semibold text-neutral-900 dark:text-white mb-2">
					Invitation {invitation.status.charAt(0).toUpperCase() + invitation.status.slice(1)}
				</h1>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6">
					This invitation has already been {invitation.status}.
				</p>
				<a href="/dashboard" class="inline-flex items-center justify-center px-4 py-2 font-medium rounded-md bg-brand-600 text-white hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600">Go to Dashboard</a>
			</div>

		<!-- Valid Invitation -->
		{:else}
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
				<!-- Header -->
				<div class="bg-primary-600 dark:bg-primary-700 px-6 py-8 text-center">
					<div class="w-16 h-16 mx-auto mb-4 rounded-full bg-white/20 flex items-center justify-center">
						<Users class="w-8 h-8 text-white" />
					</div>
					<h1 class="text-xl font-semibold text-white">
						You're invited to join
					</h1>
					<p class="text-2xl font-bold text-white mt-1">
						{invitation.workspace_name}
					</p>
				</div>

				<!-- Details -->
				<div class="p-6 space-y-4">
					<!-- Inviter -->
					{#if invitation.inviter_name}
						<div class="flex items-center gap-3 text-neutral-600 dark:text-neutral-400">
							<Users size={18} />
							<span>Invited by <strong class="text-neutral-900 dark:text-white">{invitation.inviter_name}</strong></span>
						</div>
					{/if}

					<!-- Role -->
					<div class="flex items-center gap-3 text-neutral-600 dark:text-neutral-400">
						<Shield size={18} />
						<span>You'll join as <strong class="text-neutral-900 dark:text-white">{roleDisplay}</strong></span>
					</div>

					<!-- Expiry -->
					<div class="flex items-center gap-3 text-neutral-600 dark:text-neutral-400">
						<Clock size={18} />
						<span>
							{#if daysUntilExpiry <= 1}
								<span class="text-amber-600 dark:text-amber-400">Expires today</span>
							{:else if daysUntilExpiry <= 3}
								<span class="text-amber-600 dark:text-amber-400">Expires in {daysUntilExpiry} days</span>
							{:else}
								Expires {formatDate(invitation.expires_at)}
							{/if}
						</span>
					</div>

					<!-- Error -->
					{#if actionError}
						<div class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
							<p class="text-sm text-red-700 dark:text-red-300">{actionError}</p>
						</div>
					{/if}

					<!-- Actions -->
					<div class="flex gap-3 pt-4">
						<Button
							variant="outline"
							class="flex-1"
							onclick={handleDecline}
							disabled={isDeclining || isAccepting}
						>
							{isDeclining ? 'Declining...' : 'Decline'}
						</Button>
						<Button
							class="flex-1"
							onclick={handleAccept}
							disabled={isAccepting || isDeclining}
						>
							{isAccepting ? 'Accepting...' : 'Accept Invitation'}
						</Button>
					</div>

					<p class="text-xs text-center text-neutral-500 dark:text-neutral-500 mt-4">
						By accepting, you'll be added to this workspace and can collaborate with the team.
					</p>
				</div>
			</div>
		{/if}
	</div>
</div>
