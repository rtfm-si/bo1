<script lang="ts">
	/**
	 * Button Component - shadcn-svelte wrapper
	 * Adds loading spinner on top of shadcn Button
	 */
	import { Button as ShadcnButton } from './shadcn/button';
	import type { ButtonVariant, ButtonSize } from './shadcn/button';
	import type { Snippet } from 'svelte';

	// Props
	let {
		variant = 'brand',
		size = 'md',
		type = 'button',
		disabled = false,
		loading = false,
		ariaLabel,
		title,
		href,
		onclick,
		class: className = '',
		children,
	}: {
		variant?: 'brand' | 'accent' | 'secondary' | 'outline' | 'ghost' | 'danger';
		size?: 'sm' | 'md' | 'lg';
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		loading?: boolean;
		ariaLabel?: string;
		title?: string;
		href?: string;
		onclick?: (event: MouseEvent) => void;
		class?: string;
		children?: Snippet;
	} = $props();
</script>

<ShadcnButton
	{type}
	variant={variant as ButtonVariant}
	size={size as ButtonSize}
	disabled={disabled || loading}
	aria-label={ariaLabel}
	{title}
	{href}
	{onclick}
	class={className}
>
	{#if loading}
		<svg
			class="animate-spin h-5 w-5"
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
		>
			<circle
				class="opacity-25"
				cx="12"
				cy="12"
				r="10"
				stroke="currentColor"
				stroke-width="4"
			/>
			<path
				class="opacity-75"
				fill="currentColor"
				d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
			/>
		</svg>
	{/if}
	{@render children?.()}
</ShadcnButton>
