<script lang="ts">
	/**
	 * Badge Component - shadcn-svelte wrapper with backward-compatible API
	 * Maps legacy variant names to shadcn + custom styling
	 */
	import { Badge as ShadcnBadge, type BadgeVariant } from './shadcn/badge';
	import type { Snippet } from 'svelte';

	// Props matching the legacy API
	interface Props {
		variant?: 'brand' | 'success' | 'warning' | 'error' | 'info' | 'neutral';
		size?: 'sm' | 'md' | 'lg';
		children?: Snippet;
	}

	let {
		variant = 'neutral',
		size = 'md',
		children
	}: Props = $props();

	// Map legacy variants to shadcn variants + custom classes
	// shadcn only has: default, secondary, destructive, outline
	const variantConfig: Record<string, { shadcn: BadgeVariant; custom: string }> = {
		brand: { shadcn: 'default', custom: 'bg-brand-600 text-white border-brand-600 hover:bg-brand-700' },
		success: { shadcn: 'default', custom: 'bg-success-100 text-success-800 border-success-200 dark:bg-success-900 dark:text-success-200 dark:border-success-800' },
		warning: { shadcn: 'default', custom: 'bg-warning-100 text-warning-800 border-warning-200 dark:bg-warning-900 dark:text-warning-200 dark:border-warning-800' },
		error: { shadcn: 'destructive', custom: '' },
		info: { shadcn: 'default', custom: 'bg-info-100 text-info-800 border-info-200 dark:bg-info-900 dark:text-info-200 dark:border-info-800' },
		neutral: { shadcn: 'secondary', custom: '' },
	};

	// Size classes
	const sizeClasses = {
		sm: 'px-2 py-0.5 text-xs',
		md: 'px-2.5 py-1 text-sm',
		lg: 'px-3 py-1.5 text-base',
	};

	const config = $derived(variantConfig[variant] ?? variantConfig.neutral);
	const sizeClass = $derived(sizeClasses[size] ?? sizeClasses.md);
</script>

<ShadcnBadge
	variant={config.shadcn}
	class="{config.custom} {sizeClass}"
>
	{@render children?.()}
</ShadcnBadge>
