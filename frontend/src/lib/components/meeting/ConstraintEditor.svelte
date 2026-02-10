<script lang="ts">
	/**
	 * ConstraintEditor - Mid-meeting constraint editor panel
	 * Allows users to add/remove/modify constraints during an active deliberation.
	 */
	import { apiClient } from '$lib/api/client';
	import { Settings2, Plus, X, Save } from 'lucide-svelte';

	const CONSTRAINT_TYPES = [
		'budget',
		'time',
		'resource',
		'regulatory',
		'technical',
		'ethical',
		'other'
	] as const;

	interface Props {
		sessionId: string;
		sessionStatus: string;
		constraints: Array<{ type: string; description: string; value?: unknown }>;
	}

	let { sessionId, sessionStatus, constraints }: Props = $props();

	let open = $state(false);
	let saving = $state(false);
	let error = $state('');

	// Local editable copy
	let editableConstraints = $state<Array<{ type: string; description: string; value: string }>>(
		[]
	);

	function syncFromProps() {
		editableConstraints = constraints.map((c) => ({
			type: c.type,
			description: c.description,
			value: c.value != null ? String(c.value) : ''
		}));
	}

	function toggleOpen() {
		if (!open) syncFromProps();
		open = !open;
		error = '';
	}

	function addConstraint() {
		editableConstraints = [
			...editableConstraints,
			{ type: 'other', description: '', value: '' }
		];
	}

	function removeConstraint(index: number) {
		editableConstraints = editableConstraints.filter((_, i) => i !== index);
	}

	async function save() {
		// Validate
		const valid = editableConstraints.filter((c) => c.description.trim().length >= 5);
		if (valid.length === 0 && editableConstraints.length > 0) {
			error = 'Each constraint needs at least 5 characters.';
			return;
		}

		saving = true;
		error = '';
		try {
			const payload = valid.map((c) => ({
				type: c.type,
				description: c.description.trim(),
				value: c.value.trim() || undefined
			}));
			await apiClient.updateConstraints(sessionId, payload);
			open = false;
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Failed to update constraints';
		} finally {
			saving = false;
		}
	}

	const isEnabled = $derived(sessionStatus === 'running');
</script>

{#if isEnabled}
	<div class="relative">
		<button
			type="button"
			class="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
			onclick={toggleOpen}
		>
			<Settings2 class="w-3.5 h-3.5" />
			Constraints
			{#if constraints.length > 0}
				<span
					class="ml-0.5 inline-flex items-center justify-center w-4 h-4 rounded-full bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300 text-[10px]"
				>
					{constraints.length}
				</span>
			{/if}
		</button>

		{#if open}
			<div
				class="absolute right-0 top-full mt-2 z-50 w-96 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-xl p-4"
			>
				<div class="flex items-center justify-between mb-3">
					<h3 class="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
						Active Constraints
					</h3>
					<button
						type="button"
						class="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
						onclick={toggleOpen}
					>
						<X class="w-4 h-4" />
					</button>
				</div>

				<div class="space-y-3 max-h-64 overflow-y-auto">
					{#each editableConstraints as constraint, i (i)}
						<div class="flex gap-2 items-start">
							<select
								bind:value={constraint.type}
								class="w-24 flex-shrink-0 rounded border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-2 py-1 text-xs"
							>
								{#each CONSTRAINT_TYPES as t (t)}
									<option value={t}>{t}</option>
								{/each}
							</select>
							<input
								type="text"
								bind:value={constraint.description}
								placeholder="Constraint description..."
								class="flex-1 rounded border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-2 py-1 text-xs"
							/>
							<input
								type="text"
								bind:value={constraint.value}
								placeholder="Value"
								class="w-20 flex-shrink-0 rounded border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-2 py-1 text-xs"
							/>
							<button
								type="button"
								class="flex-shrink-0 text-neutral-400 hover:text-error-500"
								onclick={() => removeConstraint(i)}
							>
								<X class="w-3.5 h-3.5" />
							</button>
						</div>
					{/each}
				</div>

				{#if error}
					<p class="text-xs text-error-500 mt-2">{error}</p>
				{/if}

				<div class="flex items-center justify-between mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700">
					<button
						type="button"
						class="inline-flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700"
						onclick={addConstraint}
					>
						<Plus class="w-3.5 h-3.5" />
						Add constraint
					</button>
					<button
						type="button"
						class="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
						onclick={save}
						disabled={saving}
					>
						<Save class="w-3.5 h-3.5" />
						{saving ? 'Saving...' : 'Save'}
					</button>
				</div>
			</div>
		{/if}
	</div>
{/if}
