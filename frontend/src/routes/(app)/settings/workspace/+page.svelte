<script lang="ts">
	/**
	 * Workspace Settings Page - Manage current workspace details and members
	 */
	import { onMount } from 'svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { currentWorkspace, workspaces, refreshWorkspaces } from '$lib/stores/workspace';
	import { user } from '$lib/stores/auth';
	import { apiClient } from '$lib/api/client';
	import InvitationManager from '$lib/components/workspace/InvitationManager.svelte';
	import CreateWorkspaceModal from '$lib/components/workspace/CreateWorkspaceModal.svelte';
	import type { WorkspaceMemberResponse } from '$lib/api/types';

	let members = $state<WorkspaceMemberResponse[]>([]);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let showCreateModal = $state(false);
	let leaveConfirmOpen = $state(false);
	let isLeaving = $state(false);

	// Load members when workspace changes
	$effect(() => {
		if ($currentWorkspace) {
			loadMembers();
		} else {
			members = [];
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

	// Check if current user is owner
	const isOwner = $derived($currentWorkspace?.owner_id === $user?.id);
	const currentMember = $derived(members.find((m) => m.user_id === $user?.id));
	const isAdmin = $derived(currentMember?.role === 'admin' || currentMember?.role === 'owner');
</script>

<svelte:head>
	<title>Workspace Settings - Board of One</title>
</svelte:head>

<div class="space-y-6">
	<!-- Page Header -->
	<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
		<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-2">Workspace Settings</h2>
		<p class="text-slate-600 dark:text-slate-400">
			Manage your workspace, members, and team settings.
		</p>
	</div>

	{#if error}
		<Alert variant="error">{error}</Alert>
	{/if}

	{#if !$currentWorkspace}
		<!-- No workspace selected -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="text-center py-8">
				<div class="text-4xl mb-4">🏢</div>
				<h3 class="text-lg font-medium text-slate-900 dark:text-white mb-2">No Workspace Selected</h3>
				<p class="text-slate-600 dark:text-slate-400 mb-6">
					You're currently in Personal mode. Create or join a workspace to collaborate with others.
				</p>
				<Button variant="brand" onclick={() => (showCreateModal = true)}>
					Create Workspace
				</Button>
			</div>
		</div>

		{#if $workspaces.length > 0}
			<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
				<h3 class="text-lg font-medium text-slate-900 dark:text-white mb-4">Your Workspaces</h3>
				<ul class="divide-y divide-slate-200 dark:divide-slate-700">
					{#each $workspaces as workspace}
						<li class="py-3 flex items-center justify-between">
							<div>
								<p class="font-medium text-slate-900 dark:text-white">{workspace.name}</p>
								<p class="text-sm text-slate-500">/{workspace.slug}</p>
							</div>
							{#if workspace.member_count !== undefined}
								<span class="text-sm text-slate-500">
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
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="flex items-start justify-between mb-6">
				<div>
					<h3 class="text-lg font-medium text-slate-900 dark:text-white">{$currentWorkspace.name}</h3>
					<p class="text-sm text-slate-500 dark:text-slate-400">/{$currentWorkspace.slug}</p>
				</div>
				{#if isOwner}
					<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-200">
						Owner
					</span>
				{:else if isAdmin}
					<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">
						Admin
					</span>
				{:else}
					<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-200">
						Member
					</span>
				{/if}
			</div>

			<dl class="grid grid-cols-2 gap-4 text-sm">
				<div>
					<dt class="text-slate-500 dark:text-slate-400">Members</dt>
					<dd class="font-medium text-slate-900 dark:text-white">{members.length}</dd>
				</div>
				<div>
					<dt class="text-slate-500 dark:text-slate-400">Created</dt>
					<dd class="font-medium text-slate-900 dark:text-white">
						{new Date($currentWorkspace.created_at).toLocaleDateString()}
					</dd>
				</div>
			</dl>
		</div>

		<!-- Members List -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<h3 class="text-lg font-medium text-slate-900 dark:text-white mb-4">Members</h3>

			{#if isLoading}
				<div class="py-8 text-center">
					<div class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full mx-auto"></div>
				</div>
			{:else if members.length === 0}
				<p class="text-slate-500 py-4">No members found.</p>
			{:else}
				<ul class="divide-y divide-slate-200 dark:divide-slate-700">
					{#each members as member}
						<li class="py-3 flex items-center justify-between">
							<div>
								<p class="font-medium text-slate-900 dark:text-white">
									{member.user_email || member.user_id}
								</p>
								<p class="text-sm text-slate-500 capitalize">{member.role}</p>
							</div>
							<span class="text-sm text-slate-500">
								Joined {new Date(member.joined_at).toLocaleDateString()}
							</span>
						</li>
					{/each}
				</ul>
			{/if}
		</div>

		<!-- Invitation Manager (admin+) -->
		{#if isAdmin}
			<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
				<h3 class="text-lg font-medium text-slate-900 dark:text-white mb-4">Invitations</h3>
				<InvitationManager workspaceId={$currentWorkspace.id} />
			</div>
		{/if}

		<!-- Danger Zone -->
		{#if !isOwner}
			<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-red-200 dark:border-red-900 p-6">
				<h3 class="text-lg font-medium text-red-600 dark:text-red-400 mb-2">Danger Zone</h3>
				<p class="text-slate-600 dark:text-slate-400 mb-4">
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
