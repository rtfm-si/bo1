<script lang="ts">
	import type { Snippet, ComponentType } from 'svelte';

	interface Props {
		title: string;
		description?: string;
		icon?: ComponentType;
		actions?: Snippet;
	}

	let { title, description, icon, actions }: Props = $props();
</script>

<div class="text-center py-12">
	{#if icon}
		<svelte:component this={icon} class="w-12 h-12 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" />
	{/if}
	<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-2">{title}</h3>
	{#if description}
		<p class="text-neutral-500 dark:text-neutral-400 mb-4">{description}</p>
	{/if}
	{#if actions}
		<div class="flex justify-center gap-3">
			{@render actions()}
		</div>
	{/if}
</div>
