<script lang="ts">
	/**
	 * WorkspaceSwitcher Component - Dropdown for switching between workspaces
	 * Shows current workspace name and allows switching or creating new workspaces
	 */
	import { beforeNavigate } from '$app/navigation';
	import { Building2, ChevronDown, Check, Plus, User } from 'lucide-svelte';
	import {
		workspaces,
		currentWorkspace,
		switchWorkspace,
		isWorkspaceLoading
	} from '$lib/stores/workspace';
	import type { WorkspaceResponse } from '$lib/api/types';

	interface Props {
		onCreateWorkspace?: () => void;
	}

	let { onCreateWorkspace }: Props = $props();

	let isOpen = $state(false);
	let closeTimeout: ReturnType<typeof setTimeout> | null = null;

	// Pre-read stores to ensure subscriptions happen outside reactive context
	$currentWorkspace;
	$workspaces;
	$isWorkspaceLoading;

	// Current display name
	const displayName = $derived($currentWorkspace?.name || 'Personal');

	function openDropdown() {
		if (closeTimeout) {
			clearTimeout(closeTimeout);
			closeTimeout = null;
		}
		isOpen = true;
	}

	function closeDropdown() {
		closeTimeout = setTimeout(() => {
			isOpen = false;
		}, 150);
	}

	function handleSelect(workspace: WorkspaceResponse) {
		switchWorkspace(workspace.id);
		isOpen = false;
	}

	function handleCreateClick() {
		isOpen = false;
		onCreateWorkspace?.();
	}

	function handleKeydown(e: KeyboardEvent) {
		switch (e.key) {
			case 'Enter':
			case ' ':
				isOpen = !isOpen;
				e.preventDefault();
				break;
			case 'Escape':
				isOpen = false;
				e.preventDefault();
				break;
			case 'ArrowDown':
				if (!isOpen) {
					isOpen = true;
				}
				e.preventDefault();
				break;
		}
	}

	// Close on navigation
	beforeNavigate(() => {
		isOpen = false;
	});
</script>

<div
	class="relative"
	role="navigation"
	aria-label="Workspace switcher"
	onmouseenter={openDropdown}
	onmouseleave={closeDropdown}
>
	<!-- Trigger button -->
	<button
		type="button"
		class="flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-colors bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300"
		aria-expanded={isOpen}
		aria-haspopup="listbox"
		disabled={$isWorkspaceLoading}
		onclick={() => (isOpen = !isOpen)}
		onkeydown={handleKeydown}
	>
		{#if $currentWorkspace}
			<Building2 class="w-4 h-4 text-brand-600 dark:text-brand-400" />
		{:else}
			<User class="w-4 h-4 text-neutral-500" />
		{/if}
		<span class="max-w-[120px] truncate font-medium">{displayName}</span>
		<ChevronDown
			class="w-4 h-4 transition-transform {isOpen ? 'rotate-180' : ''}"
		/>
	</button>

	<!-- Dropdown menu -->
	{#if isOpen}
		<!-- svelte-ignore a11y_interactive_supports_focus -->
		<div
			class="absolute left-0 top-full mt-1 min-w-[200px] max-w-[280px] bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg py-1 z-50"
			role="listbox"
			aria-label="Available workspaces"
			onmouseenter={openDropdown}
			onmouseleave={closeDropdown}
		>
			<!-- Personal option (no workspace) -->
			<button
				type="button"
				class="w-full flex items-center gap-3 px-3 py-2 text-sm transition-colors text-left {!$currentWorkspace
					? 'text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 font-medium'
					: 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700'}"
				role="option"
				aria-selected={!$currentWorkspace}
				onclick={() => { switchWorkspace(''); isOpen = false; }}
			>
				<User class="w-4 h-4 flex-shrink-0" />
				<span class="flex-1 truncate">Personal</span>
				{#if !$currentWorkspace}
					<Check class="w-4 h-4 text-brand-600 dark:text-brand-400" />
				{/if}
			</button>

			{#if $workspaces.length > 0}
				<div class="my-1 border-t border-neutral-200 dark:border-neutral-700"></div>

				<!-- Workspace list -->
				{#each $workspaces as workspace (workspace.id)}
					<button
						type="button"
						class="w-full flex items-center gap-3 px-3 py-2 text-sm transition-colors text-left {$currentWorkspace?.id === workspace.id
							? 'text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 font-medium'
							: 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700'}"
						role="option"
						aria-selected={$currentWorkspace?.id === workspace.id}
						onclick={() => handleSelect(workspace)}
					>
						<Building2 class="w-4 h-4 flex-shrink-0 text-brand-500" />
						<div class="flex-1 min-w-0">
							<span class="block truncate">{workspace.name}</span>
							{#if workspace.member_count !== undefined}
								<span class="text-xs text-neutral-500 dark:text-neutral-400">
									{workspace.member_count} member{workspace.member_count !== 1 ? 's' : ''}
								</span>
							{/if}
						</div>
						{#if $currentWorkspace?.id === workspace.id}
							<Check class="w-4 h-4 text-brand-600 dark:text-brand-400 flex-shrink-0" />
						{/if}
					</button>
				{/each}
			{/if}

			<!-- Create workspace button -->
			<div class="my-1 border-t border-neutral-200 dark:border-neutral-700"></div>
			<button
				type="button"
				class="w-full flex items-center gap-3 px-3 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
				onclick={handleCreateClick}
			>
				<Plus class="w-4 h-4" />
				<span>Create Workspace</span>
			</button>
		</div>
	{/if}
</div>
