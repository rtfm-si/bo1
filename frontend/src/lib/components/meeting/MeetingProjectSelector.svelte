<script lang="ts">
	/**
	 * MeetingProjectSelector - Select projects to link to a meeting
	 *
	 * Used in:
	 * - Meeting creation: select existing projects to link
	 * - Meeting detail: manage linked projects post-completion
	 *
	 * Filters to same-workspace projects only.
	 */
	import { apiClient } from '$lib/api/client';
	import type { AvailableProjectItem, SessionProjectItem } from '$lib/api/types';
	import { Check, ChevronDown, FolderKanban, Loader2, X } from 'lucide-svelte';

	interface Props {
		/** Session ID for existing meetings */
		sessionId?: string;
		/** Current linked project IDs (for creation flow) */
		selectedProjectIds?: string[];
		/** Callback when selection changes */
		onSelectionChange?: (projectIds: string[]) => void;
		/** Whether the selector is disabled */
		disabled?: boolean;
		/** Label text */
		label?: string;
	}

	let {
		sessionId = '',
		selectedProjectIds = [],
		onSelectionChange,
		disabled = false,
		label = 'Link to Projects'
	}: Props = $props();

	let isExpanded = $state(false);
	let isLoading = $state(false);
	let availableProjects = $state<AvailableProjectItem[]>([]);
	let linkedProjects = $state<SessionProjectItem[]>([]);
	let selectedIds = $state<Set<string>>(new Set(selectedProjectIds));

	// Track current mode - are we managing an existing session or creating new?
	let isExistingSession = $derived(!!sessionId);

	// Load projects on expand
	async function loadProjects() {
		if (!isExpanded) return;

		isLoading = true;
		try {
			if (isExistingSession) {
				// Load both available and linked for existing sessions
				const [availableResp, linkedResp] = await Promise.all([
					apiClient.getAvailableProjects(sessionId),
					apiClient.getSessionProjects(sessionId)
				]);
				availableProjects = availableResp.projects;
				linkedProjects = linkedResp.projects;
				// Update selectedIds from linked projects
				selectedIds = new Set(linkedProjects.map((p) => p.project_id));
			} else {
				// For creation flow, get all user projects
				const projectsResp = await apiClient.listProjects({ per_page: 50 });
				availableProjects = projectsResp.projects.map((p) => ({
					id: p.id,
					name: p.name,
					description: p.description ?? null,
					status: p.status,
					progress_percent: p.progress_percent,
					is_linked: selectedIds.has(p.id)
				}));
			}
		} catch (err) {
			console.error('Failed to load projects:', err);
		} finally {
			isLoading = false;
		}
	}

	// Load on expand
	$effect(() => {
		if (isExpanded) {
			loadProjects();
		}
	});

	// Toggle project selection
	async function toggleProject(projectId: string) {
		if (disabled) return;

		const newSelected = new Set(selectedIds);
		const wasSelected = newSelected.has(projectId);

		if (wasSelected) {
			newSelected.delete(projectId);
			// If existing session, unlink via API
			if (isExistingSession) {
				try {
					await apiClient.unlinkProjectFromSession(sessionId, projectId);
				} catch (err) {
					console.error('Failed to unlink project:', err);
					return; // Don't update UI on error
				}
			}
		} else {
			newSelected.add(projectId);
			// If existing session, link via API
			if (isExistingSession) {
				try {
					await apiClient.linkProjectsToSession(sessionId, {
						project_ids: [projectId]
					});
				} catch (err) {
					console.error('Failed to link project:', err);
					return; // Don't update UI on error
				}
			}
		}

		selectedIds = newSelected;
		onSelectionChange?.([...newSelected]);
	}

	// Get display text for button
	let buttonText = $derived(() => {
		const count = selectedIds.size;
		if (count === 0) return label;
		return `${count} project${count === 1 ? '' : 's'} linked`;
	});

	// Status badge colors
	function getStatusColor(status: string): string {
		switch (status) {
			case 'active':
				return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
			case 'paused':
				return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
			case 'completed':
				return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
			default:
				return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
		}
	}
</script>

<div class="relative">
	<!-- Toggle Button -->
	<button
		type="button"
		class="flex w-full items-center justify-between gap-2 rounded-lg border border-gray-200 px-4 py-2.5 text-left transition-colors hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
		class:opacity-50={disabled}
		class:cursor-not-allowed={disabled}
		onclick={() => !disabled && (isExpanded = !isExpanded)}
	>
		<span class="flex items-center gap-2">
			<FolderKanban class="h-4 w-4 text-gray-500" />
			<span class="text-sm text-gray-700 dark:text-gray-300">{buttonText()}</span>
		</span>
		<ChevronDown
			class="h-4 w-4 text-gray-400 transition-transform {isExpanded ? 'rotate-180' : ''}"
		/>
	</button>

	<!-- Dropdown Panel -->
	{#if isExpanded}
		<div
			class="absolute z-20 mt-2 w-full rounded-lg border border-gray-200 bg-white p-2 shadow-lg dark:border-gray-700 dark:bg-gray-800"
		>
			{#if isLoading}
				<div class="flex items-center justify-center py-8">
					<Loader2 class="h-5 w-5 animate-spin text-gray-400" />
				</div>
			{:else if availableProjects.length === 0}
				<div class="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
					<FolderKanban class="mx-auto mb-2 h-8 w-8 text-gray-300 dark:text-gray-600" />
					<p>No projects available</p>
					<p class="text-xs">Create a project first to link it here</p>
				</div>
			{:else}
				<div class="max-h-64 space-y-1 overflow-y-auto">
					{#each availableProjects as project (project.id)}
						<button
							type="button"
							class="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
							onclick={() => toggleProject(project.id)}
						>
							<!-- Checkbox -->
							<div
								class="flex h-5 w-5 shrink-0 items-center justify-center rounded border"
								class:border-brand-500={selectedIds.has(project.id)}
								class:bg-brand-500={selectedIds.has(project.id)}
								class:border-gray-300={!selectedIds.has(project.id)}
								class:dark:border-gray-600={!selectedIds.has(project.id)}
							>
								{#if selectedIds.has(project.id)}
									<Check class="h-3 w-3 text-white" />
								{/if}
							</div>

							<!-- Project Info -->
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2">
									<span class="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
										{project.name}
									</span>
									<span class={`rounded px-1.5 py-0.5 text-xs ${getStatusColor(project.status)}`}>
										{project.status}
									</span>
								</div>
								{#if project.description}
									<p class="truncate text-xs text-gray-500 dark:text-gray-400">
										{project.description}
									</p>
								{/if}
							</div>

							<!-- Progress -->
							<div class="flex shrink-0 items-center gap-1">
								<div class="h-1.5 w-12 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-600">
									<div
										class="h-full bg-brand-500 transition-all"
										style="width: {project.progress_percent}%"
									></div>
								</div>
								<span class="text-xs text-gray-500">{project.progress_percent}%</span>
							</div>
						</button>
					{/each}
				</div>
			{/if}

			<!-- Close button -->
			<div class="mt-2 border-t border-gray-200 pt-2 dark:border-gray-700">
				<button
					type="button"
					class="flex w-full items-center justify-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
					onclick={() => (isExpanded = false)}
				>
					<X class="h-4 w-4" />
					Close
				</button>
			</div>
		</div>
	{/if}
</div>
