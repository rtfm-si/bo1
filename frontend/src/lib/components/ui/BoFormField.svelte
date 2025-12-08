<script lang="ts">
	/**
	 * BoFormField - Form field wrapper with label, description, and error
	 * Use with any input component via the field slot
	 */
	import type { Snippet } from 'svelte';

	interface Props {
		label?: string;
		description?: string;
		error?: string;
		required?: boolean;
		id?: string;
		class?: string;
		children?: Snippet;
	}

	let {
		label,
		description,
		error,
		required = false,
		id,
		class: className = '',
		children,
	}: Props = $props();

	const fieldId = $derived(id || `field-${Math.random().toString(36).substring(7)}`);
</script>

<div class="w-full {className}">
	{#if label}
		<label
			for={fieldId}
			class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5"
		>
			{label}
			{#if required}
				<span class="text-error-500 ml-0.5">*</span>
			{/if}
		</label>
	{/if}

	{#if description}
		<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-2">
			{description}
		</p>
	{/if}

	<div data-field-id={fieldId}>
		{@render children?.()}
	</div>

	{#if error}
		<p
			id="{fieldId}-error"
			class="mt-1.5 text-sm text-error-600 dark:text-error-400"
			role="alert"
		>
			{error}
		</p>
	{/if}
</div>
