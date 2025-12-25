<script lang="ts">
	/**
	 * BoButton - Canonical button wrapper
	 * Wraps Button.svelte with standardized Bo1 API
	 */
	import Button from './Button.svelte';
	import type { Snippet } from 'svelte';

	let {
		variant = 'brand',
		size = 'md',
		type = 'button',
		disabled = false,
		loading = false,
		ariaLabel,
		title,
		onclick,
		class: className = '',
		children,
	}: {
		variant?: 'brand' | 'secondary' | 'outline' | 'ghost' | 'danger';
		size?: 'sm' | 'md' | 'lg';
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		loading?: boolean;
		ariaLabel?: string;
		title?: string;
		onclick?: (event: MouseEvent) => void;
		class?: string;
		children?: Snippet;
	} = $props();
</script>

<Button
	{variant}
	{size}
	{type}
	{disabled}
	{loading}
	{ariaLabel}
	{title}
	{onclick}
	class={className}
>
	{@render children?.()}
</Button>
