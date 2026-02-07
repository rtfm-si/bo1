<script lang="ts">
	/**
	 * PanelCard - Card with optional icon-header, used for accordion-based panels
	 */
	import type { Snippet } from 'svelte';

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	type IconComponent = new (...args: any[]) => any;

	interface Props {
		title?: string;
		subtitle?: string;
		icon?: IconComponent;
		iconColorClass?: string;
		iconBgClass?: string;
		headerRight?: Snippet;
		noPadding?: boolean;
		class?: string;
		children?: Snippet;
	}

	let {
		title,
		subtitle,
		icon,
		iconColorClass = 'text-neutral-600 dark:text-neutral-400',
		iconBgClass = 'bg-neutral-100 dark:bg-neutral-700',
		headerRight,
		noPadding = false,
		class: className = '',
		children
	}: Props = $props();
</script>

<div
	class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 overflow-hidden {className}"
>
	{#if title}
		<div class="border-b border-neutral-200 dark:border-neutral-700 p-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					{#if icon}
						{@const Icon = icon}
						<Icon class="w-5 h-5 {iconColorClass}" />
					{/if}
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">{title}</h3>
				</div>
				{#if headerRight}
					{@render headerRight()}
				{/if}
			</div>
			{#if subtitle}
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{subtitle}</p>
			{/if}
		</div>
	{/if}
	{#if !noPadding}
		<div class="p-4">
			{@render children?.()}
		</div>
	{:else}
		{@render children?.()}
	{/if}
</div>
