<script lang="ts">
	/**
	 * Workspace Settings Page - Manage current workspace details and members
	 */
	import { onMount } from 'svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import { currentWorkspace, workspaces, refreshWorkspaces } from '$lib/stores/workspace';
	import { user } from '$lib/stores/auth';
	import { apiClient } from '$lib/api/client';
	import InvitationManager from '$lib/components/workspace/InvitationManager.svelte';
	import CreateWorkspaceModal from '$lib/components/workspace/CreateWorkspaceModal.svelte';
	import JoinRequestsPanel from '$lib/components/workspace/JoinRequestsPanel.svelte';
	import type { WorkspaceMemberResponse, WorkspaceDiscoverability, RoleChangeResponse } from '$lib/api/types';

	// Pre-read stores to ensure subscriptions happen outside reactive context
	$currentWorkspace;
	$workspaces;
	$user;

	let members = $state<WorkspaceMemberResponse[]>([]);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let showCreateModal = $state(false);
	let leaveConfirmOpen = $state(false);
	let isLeaving = $state(false);

	// Discoverability state
	let discoverability = $state<WorkspaceDiscoverability>('private');
	let isSavingDiscoverability = $state(false);
	let pendingRequestsCount = $state(0);

	// Role management state
	let showTransferModal = $state(false);
	let transferTargetId = $state<string | null>(null);
	let isTransferring = $state(false);
	let roleHistoryExpanded = $state(false);
	let roleHistory = $state<RoleChangeResponse[]>([]);
	let isLoadingHistory = $state(false);
	let isChangingRole = $state<string | null>(null);

	// Load members and pending requests when workspace changes
	$effect(() => {
		if ($currentWorkspace) {
			loadMembers();
			loadPendingRequestsCount();
		} else {
			members = [];
			pendingRequestsCount = 0;
		}
	});

	async function loadMembers() {
		if (!$currentWorkspace) return;

		isLoading = true;
		error = null;

		try {
			const response = await fetch(
				`${import.meta.env.VITE_API_URL || ''}/api/v1/workspaces/${$currentWorkspace.id}/members`,
				{ credentials: 'include' }
			);
			if (response.ok) {
				members = await response.json();
			} else {
				error = 'Failed to load members';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load members';
		} finally {
			isLoading = false;
		}
	}

	async function loadPendingRequestsCount() {
		if (!$currentWorkspace) return;

		try {
			const response = await apiClient.listJoinRequests($currentWorkspace.id);
			pendingRequestsCount = response.total;
		} catch {
			// Silently fail - user may not have admin access
			pendingRequestsCount = 0;
		}
	}

	async function handleDiscoverabilityChange(newValue: WorkspaceDiscoverability) {
		if (!$currentWorkspace || isSavingDiscoverability) return;

		isSavingDiscoverability = true;
		error = null;

		try {
			await apiClient.updateWorkspaceSettings($currentWorkspace.id, {
				discoverability: newValue
			});
			discoverability = newValue;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update discoverability';
		} finally {
			isSavingDiscoverability = false;
		}
	}

	function handleRequestProcessed() {
		loadPendingRequestsCount();
	}

	async function handleLeaveWorkspace() {
		if (!$currentWorkspace || !$user) return;

		isLeaving = true;
		try {
			await apiClient.leaveWorkspace($currentWorkspace.id, $user.id);
			await refreshWorkspaces();
			leaveConfirmOpen = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to leave workspace';
		} finally {
			isLeaving = false;
		}
	}

	function handleCreateSuccess() {
		showCreateModal = false;
	}

	// Role management functions
	async function handlePromote(userId: string) {
		if (!$currentWorkspace || isChangingRole) return;

		isChangingRole = userId;
		error = null;

		try {
			await apiClient.promoteMember($currentWorkspace.id, userId);
			await loadMembers();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to promote member';
		} finally {
			isChangingRole = null;
		}
	}

	async function handleDemote(userId: string) {
		if (!$currentWorkspace || isChangingRole) return;

		isChangingRole = userId;
		error = null;

		try {
			await apiClient.demoteMember($currentWorkspace.id, userId);
			await loadMembers();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to demote admin';
		} finally {
			isChangingRole = null;
		}
	}

	function openTransferModal(userId: string) {
		transferTargetId = userId;
		showTransferModal = true;
	}

	async function handleTransferOwnership() {
		if (!$currentWorkspace || !transferTargetId || isTransferring) return;

		isTransferring = true;
		error = null;

		try {
			await apiClient.transferWorkspaceOwnership($currentWorkspace.id, transferTargetId);
			await refreshWorkspaces();
			await loadMembers();
			showTransferModal = false;
			transferTargetId = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to transfer ownership';
		} finally {
			isTransferring = false;
		}
	}

	async function loadRoleHistory() {
		if (!$currentWorkspace || isLoadingHistory) return;

		isLoadingHistory = true;
		try {
			const response = await apiClient.getRoleHistory($currentWorkspace.id);
			roleHistory = response.changes;
		} catch {
			// Silently fail - user may not have admin access
			roleHistory = [];
		} finally {
			isLoadingHistory = false;
		}
	}

	function toggleRoleHistory() {
		roleHistoryExpanded = !roleHistoryExpanded;
		if (roleHistoryExpanded && roleHistory.length === 0) {
			loadRoleHistory();
		}
	}

	function formatRoleChange(change: RoleChangeResponse): string {
		const userLabel = change.user_email || change.user_id;
		switch (change.change_type) {
			case 'transfer_ownership':
				return change.new_role === 'owner'
					? `${userLabel} became owner`
					: `${userLabel} became admin (former owner)`;
			case 'promote':
				return `${userLabel} promoted to admin`;
			case 'demote':
				return `${userLabel} demoted to member`;
			default:
				return `${userLabel} role changed from ${change.old_role} to ${change.new_role}`;
		}
	}

	// Check if current user is owner
	const isOwner = $derived($currentWorkspace?.owner_id === $user?.id);
	const currentMember = $derived(members.find((m) => m.user_id === $user?.id));
	const isAdmin = $derived(currentMember?.role === 'admin' || currentMember?.role === 'owner');
	const transferTarget = $derived(members.find((m) => m.user_id === transferTargetId));
</script>

<svelte:head>
	<title>Workspace Settings - Board of One</title>
</svelte:head>

<div class="space-y-6">
	<!-- Page Header -->
	<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
		<h2 class="text-xl font-semibold text-neutral-900 dark:text-white mb-2">Workspace Settings</h2>
		<p class="text-neutral-600 dark:text-neutral-400">
			Manage your workspace, members, and team settings.
		</p>
	</div>

	{#if error}
		<Alert variant="error">{error}</Alert>
	{/if}

	{#if !$currentWorkspace}
		<!-- No workspace selected -->
		<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
			<div class="text-center py-8">
				<div class="text-4xl mb-4">🏢</div>
				<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-2">No Workspace Selected</h3>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6">
					You're currently in Personal mode. Create or join a workspace to collaborate with others.
				</p>
				<Button variant="brand" onclick={() => (showCreateModal = true)}>
					Create Workspace
				</Button>
			</div>
		</div>

		{#if $workspaces.length > 0}
			<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
				<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-4">Your Workspaces</h3>
				<ul class="divide-y divide-neutral-200 dark:divide-neutral-700">
					{#each $workspaces as workspace}
						<li class="py-3 flex items-center justify-between">
							<div>
								<p class="font-medium text-neutral-900 dark:text-white">{workspace.name}</p>
								<p class="text-sm text-neutral-500">/{workspace.slug}</p>
							</div>
							{#if workspace.member_count !== undefined}
								<span class="text-sm text-neutral-500">
									{workspace.member_count} member{workspace.member_count !== 1 ? 's' : ''}
								</span>
							{/if}
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	{:else}
		<!-- Current workspace details -->
		<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
			<div class="flex items-start justify-between mb-6">
				<div>
					<h3 class="text-lg font-medium text-neutral-900 dark:text-white">{$currentWorkspace.name}</h3>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">/{$currentWorkspace.slug}</p>
				</div>
				{#if isOwner}
					<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-200">
						Owner
					</span>
				{:else if isAdmin}
					<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200">
						Admin
					</span>
				{:else}
					<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-800 dark:bg-neutral-700 dark:text-neutral-200">
						Member
					</span>
				{/if}
			</div>

			<dl class="grid grid-cols-2 gap-4 text-sm">
				<div>
					<dt class="text-neutral-500 dark:text-neutral-400">Members</dt>
					<dd class="font-medium text-neutral-900 dark:text-white">{members.length}</dd>
				</div>
				<div>
					<dt class="text-neutral-500 dark:text-neutral-400">Created</dt>
					<dd class="font-medium text-neutral-900 dark:text-white">
						{new Date($currentWorkspace.created_at).toLocaleDateString()}
					</dd>
				</div>
			</dl>
		</div>

		<!-- Members List -->
		<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
			<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-4">Members</h3>

			{#if isLoading}
				<div class="py-8 text-center">
					<Spinner size="lg" class="mx-auto" />
				</div>
			{:else if members.length === 0}
				<p class="text-neutral-500 py-4">No members found.</p>
			{:else}
				<ul class="divide-y divide-neutral-200 dark:divide-neutral-700">
					{#each members as member}
						<li class="py-3 flex items-center justify-between gap-4">
							<div class="flex-1 min-w-0">
								<p class="font-medium text-neutral-900 dark:text-white truncate">
									{member.user_email || member.user_id}
								</p>
								<p class="text-sm text-neutral-500 capitalize">{member.role}</p>
							</div>
							<div class="flex items-center gap-2">
								<span class="text-sm text-neutral-500 hidden sm:inline">
									Joined {new Date(member.joined_at).toLocaleDateString()}
								</span>
								<!-- Role management actions (owner only) -->
								{#if isOwner && member.user_id !== $user?.id}
									{#if member.role === 'member'}
										<button
											onclick={() => handlePromote(member.user_id)}
											disabled={isChangingRole === member.user_id}
											class="px-2 py-1 text-xs font-medium text-brand-600 hover:text-brand-700 hover:bg-brand-50 dark:text-brand-400 dark:hover:text-brand-300 dark:hover:bg-brand-900/20 rounded transition-colors disabled:opacity-50"
										>
											{isChangingRole === member.user_id ? 'Promoting...' : 'Make Admin'}
										</button>
									{:else if member.role === 'admin'}
										<button
											onclick={() => handleDemote(member.user_id)}
											disabled={isChangingRole === member.user_id}
											class="px-2 py-1 text-xs font-medium text-warning-600 hover:text-warning-700 hover:bg-warning-50 dark:text-warning-400 dark:hover:text-warning-300 dark:hover:bg-warning-900/20 rounded transition-colors disabled:opacity-50"
										>
											{isChangingRole === member.user_id ? 'Demoting...' : 'Remove Admin'}
										</button>
										<button
											onclick={() => openTransferModal(member.user_id)}
											class="px-2 py-1 text-xs font-medium text-error-600 hover:text-error-700 hover:bg-error-50 dark:text-error-400 dark:hover:text-error-300 dark:hover:bg-error-900/20 rounded transition-colors"
										>
											Transfer Ownership
										</button>
									{/if}
								{/if}
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		</div>

		<!-- Invitation Manager (admin+) -->
		{#if isAdmin}
			<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
				<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-4">Invitations</h3>
				<InvitationManager workspaceId={$currentWorkspace.id} />
			</div>
		{/if}

		<!-- Discoverability Settings (admin+) -->
		{#if isAdmin}
			<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
				<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-2">Discoverability</h3>
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
					Control how users can find and join this workspace.
				</p>

				<div class="space-y-3">
					<label class="flex items-start gap-3 p-3 rounded-lg border border-neutral-200 dark:border-neutral-700 cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors {discoverability === 'private' ? 'ring-2 ring-brand-500 border-brand-500' : ''}">
						<input
							type="radio"
							name="discoverability"
							value="private"
							checked={discoverability === 'private'}
							onchange={() => handleDiscoverabilityChange('private')}
							disabled={isSavingDiscoverability}
							class="mt-1"
						/>
						<div>
							<p class="font-medium text-neutral-900 dark:text-white">Private</p>
							<p class="text-sm text-neutral-500 dark:text-neutral-400">
								Only invited members can join. Workspace is not discoverable.
							</p>
						</div>
					</label>

					<label class="flex items-start gap-3 p-3 rounded-lg border border-neutral-200 dark:border-neutral-700 cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors {discoverability === 'invite_only' ? 'ring-2 ring-brand-500 border-brand-500' : ''}">
						<input
							type="radio"
							name="discoverability"
							value="invite_only"
							checked={discoverability === 'invite_only'}
							onchange={() => handleDiscoverabilityChange('invite_only')}
							disabled={isSavingDiscoverability}
							class="mt-1"
						/>
						<div>
							<p class="font-medium text-neutral-900 dark:text-white">Invite Only</p>
							<p class="text-sm text-neutral-500 dark:text-neutral-400">
								Only invited members can join. Workspace is visible but not joinable.
							</p>
						</div>
					</label>

					<label class="flex items-start gap-3 p-3 rounded-lg border border-neutral-200 dark:border-neutral-700 cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors {discoverability === 'request_to_join' ? 'ring-2 ring-brand-500 border-brand-500' : ''}">
						<input
							type="radio"
							name="discoverability"
							value="request_to_join"
							checked={discoverability === 'request_to_join'}
							onchange={() => handleDiscoverabilityChange('request_to_join')}
							disabled={isSavingDiscoverability}
							class="mt-1"
						/>
						<div>
							<p class="font-medium text-neutral-900 dark:text-white">Request to Join</p>
							<p class="text-sm text-neutral-500 dark:text-neutral-400">
								Anyone can request to join. Admins must approve each request.
							</p>
						</div>
					</label>
				</div>

				{#if isSavingDiscoverability}
					<p class="text-sm text-neutral-500 mt-3">Saving...</p>
				{/if}
			</div>
		{/if}

		<!-- Join Requests (admin+) -->
		{#if isAdmin}
			<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-medium text-neutral-900 dark:text-white">Join Requests</h3>
					{#if pendingRequestsCount > 0}
						<span class="px-2 py-1 text-xs font-medium bg-warning-100 text-warning-800 dark:bg-warning-900/30 dark:text-warning-300 rounded-full">
							{pendingRequestsCount} pending
						</span>
					{/if}
				</div>
				<JoinRequestsPanel workspaceId={$currentWorkspace.id} onRequestProcessed={handleRequestProcessed} />
			</div>
		{/if}

		<!-- Billing (admin+) -->
		{#if isAdmin}
			<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
				<div class="flex items-center justify-between">
					<div>
						<h3 class="text-lg font-medium text-neutral-900 dark:text-white">Billing</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">
							Manage workspace subscription and billing
						</p>
					</div>
					<a
						href="/settings/workspace/billing"
						class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 transition-colors"
					>
						Manage Billing
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
					</a>
				</div>
			</div>
		{/if}

		<!-- Role History (admin+) -->
		{#if isAdmin}
			<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700">
				<button
					onclick={toggleRoleHistory}
					class="w-full p-6 flex items-center justify-between text-left"
				>
					<div>
						<h3 class="text-lg font-medium text-neutral-900 dark:text-white">Role History</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">
							View all role changes in this workspace
						</p>
					</div>
					<svg
						class="w-5 h-5 text-neutral-400 transition-transform {roleHistoryExpanded ? 'rotate-180' : ''}"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
				</button>

				{#if roleHistoryExpanded}
					<div class="px-6 pb-6 border-t border-neutral-200 dark:border-neutral-700 pt-4">
						{#if isLoadingHistory}
							<div class="py-4 text-center">
								<Spinner size="md" class="mx-auto" />
							</div>
						{:else if roleHistory.length === 0}
							<p class="text-neutral-500 text-sm py-2">No role changes recorded yet.</p>
						{:else}
							<ul class="space-y-2">
								{#each roleHistory as change}
									<li class="flex items-start justify-between gap-4 py-2 border-b border-neutral-100 dark:border-neutral-700/50 last:border-0">
										<div>
											<p class="text-sm text-neutral-900 dark:text-white">
												{formatRoleChange(change)}
											</p>
											{#if change.changed_by_email}
												<p class="text-xs text-neutral-500">
													by {change.changed_by_email}
												</p>
											{/if}
										</div>
										<span class="text-xs text-neutral-400 whitespace-nowrap">
											{new Date(change.changed_at).toLocaleDateString()}
										</span>
									</li>
								{/each}
							</ul>
						{/if}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Danger Zone -->
		{#if !isOwner}
			<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-error-200 dark:border-error-900 p-6">
				<h3 class="text-lg font-medium text-error-600 dark:text-error-400 mb-2">Danger Zone</h3>
				<p class="text-neutral-600 dark:text-neutral-400 mb-4">
					Leave this workspace. You will lose access to all workspace data.
				</p>

				{#if leaveConfirmOpen}
					<div class="flex items-center gap-3">
						<Button variant="danger" onclick={handleLeaveWorkspace} loading={isLeaving}>
							Confirm Leave
						</Button>
						<Button variant="ghost" onclick={() => (leaveConfirmOpen = false)} disabled={isLeaving}>
							Cancel
						</Button>
					</div>
				{:else}
					<Button variant="outline" onclick={() => (leaveConfirmOpen = true)}>
						Leave Workspace
					</Button>
				{/if}
			</div>
		{/if}
	{/if}
</div>

<!-- Create Workspace Modal -->
<CreateWorkspaceModal bind:open={showCreateModal} onsuccess={handleCreateSuccess} />

<!-- Transfer Ownership Modal -->
{#if showTransferModal && transferTarget}
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
		<div class="bg-white dark:bg-neutral-800 rounded-xl shadow-xl max-w-md w-full p-6">
			<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
				Transfer Ownership
			</h3>
			<div class="space-y-4">
				<Alert variant="warning">
					You are about to transfer ownership of this workspace to <strong>{transferTarget.user_email || transferTarget.user_id}</strong>. This action cannot be undone.
				</Alert>
				<p class="text-sm text-neutral-600 dark:text-neutral-400">
					After the transfer:
				</p>
				<ul class="text-sm text-neutral-600 dark:text-neutral-400 list-disc list-inside space-y-1">
					<li>You will become an Admin</li>
					<li>The new owner will have full control</li>
					<li>Only the new owner can transfer ownership again</li>
				</ul>
			</div>
			<div class="flex items-center justify-end gap-3 mt-6">
				<Button
					variant="ghost"
					onclick={() => {
						showTransferModal = false;
						transferTargetId = null;
					}}
					disabled={isTransferring}
				>
					Cancel
				</Button>
				<Button
					variant="danger"
					onclick={handleTransferOwnership}
					loading={isTransferring}
				>
					Transfer Ownership
				</Button>
			</div>
		</div>
	</div>
{/if}
