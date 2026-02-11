<script lang="ts">
	/**
	 * Avatar Component - User/persona profile picture with fallback initials
	 * Used for advisor profiles, user identification
	 */

	// Props
	interface Props {
		name: string;
		src?: string;
		size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
		status?: 'online' | 'offline' | 'typing';
	}

	import { getInitials } from '$lib/utils/colors';

	let {
		name,
		src,
		size = 'md',
		status
	}: Props = $props();

	// Size styles
	const sizes = {
		xs: 'w-6 h-6 text-xs',
		sm: 'w-8 h-8 text-sm',
		md: 'w-10 h-10 text-base',
		lg: 'w-12 h-12 text-lg',
		xl: 'w-16 h-16 text-xl',
	};

	// Status indicator sizes
	const statusSizes = {
		xs: 'w-1.5 h-1.5',
		sm: 'w-2 h-2',
		md: 'w-2.5 h-2.5',
		lg: 'w-3 h-3',
		xl: 'w-4 h-4',
	};

	// Status colors
	const statusColors = {
		online: 'bg-success-500',
		offline: 'bg-neutral-400',
		typing: 'bg-brand-500 animate-pulse',
	};

	// Compute classes
	const avatarClasses = $derived([
		'relative inline-flex items-center justify-center rounded-full',
		'bg-brand-100 dark:bg-brand-900',
		'text-brand-700 dark:text-brand-300',
		'font-semibold select-none',
		sizes[size],
	].join(' '));

	const initials = $derived(getInitials(name));
</script>

<div class="relative inline-block">
	<div class={avatarClasses}>
		{#if src}
			<img
				{src}
				alt={name}
				class="w-full h-full rounded-full object-cover"
			/>
		{:else}
			{initials}
		{/if}
	</div>

	{#if status}
		<span
			class={[
				'absolute bottom-0 right-0 block rounded-full ring-2 ring-white dark:ring-neutral-900',
				statusSizes[size],
				statusColors[status],
			].join(' ')}
			aria-label={`Status: ${status}`}
		></span>
	{/if}
</div>
