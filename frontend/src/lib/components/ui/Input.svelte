<script lang="ts">
	/**
	 * Input Component - shadcn-svelte wrapper with backward-compatible API
	 * Preserves label, error, and helper text functionality
	 */
	import { Input as ShadcnInput } from './shadcn/input';

	// Props matching the legacy API
	let {
		type = 'text',
		value = $bindable(''),
		placeholder = '',
		label,
		helperText,
		error,
		disabled = false,
		required = false,
		id,
		ariaLabel,
		oninput,
		onchange,
		onblur,
		onfocus,
		onkeydown,
	}: {
		type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url';
		value?: string;
		placeholder?: string;
		label?: string;
		helperText?: string;
		error?: string;
		disabled?: boolean;
		required?: boolean;
		id?: string;
		ariaLabel?: string;
		oninput?: (event: Event) => void;
		onchange?: (event: Event) => void;
		onblur?: (event: FocusEvent) => void;
		onfocus?: (event: FocusEvent) => void;
		onkeydown?: (event: KeyboardEvent) => void;
	} = $props();

	// Generate ID if not provided
	const inputId = $derived(id || `input-${Math.random().toString(36).substring(7)}`);
</script>

<div class="w-full">
	{#if label}
		<label
			for={inputId}
			class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
		>
			{label}
			{#if required}
				<span class="text-error-500">*</span>
			{/if}
		</label>
	{/if}

	<ShadcnInput
		{type}
		{placeholder}
		{disabled}
		{required}
		id={inputId}
		bind:value
		aria-label={ariaLabel}
		aria-invalid={error ? 'true' : 'false'}
		aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
		class={error ? 'border-error-500 focus-visible:ring-error-500 focus-visible:border-error-500' : ''}
		{oninput}
		{onchange}
		{onblur}
		{onfocus}
		{onkeydown}
	/>

	{#if error}
		<p id="{inputId}-error" class="mt-2 text-sm text-error-600 dark:text-error-400">
			{error}
		</p>
	{:else if helperText}
		<p id="{inputId}-helper" class="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
			{helperText}
		</p>
	{/if}
</div>
