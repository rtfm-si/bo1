<script lang="ts">
	/**
	 * ProjectSelector Component - Dropdown for assigning actions to projects
	 * Shows user's projects with ability to assign, unassign, or create new
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { ProjectDetailResponse } from '$lib/api/types';
	import Button from '$lib/components/ui/Button.svelte';
	import CreateProjectModal from '$lib/components/projects/CreateProjectModal.svelte';
	import {
		FolderKanban,
		ChevronDown,
		Check,
		Plus,
		X,
		Loader2,
		AlertCircle
	} from 'lucide-svelte';

	interface Props {
		actionId: string;
		currentProjectId?: string | null;
		onchange?: (projectId: string | null, projectName: string | null) => void;
	}

	let { actionId, currentProjectId = null, onchange }: Props = $props();

	// State
	let projects = $state<ProjectDetailResponse[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let isOpen = $state(false);
	let isUpdating = $state(false);
	let showCreateModal = $state(false);

	// Current project derived
	const currentProject = $derived(
		projects.find(p => p.id === currentProjectId) || null
	);

	async function loadProjects() {
		try {
			isLoading = true;
			error = null;
			const response = await apiClient.listProjects({ per_page: 100 });
			projects = response.projects.filter(p => p.status !== 'archived');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load projects';
		} finally {
			isLoading = false;
		}
	}

	async function selectProject(project: ProjectDetailResponse | null) {
		if (isUpdating) return;

		try {
			isUpdating = true;
			error = null;

			if (project) {
				// Assign to new project
				// If currently assigned to another project, remove from old first
				if (currentProjectId && currentProjectId !== project.id) {
					await apiClient.removeActionFromProject(currentProjectId, actionId);
				}
				await apiClient.assignActionToProject(project.id, actionId);
				onchange?.(project.id, project.name);
			} else {
				// Remove from current project
				if (currentProjectId) {
					await apiClient.removeActionFromProject(currentProjectId, actionId);
				}
				onchange?.(null, null);
			}

			isOpen = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update project';
		} finally {
			isUpdating = false;
		}
	}

	function handleCreateProject() {
		isOpen = false;
		showCreateModal = true;
	}

	async function handleProjectCreated(newProject: ProjectDetailResponse) {
		// Add to list and select it
		projects = [newProject, ...projects];
		await selectProject(newProject);
		showCreateModal = false;
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.project-selector-container')) {
			isOpen = false;
		}
	}

	onMount(() => {
		loadProjects();
		document.addEventListener('click', handleClickOutside);
		return () => document.removeEventListener('click', handleClickOutside);
	});
</script>

<div class="project-selector-container relative">
	<!-- Trigger Button -->
	<button
		type="button"
		onclick={() => isOpen = !isOpen}
		disabled={isLoading || isUpdating}
		class="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border transition-colors
			{currentProject
				? 'bg-brand-50 dark:bg-brand-900/20 border-brand-200 dark:border-brand-800 text-brand-700 dark:text-brand-300'
				: 'bg-neutral-50 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400'}
			hover:border-brand-300 dark:hover:border-brand-700
			disabled:opacity-50 disabled:cursor-not-allowed"
	>
		{#if isLoading || isUpdating}
			<Loader2 class="w-4 h-4 animate-spin" />
		{:else}
			<FolderKanban class="w-4 h-4" />
		{/if}
		<span class="max-w-[150px] truncate">
			{currentProject?.name || 'No project'}
		</span>
		<ChevronDown class="w-4 h-4 {isOpen ? 'rotate-180' : ''} transition-transform" />
	</button>

	<!-- Dropdown Menu -->
	{#if isOpen}
		<div class="absolute z-50 mt-1 w-64 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg overflow-hidden">
			<!-- Search/Header -->
			<div class="px-3 py-2 border-b border-neutral-200 dark:border-neutral-700">
				<span class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
					Assign to Project
				</span>
			</div>

			{#if error}
				<div class="px-3 py-2 flex items-center gap-2 text-sm text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/20">
					<AlertCircle class="w-4 h-4" />
					{error}
				</div>
			{/if}

			<!-- Options List -->
			<div class="max-h-64 overflow-y-auto">
				<!-- No project option -->
				<button
					type="button"
					onclick={() => selectProject(null)}
					disabled={isUpdating || !currentProjectId}
					class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors disabled:opacity-50"
				>
					<X class="w-4 h-4 text-neutral-400" />
					<span class="flex-1 text-neutral-600 dark:text-neutral-400">No project</span>
					{#if !currentProjectId}
						<Check class="w-4 h-4 text-brand-600 dark:text-brand-400" />
					{/if}
				</button>

				<!-- Divider -->
				<div class="border-t border-neutral-200 dark:border-neutral-700 my-1"></div>

				<!-- Projects -->
				{#if projects.length === 0 && !isLoading}
					<div class="px-3 py-4 text-sm text-center text-neutral-500 dark:text-neutral-400">
						No projects yet
					</div>
				{:else}
					{#each projects as project (project.id)}
						<button
							type="button"
							onclick={() => selectProject(project)}
							disabled={isUpdating}
							class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors disabled:opacity-50"
						>
							<div
								class="w-3 h-3 rounded-full flex-shrink-0"
								style="background-color: {project.color || '#6366f1'}"
							></div>
							<span class="flex-1 truncate text-neutral-900 dark:text-neutral-100">
								{project.name}
							</span>
							{#if project.id === currentProjectId}
								<Check class="w-4 h-4 text-brand-600 dark:text-brand-400" />
							{/if}
						</button>
					{/each}
				{/if}

				<!-- Create new option -->
				<div class="border-t border-neutral-200 dark:border-neutral-700 mt-1">
					<button
						type="button"
						onclick={handleCreateProject}
						disabled={isUpdating}
						class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors"
					>
						<Plus class="w-4 h-4" />
						<span>Create new project</span>
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>

<!-- Create Project Modal -->
<CreateProjectModal
	bind:open={showCreateModal}
	actionIdToAssign={actionId}
	onsuccess={handleProjectCreated}
/>
