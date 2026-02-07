<script lang="ts">
	import type { Snippet, ComponentType } from 'svelte';

	interface Props {
		title: string;
		icon?: ComponentType;
		backHref?: string;
		badge?: Snippet;
		actions?: Snippet;
	}

	let { title, icon, backHref = '/admin', badge, actions }: Props = $props();
</script>

<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
	<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-4">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-4">
				<a
					href={backHref}
					class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
					aria-label="Back to admin dashboard"
				>
					<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
					</svg>
				</a>
				<div class="flex items-center gap-2">
					{#if icon}
						<svelte:component this={icon} class="w-6 h-6 text-brand-600 dark:text-brand-400" />
					{/if}
					<h1 class="text-xl font-semibold text-neutral-900 dark:text-white">{title}</h1>
				</div>
				{#if badge}
					{@render badge()}
				{/if}
			</div>
			{#if actions}
				<div class="flex items-center gap-2">
					{@render actions()}
				</div>
			{/if}
		</div>
	</div>
</header>
