<script lang="ts">
	/**
	 * UpdateInput - Form to add progress updates, blockers, or notes to an action
	 */
	import type { ActionUpdateCreate } from '$lib/api/types';

	interface Props {
		onSubmit: (update: ActionUpdateCreate) => Promise<void>;
		disabled?: boolean;
	}

	let { onSubmit, disabled = false }: Props = $props();

	let updateType = $state<'progress' | 'blocker' | 'note'>('note');
	let content = $state('');
	let progressPercent = $state(50);
	let submitting = $state(false);
	let error = $state<string | null>(null);

	const typeOptions = [
		{ value: 'note', label: 'Note', icon: 'comment', color: 'var(--color-muted)' },
		{ value: 'progress', label: 'Progress', icon: 'chart-line', color: 'var(--color-brand)' },
		{ value: 'blocker', label: 'Blocker', icon: 'exclamation-triangle', color: 'var(--color-error)' }
	] as const;

	async function handleSubmit() {
		if (!content.trim()) {
			error = 'Please enter a message';
			return;
		}

		error = null;
		submitting = true;

		try {
			const update: ActionUpdateCreate = {
				update_type: updateType,
				content: content.trim(),
				progress_percent: updateType === 'progress' ? progressPercent : null
			};

			await onSubmit(update);

			// Reset form on success
			content = '';
			progressPercent = 50;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to add update';
		} finally {
			submitting = false;
		}
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
			handleSubmit();
		}
	}
</script>

<div class="update-input">
	<div class="type-selector">
		{#each typeOptions as option (option.value)}
			<button
				type="button"
				class="type-btn"
				class:active={updateType === option.value}
				style="--type-color: {option.color}"
				onclick={() => (updateType = option.value)}
				{disabled}
			>
				{option.label}
			</button>
		{/each}
	</div>

	<div class="input-area">
		<textarea
			bind:value={content}
			placeholder={updateType === 'progress'
				? 'Describe your progress...'
				: updateType === 'blocker'
					? 'What is blocking this action?'
					: 'Add a note...'}
			rows="2"
			{disabled}
			onkeydown={handleKeyDown}
		></textarea>

		{#if updateType === 'progress'}
			<div class="progress-slider">
				<label for="progress-input">Progress: {progressPercent}%</label>
				<input
					id="progress-input"
					type="range"
					min="0"
					max="100"
					step="5"
					bind:value={progressPercent}
					{disabled}
				/>
			</div>
		{/if}
	</div>

	{#if error}
		<p class="error">{error}</p>
	{/if}

	<div class="actions">
		<span class="hint">Press Cmd+Enter to submit</span>
		<button
			type="button"
			class="submit-btn"
			onclick={handleSubmit}
			disabled={disabled || submitting || !content.trim()}
		>
			{#if submitting}
				Adding...
			{:else}
				Add {typeOptions.find((t) => t.value === updateType)?.label || 'Update'}
			{/if}
		</button>
	</div>
</div>

<style>
	.update-input {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.type-selector {
		display: flex;
		gap: 0.5rem;
	}

	.type-btn {
		flex: 1;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: 0.375rem;
		background-color: var(--color-surface);
		color: var(--color-foreground);
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.type-btn:hover:not(:disabled) {
		border-color: var(--type-color);
		color: var(--type-color);
	}

	.type-btn.active {
		background-color: var(--type-color);
		border-color: var(--type-color);
		color: white;
	}

	.type-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.input-area {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	textarea {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: 0.375rem;
		background-color: var(--color-surface);
		color: var(--color-foreground);
		font-size: 0.875rem;
		line-height: 1.5;
		resize: vertical;
		min-height: 60px;
	}

	textarea:focus {
		outline: none;
		border-color: var(--color-brand);
		box-shadow: 0 0 0 2px rgba(var(--color-brand-rgb), 0.1);
	}

	textarea:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	textarea::placeholder {
		color: var(--color-muted);
	}

	.progress-slider {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.progress-slider label {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--color-brand);
	}

	.progress-slider input[type='range'] {
		width: 100%;
		height: 0.5rem;
		border-radius: 0.25rem;
		background: var(--color-surface-secondary);
		appearance: none;
		cursor: pointer;
	}

	.progress-slider input[type='range']::-webkit-slider-thumb {
		appearance: none;
		width: 1rem;
		height: 1rem;
		border-radius: 50%;
		background: var(--color-brand);
		cursor: pointer;
	}

	.progress-slider input[type='range']::-moz-range-thumb {
		width: 1rem;
		height: 1rem;
		border-radius: 50%;
		background: var(--color-brand);
		border: none;
		cursor: pointer;
	}

	.error {
		margin: 0;
		font-size: 0.75rem;
		color: var(--color-error);
	}

	.actions {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.hint {
		font-size: 0.75rem;
		color: var(--color-muted);
	}

	.submit-btn {
		padding: 0.5rem 1rem;
		border: none;
		border-radius: 0.375rem;
		background-color: var(--color-brand);
		color: white;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: background-color 0.15s ease;
	}

	.submit-btn:hover:not(:disabled) {
		background-color: var(--color-brand-hover, var(--color-brand));
		filter: brightness(1.1);
	}

	.submit-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>
