<script lang="ts">
	/**
	 * CreateProjectModal Component - Form for creating a new project
	 * Can optionally auto-assign an action to the new project
	 */
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { apiClient } from '$lib/api/client';
	import type { ProjectDetailResponse, ProjectStatus } from '$lib/api/types';

	interface Props {
		open?: boolean;
		actionIdToAssign?: string;
		onclose?: () => void;
		onsuccess?: (project: ProjectDetailResponse) => void;
	}

	let { open = $bindable(false), actionIdToAssign, onclose, onsuccess }: Props = $props();

	// Form state
	let name = $state('');
	let description = $state('');
	let status = $state<ProjectStatus>('active');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	// Status options
	const statusOptions: { value: ProjectStatus; label: string }[] = [
		{ value: 'active', label: 'Active' },
		{ value: 'paused', label: 'Paused' },
		{ value: 'completed', label: 'Completed' }
	];

	function handleClose() {
		// Reset form state
		name = '';
		description = '';
		status = 'active';
		error = null;
		onclose?.();
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!name.trim()) {
			error = 'Project name is required';
			return;
		}

		isSubmitting = true;
		error = null;

		try {
			// Create the project
			const project = await apiClient.createProject({
				name: name.trim(),
				description: description.trim() || undefined
			});

			// If we have an action to assign, do it
			if (actionIdToAssign) {
				await apiClient.assignActionToProject(project.id, actionIdToAssign);
			}

			// Reset form and notify
			name = '';
			description = '';
			status = 'active';
			open = false;
			onsuccess?.(project);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create project';
		} finally {
			isSubmitting = false;
		}
	}
</script>

<Modal {open} title="Create New Project" size="sm" onclose={handleClose}>
	<form onsubmit={handleSubmit} class="space-y-4">
		{#if error}
			<Alert variant="error">{error}</Alert>
		{/if}

		<div class="space-y-1">
			<label for="project-name" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
				Project Name <span class="text-error-500">*</span>
			</label>
			<Input
				id="project-name"
				bind:value={name}
				placeholder="Q1 Marketing Campaign"
				required
				disabled={isSubmitting}
			/>
		</div>

		<div class="space-y-1">
			<label for="project-description" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
				Description <span class="text-neutral-400">(optional)</span>
			</label>
			<textarea
				id="project-description"
				bind:value={description}
				placeholder="Brief description of the project..."
				rows="3"
				disabled={isSubmitting}
				class="w-full px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100
					bg-white dark:bg-neutral-800
					border border-neutral-300 dark:border-neutral-600
					rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
					resize-none disabled:opacity-50"
			></textarea>
		</div>

		<div class="space-y-1">
			<label for="project-status" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
				Status
			</label>
			<select
				id="project-status"
				bind:value={status}
				disabled={isSubmitting}
				class="w-full px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100
					bg-white dark:bg-neutral-800
					border border-neutral-300 dark:border-neutral-600
					rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
					disabled:opacity-50"
			>
				{#each statusOptions as option (option.value)}
					<option value={option.value}>{option.label}</option>
				{/each}
			</select>
		</div>

		{#if actionIdToAssign}
			<p class="text-xs text-neutral-500 dark:text-neutral-400">
				The current action will be automatically assigned to this project.
			</p>
		{/if}

		<div class="flex justify-end gap-3 pt-4">
			<Button type="button" variant="ghost" onclick={handleClose} disabled={isSubmitting}>
				Cancel
			</Button>
			<Button type="submit" variant="brand" loading={isSubmitting}>
				Create Project
			</Button>
		</div>
	</form>
</Modal>
