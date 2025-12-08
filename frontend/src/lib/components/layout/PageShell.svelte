<script lang="ts">
	/**
	 * PageShell - Standard page wrapper with max-width and responsive padding
	 * Use as the root container for page content
	 */
	import type { Snippet } from 'svelte';

	interface Props {
		maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '7xl' | 'full';
		padding?: 'none' | 'sm' | 'md' | 'lg';
		class?: string;
		children?: Snippet;
	}

	let {
		maxWidth = '7xl',
		padding = 'md',
		class: className = '',
		children,
	}: Props = $props();

	const maxWidthClasses = {
		sm: 'max-w-sm',
		md: 'max-w-md',
		lg: 'max-w-lg',
		xl: 'max-w-xl',
		'2xl': 'max-w-2xl',
		'7xl': 'max-w-7xl',
		full: 'max-w-full',
	};

	const paddingClasses = {
		none: '',
		sm: 'px-4 py-4',
		md: 'px-4 sm:px-6 lg:px-8 py-6',
		lg: 'px-4 sm:px-6 lg:px-8 py-8',
	};

	const classes = $derived([
		maxWidthClasses[maxWidth],
		'mx-auto',
		paddingClasses[padding],
		className,
	].filter(Boolean).join(' '));
</script>

<div class={classes}>
	{@render children?.()}
</div>
