<script lang="ts">
	/**
	 * StatCard - Reusable stat display card
	 *
	 * Two layout modes:
	 * 1. Simple (no children): label + value + optional subtitle, icon on right
	 * 2. With children: icon + label header, then slot for StatCardRow list
	 */
	import type { Snippet } from 'svelte';

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	type IconComponent = new (...args: any[]) => any;

	interface Props {
		label: string;
		value?: string | number;
		subtitle?: string;
		icon?: IconComponent;
		iconColorClass?: string;
		iconBgClass?: string;
		size?: 'sm' | 'md';
		class?: string;
		children?: Snippet;
	}

	let {
		label,
		value,
		subtitle,
		icon: Icon,
		iconColorClass = 'text-neutral-600 dark:text-neutral-400',
		iconBgClass = 'bg-neutral-100 dark:bg-neutral-700',
		size = 'md',
		class: className = '',
		children
	}: Props = $props();

	const isMd = $derived(size === 'md');
</script>

<div
	class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 {isMd
		? 'p-6'
		: 'p-4'} {className}"
>
	{#if children}
		<!-- Header + rows layout -->
		{#if Icon}
			<div class="flex items-center gap-3 mb-4">
				<div class="p-3 {iconBgClass} rounded-lg">
					<Icon class="w-6 h-6 {iconColorClass}" />
				</div>
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">{label}</h3>
			</div>
		{:else}
			<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">{label}</h3>
		{/if}
		<div class="space-y-2">
			{@render children()}
		</div>
	{:else}
		<!-- Simple stat layout -->
		<div class="flex items-center justify-between">
			<div>
				<p class="{isMd ? 'text-sm' : 'text-xs'} text-neutral-600 dark:text-neutral-400 mb-1">{label}</p>
				<p class="{isMd ? 'text-2xl' : 'text-xl'} font-semibold text-neutral-900 dark:text-white">
					{value}
				</p>
				{#if subtitle}
					<p class="text-xs text-neutral-500 mt-1">{subtitle}</p>
				{/if}
			</div>
			{#if Icon}
				<div class="p-3 {iconBgClass} rounded-lg">
					<Icon class="w-6 h-6 {iconColorClass}" />
				</div>
			{/if}
		</div>
	{/if}
</div>
