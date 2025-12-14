<script lang="ts">
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { ProjectDetailResponse, ProjectStatus, UnassignedCountResponse } from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import AutogenProjectsModal from '$lib/components/projects/AutogenProjectsModal.svelte';

	// Use data fetch utility for projects
	const projectsData = useDataFetch(() => apiClient.listProjects());

	// Derived state for template compatibility
	const projects = $derived<ProjectDetailResponse[]>(projectsData.data?.projects || []);
	const isLoading = $derived(projectsData.isLoading);
	const error = $derived(projectsData.error);

	// Create project modal state
	let showCreateModal = $state(false);
	let newProjectName = $state('');
	let newProjectDescription = $state('');
	let isCreating = $state(false);
	let createError = $state<string | null>(null);

	// Autogen modal state
	let showAutogenModal = $state(false);
	let unassignedData = $state<UnassignedCountResponse | null>(null);

	onMount(() => {
		projectsData.fetch();
		loadUnassignedCount();
	});

	async function loadUnassignedCount() {
		try {
			unassignedData = await apiClient.getUnassignedCount();
		} catch (err) {
			console.error('Failed to load unassigned count:', err);
		}
	}

	function handleAutogenSuccess(createdProjects: ProjectDetailResponse[]) {
		// Refresh projects list
		projectsData.fetch();
		// Refresh unassigned count
		loadUnassignedCount();
	}

	function formatDate(dateString: string | null): string {
		if (!dateString) return '—';
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}

	function getStatusColor(status: ProjectStatus): string {
		switch (status) {
			case 'active':
				return 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300';
			case 'paused':
				return 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300';
			case 'completed':
				return 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300';
			case 'archived':
				return 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400';
			default:
				return 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400';
		}
	}

	function getProgressColor(progress: number): string {
		if (progress >= 100) return 'bg-success-500';
		if (progress >= 75) return 'bg-brand-500';
		if (progress >= 50) return 'bg-warning-500';
		return 'bg-neutral-400';
	}

	async function handleCreateProject() {
		if (!newProjectName.trim()) {
			createError = 'Project name is required';
			return;
		}

		isCreating = true;
		createError = null;

		try {
			await apiClient.createProject({
				name: newProjectName.trim(),
				description: newProjectDescription.trim() || null
			});
			showCreateModal = false;
			newProjectName = '';
			newProjectDescription = '';
			await projectsData.fetch();
		} catch (err) {
			createError = err instanceof Error ? err.message : 'Failed to create project';
		} finally {
			isCreating = false;
		}
	}

	async function handleDeleteProject(projectId: string, event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();

		if (!confirm('Are you sure you want to archive this project? This cannot be undone.')) {
			return;
		}

		try {
			await apiClient.deleteProject(projectId);
			await projectsData.fetch();
		} catch (err) {
			console.error('Failed to delete project:', err);
		}
	}
</script>

<svelte:head>
	<title>Projects - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Header with Create Button -->
		<div class="flex items-center justify-between mb-8">
			<div>
				<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">Projects</h1>
				<p class="mt-1 text-neutral-600 dark:text-neutral-400">
					Organize your actions into value-delivering projects
				</p>
			</div>
			<div class="flex items-center gap-3">
				<Button variant="ghost" onclick={() => (showAutogenModal = true)}>
					{#snippet children()}
						<svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
						</svg>
						Generate Ideas
						{#if unassignedData?.can_autogenerate}
							<span class="ml-1.5">
								<Badge variant="info" size="sm">{unassignedData?.unassigned_count ?? 0}</Badge>
							</span>
						{/if}
					{/snippet}
				</Button>
				<Button variant="brand" onclick={() => (showCreateModal = true)}>
					{#snippet children()}
						<svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
						</svg>
						New Project
					{/snippet}
				</Button>
			</div>
		</div>

		{#if isLoading}
			<!-- Loading State -->
			<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
				{#each Array(6) as _, i (i)}
					<ShimmerSkeleton type="card" />
				{/each}
			</div>
		{:else if error}
			<!-- Error State -->
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-6">
				<div class="flex items-center gap-3">
					<svg class="w-6 h-6 text-error-600 dark:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					<div>
						<h3 class="text-lg font-semibold text-error-900 dark:text-error-200">Error Loading Projects</h3>
						<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
					</div>
				</div>
				<div class="mt-4">
					<Button variant="danger" size="md" onclick={() => projectsData.fetch()}>
						{#snippet children()}
							Retry
						{/snippet}
					</Button>
				</div>
			</div>
		{:else if projects.length === 0}
			<!-- Empty State -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-12 text-center">
				<svg class="w-16 h-16 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
				</svg>
				<h2 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-2">
					No projects yet
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-md mx-auto">
					{#if unassignedData?.can_autogenerate}
						You have <strong>{unassignedData.unassigned_count}</strong> unassigned actions. Use autogenerate to create projects from them, or create a project manually.
					{:else}
						Generate project ideas from your business priorities, or create a project manually.
					{/if}
				</p>
				<div class="flex flex-col items-center justify-center gap-3">
					<div class="flex items-center gap-3">
						<Button variant="brand" size="lg" onclick={() => (showAutogenModal = true)}>
							{#snippet children()}
								<svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
								</svg>
								Generate Project Ideas
							{/snippet}
						</Button>
						<Button variant="ghost" size="lg" onclick={() => (showCreateModal = true)}>
							{#snippet children()}
								<svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
								</svg>
								Create Manually
							{/snippet}
						</Button>
					</div>
					<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-2">
						{#if unassignedData?.can_autogenerate}
							Suggestions from your unassigned actions or business context
						{:else}
							Suggestions based on your business priorities
						{/if}
					</p>
				</div>
			</div>
		{:else}
			<!-- Projects Grid -->
			<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
				{#each projects as project (project.id)}
					<a
						href="/projects/{project.id}"
						class="block bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition-all duration-200"
					>
						<div class="flex items-start justify-between gap-2 mb-4">
							<div class="flex items-center gap-2">
								{#if project.icon}
									<span class="text-xl">{project.icon}</span>
								{:else}
									<span class="w-8 h-8 rounded flex items-center justify-center text-sm font-bold" style="background-color: {project.color || '#6366f1'}20; color: {project.color || '#6366f1'}">
										{project.name.charAt(0).toUpperCase()}
									</span>
								{/if}
								<h3 class="font-semibold text-neutral-900 dark:text-white truncate">
									{project.name}
								</h3>
							</div>
							<span class="px-2.5 py-1 text-xs font-medium rounded-full {getStatusColor(project.status)}">
								{project.status}
							</span>
						</div>

						{#if project.description}
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4 line-clamp-2">
								{project.description}
							</p>
						{/if}

						<!-- Progress Bar -->
						<div class="mb-4">
							<div class="flex items-center justify-between text-sm mb-1">
								<span class="text-neutral-600 dark:text-neutral-400">Progress</span>
								<span class="font-medium text-neutral-900 dark:text-white">{project.progress_percent}%</span>
							</div>
							<div class="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
								<div
									class="h-full rounded-full transition-all duration-300 {getProgressColor(project.progress_percent)}"
									style="width: {project.progress_percent}%"
								></div>
							</div>
						</div>

						<!-- Stats -->
						<div class="flex items-center gap-4 text-sm text-neutral-600 dark:text-neutral-400">
							<span class="flex items-center gap-1">
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
								</svg>
								{project.completed_actions}/{project.total_actions} actions
							</span>
							{#if project.estimated_end_date}
								<span class="flex items-center gap-1">
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
									</svg>
									{formatDate(project.estimated_end_date)}
								</span>
							{/if}
						</div>

						<!-- Footer with actions -->
						<div class="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
							<span class="text-xs text-neutral-500 dark:text-neutral-500">
								Updated {formatDate(project.updated_at)}
							</span>
							<button
								onclick={(e) => handleDeleteProject(project.id, e)}
								class="p-1 hover:bg-error-50 dark:hover:bg-error-900/20 rounded transition-colors group"
								title="Archive project"
								aria-label="Archive project"
							>
								<svg class="w-4 h-4 text-neutral-400 dark:text-neutral-500 group-hover:text-error-600 dark:group-hover:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
								</svg>
							</button>
						</div>
					</a>
				{/each}
			</div>
		{/if}
	</main>
</div>

<!-- Create Project Modal -->
{#if showCreateModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
		<button
			class="absolute inset-0 bg-black/50 backdrop-blur-sm"
			onclick={() => (showCreateModal = false)}
			aria-label="Close modal"
		></button>
		<div class="relative bg-white dark:bg-neutral-800 rounded-xl shadow-xl max-w-md w-full p-6">
			<h2 class="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
				Create New Project
			</h2>

			<form onsubmit={(e) => { e.preventDefault(); handleCreateProject(); }}>
				<div class="space-y-4">
					<div>
						<label for="projectName" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
							Project Name *
						</label>
						<input
							id="projectName"
							type="text"
							bind:value={newProjectName}
							class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent"
							placeholder="e.g., Q1 Product Launch"
						/>
					</div>

					<div>
						<label for="projectDescription" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
							Description
						</label>
						<textarea
							id="projectDescription"
							bind:value={newProjectDescription}
							rows="3"
							class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
							placeholder="What is this project about?"
						></textarea>
					</div>

					{#if createError}
						<p class="text-sm text-error-600 dark:text-error-400">{createError}</p>
					{/if}
				</div>

				<div class="mt-6 flex gap-3">
					<Button variant="ghost" onclick={() => (showCreateModal = false)} disabled={isCreating}>
						{#snippet children()}
							Cancel
						{/snippet}
					</Button>
					<Button type="submit" variant="brand" disabled={isCreating}>
						{#snippet children()}
							{isCreating ? 'Creating...' : 'Create Project'}
						{/snippet}
					</Button>
				</div>
			</form>
		</div>
	</div>
{/if}

<!-- Autogenerate Projects Modal -->
<AutogenProjectsModal
	bind:open={showAutogenModal}
	onsuccess={handleAutogenSuccess}
/>
