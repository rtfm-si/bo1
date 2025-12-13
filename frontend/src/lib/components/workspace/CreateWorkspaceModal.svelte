<script lang="ts">
	/**
	 * CreateWorkspaceModal Component - Form for creating a new workspace
	 */
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { createWorkspace } from '$lib/stores/workspace';

	interface Props {
		open?: boolean;
		onclose?: () => void;
		onsuccess?: () => void;
	}

	let { open = $bindable(false), onclose, onsuccess }: Props = $props();

	let name = $state('');
	let slug = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	// Auto-generate slug from name
	const autoSlug = $derived(
		name
			.toLowerCase()
			.replace(/[^a-z0-9]+/g, '-')
			.replace(/^-|-$/g, '')
			.slice(0, 50)
	);

	// Use custom slug if provided, otherwise auto-generated
	const effectiveSlug = $derived(slug || autoSlug);

	function handleClose() {
		// Reset form state
		name = '';
		slug = '';
		error = null;
		onclose?.();
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!name.trim()) {
			error = 'Workspace name is required';
			return;
		}

		isSubmitting = true;
		error = null;

		try {
			const result = await createWorkspace(name.trim(), effectiveSlug || undefined);
			if (result) {
				// Success - close modal and notify parent
				name = '';
				slug = '';
				open = false;
				onsuccess?.();
			} else {
				error = 'Failed to create workspace';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create workspace';
		} finally {
			isSubmitting = false;
		}
	}
</script>

<Modal {open} title="Create Workspace" size="sm" onclose={handleClose}>
	<form onsubmit={handleSubmit} class="space-y-4">
		{#if error}
			<Alert variant="error">{error}</Alert>
		{/if}

		<div class="space-y-1">
			<label for="workspace-name" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
				Workspace Name
			</label>
			<Input
				id="workspace-name"
				bind:value={name}
				placeholder="My Team"
				required
				disabled={isSubmitting}
			/>
		</div>

		<div class="space-y-1">
			<label for="workspace-slug" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
				URL Slug <span class="text-neutral-400">(optional)</span>
			</label>
			<Input
				id="workspace-slug"
				bind:value={slug}
				placeholder={autoSlug || 'my-team'}
				disabled={isSubmitting}
			/>
			{#if effectiveSlug}
				<p class="text-xs text-neutral-500 dark:text-neutral-400">
					URL: /workspace/<span class="font-mono">{effectiveSlug}</span>
				</p>
			{/if}
		</div>

		<div class="flex justify-end gap-3 pt-4">
			<Button type="button" variant="ghost" onclick={handleClose} disabled={isSubmitting}>
				Cancel
			</Button>
			<Button type="submit" variant="brand" loading={isSubmitting}>
				Create Workspace
			</Button>
		</div>
	</form>
</Modal>
