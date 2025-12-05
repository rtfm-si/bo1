<script lang="ts">
	/**
	 * Breadcrumb Component - Navigation path indicator
	 */
	import { ChevronRight, Home } from 'lucide-svelte';
	import type { BreadcrumbItem } from '$lib/utils/breadcrumbs';

	interface Props {
		items: BreadcrumbItem[];
		showHome?: boolean;
		class?: string;
	}

	let { items, showHome = true, class: className = '' }: Props = $props();

	// Don't show breadcrumbs if only one item (the current page)
	const shouldShow = $derived(items.length > 1 || showHome);
</script>

{#if shouldShow}
	<nav aria-label="Breadcrumb" class="flex items-center text-sm {className}">
		<ol class="flex items-center gap-1 flex-wrap">
			{#if showHome}
				<li class="flex items-center">
					<a
						href="/dashboard"
						class="text-neutral-500 hover:text-brand-600 dark:text-neutral-400 dark:hover:text-brand-400 transition-colors"
						aria-label="Home"
					>
						<Home class="w-4 h-4" />
					</a>
				</li>
				{#if items.length > 0}
					<li class="flex items-center">
						<ChevronRight class="w-4 h-4 text-neutral-400 dark:text-neutral-500 mx-1" />
					</li>
				{/if}
			{/if}

			{#each items as item, i (item.href)}
				<li class="flex items-center">
					{#if item.isCurrent}
						<span
							class="text-neutral-900 dark:text-white font-medium truncate max-w-[200px]"
							aria-current="page"
						>
							{item.label}
						</span>
					{:else}
						<a
							href={item.href}
							class="text-neutral-500 hover:text-brand-600 dark:text-neutral-400 dark:hover:text-brand-400 transition-colors truncate max-w-[200px]"
						>
							{item.label}
						</a>
					{/if}
				</li>

				{#if i < items.length - 1}
					<li class="flex items-center">
						<ChevronRight class="w-4 h-4 text-neutral-400 dark:text-neutral-500 mx-1" />
					</li>
				{/if}
			{/each}
		</ol>
	</nav>
{/if}
