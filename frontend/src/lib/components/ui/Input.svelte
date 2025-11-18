<script lang="ts">
	/**
	 * Input Component - Text input with label, error, and helper text
	 */

	// Props
	export let type: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' = 'text';
	export let value = '';
	export let placeholder = '';
	export let label: string | undefined = undefined;
	export let helperText: string | undefined = undefined;
	export let error: string | undefined = undefined;
	export let disabled = false;
	export let required = false;
	export let id: string | undefined = undefined;

	// Generate ID if not provided
	$: inputId = id || `input-${Math.random().toString(36).substring(7)}`;

	// Compute classes
	$: inputClasses = [
		'w-full px-4 py-2 rounded-md',
		'border',
		error
			? 'border-error-500 focus:ring-error-500 focus:border-error-500'
			: 'border-neutral-300 dark:border-neutral-700 focus:ring-brand-500 focus:border-brand-500',
		'bg-white dark:bg-neutral-900',
		'text-neutral-900 dark:text-neutral-100',
		'placeholder:text-neutral-400 dark:placeholder:text-neutral-500',
		'focus:outline-none focus:ring-2 focus:ring-offset-2',
		'disabled:opacity-50 disabled:cursor-not-allowed',
		'transition-colors duration-200',
	].join(' ');
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

	<input
		{type}
		{placeholder}
		{disabled}
		{required}
		id={inputId}
		bind:value
		class={inputClasses}
		aria-invalid={error ? 'true' : 'false'}
		aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
		on:input
		on:change
		on:blur
		on:focus
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
