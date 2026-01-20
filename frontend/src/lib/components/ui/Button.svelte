<script lang="ts">
	/**
	 * Button Component - shadcn-svelte wrapper with backward-compatible API
	 * Maps existing Bo1 variant/size props to shadcn equivalents
	 */
	import { Button as ShadcnButton, type ButtonProps } from './shadcn/button';
	import type { Snippet } from 'svelte';

	// Props matching the legacy API
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

	// Map legacy variants to shadcn variants
	const variantMap: Record<string, ButtonProps['variant']> = {
		brand: 'default',
		accent: 'default', // Use default with accent styling
		secondary: 'secondary',
		outline: 'outline',
		ghost: 'ghost',
		danger: 'destructive',
	};

	// Map legacy sizes to shadcn sizes
	const sizeMap: Record<string, ButtonProps['size']> = {
		sm: 'sm',
		md: 'default',
		lg: 'lg',
	};

	// Custom classes for variants shadcn doesn't have built-in
	const customVariantClasses: Record<string, string> = {
		brand: 'bg-brand-600 hover:bg-brand-700 text-white',
		accent: 'bg-accent-600 hover:bg-accent-700 text-white',
	};

	const shadcnVariant = $derived(variantMap[variant] ?? 'default');
	const shadcnSize = $derived(sizeMap[size] ?? 'default');
	const customClass = $derived(
		variant === 'brand' || variant === 'accent' ? customVariantClasses[variant] : ''
	);
</script>

<ShadcnButton
	{type}
	variant={shadcnVariant}
	size={shadcnSize}
	disabled={disabled || loading}
	aria-label={ariaLabel}
	{title}
	{href}
	{onclick}
	class="{customClass} {className}"
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
