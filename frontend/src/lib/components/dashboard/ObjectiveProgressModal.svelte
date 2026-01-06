<script lang="ts">
	/**
	 * ObjectiveProgressModal - Edit progress for a strategic objective
	 * Allows setting current/target values with optional unit
	 */
	import Modal from '$lib/components/ui/Modal.svelte';
	import { Button } from '$lib/components/ui/shadcn/button';
	import { Input } from '$lib/components/ui/shadcn/input';
	import type { ObjectiveProgress } from '$lib/api/types';

	interface Props {
		open?: boolean;
		objectiveIndex: number;
		objectiveText: string;
		progress: ObjectiveProgress | null;
		loading?: boolean;
		onSave: (index: number, current: string, target: string, unit: string | null) => void;
		onClose: () => void;
	}

	let {
		open = $bindable(false),
		objectiveIndex,
		objectiveText,
		progress,
		loading = false,
		onSave,
		onClose
	}: Props = $props();

	// Form state
	let current = $state(progress?.current || '');
	let target = $state(progress?.target || '');
	let unit = $state(progress?.unit || '');

	// Reset form when progress changes
	// Defer mutations to avoid state_unsafe_mutation during effect
	// Use setTimeout(0) not queueMicrotask - microtasks can still be in same render batch
	$effect(() => {
		const newCurrent = progress?.current || '';
		const newTarget = progress?.target || '';
		const newUnit = progress?.unit || '';
		setTimeout(() => {
			current = newCurrent;
			target = newTarget;
			unit = newUnit;
		}, 0);
	});

	// Common unit presets
	const unitPresets = ['%', '$', 'MRR', 'customers', 'users', 'count'];

	function handleSave() {
		if (!current.trim() || !target.trim()) return;
		onSave(objectiveIndex, current.trim(), target.trim(), unit.trim() || null);
	}

	function handleClose() {
		open = false;
		onClose();
	}

	function selectUnit(preset: string) {
		unit = preset;
	}
</script>

<Modal bind:open title="Track Progress" size="sm" onclose={handleClose}>
	<div class="space-y-4">
		<!-- Objective display -->
		<div class="p-3 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
			<span class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Objective</span>
			<p class="text-sm text-neutral-900 dark:text-white mt-1">{objectiveText}</p>
		</div>

		<!-- Current value -->
		<div>
			<label for="current" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
				Current Value
			</label>
			<Input
				id="current"
				bind:value={current}
				placeholder="e.g., 5K, 50%, 100"
				class="w-full"
				disabled={loading}
			/>
		</div>

		<!-- Target value -->
		<div>
			<label for="target" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
				Target Value
			</label>
			<Input
				id="target"
				bind:value={target}
				placeholder="e.g., 10K, 80%, 500"
				class="w-full"
				disabled={loading}
			/>
		</div>

		<!-- Unit (optional) -->
		<div>
			<label for="unit" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
				Unit <span class="text-neutral-400 font-normal">(optional)</span>
			</label>
			<Input
				id="unit"
				bind:value={unit}
				placeholder="e.g., MRR, %, customers"
				class="w-full"
				disabled={loading}
			/>
			<!-- Unit presets -->
			<div class="flex flex-wrap gap-1 mt-2">
				{#each unitPresets as preset}
					<button
						type="button"
						onclick={() => selectUnit(preset)}
						class={[
							'text-xs px-2 py-0.5 rounded-full transition-colors',
							unit === preset
								? 'bg-brand-100 dark:bg-brand-900/50 text-brand-700 dark:text-brand-300'
								: 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-600'
						].join(' ')}
						disabled={loading}
					>
						{preset}
					</button>
				{/each}
			</div>
		</div>
	</div>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="outline" onclick={handleClose} disabled={loading}>
				Cancel
			</Button>
			<Button
				variant="default"
				onclick={handleSave}
				disabled={loading || !current.trim() || !target.trim()}
			>
				{#if loading}
					<svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					Saving...
				{:else}
					Save Progress
				{/if}
			</Button>
		</div>
	{/snippet}
</Modal>
