<script lang="ts">
	interface Props {
		sql: string;
		expanded?: boolean;
	}

	let { sql, expanded = $bindable(false) }: Props = $props();
</script>

<div class="mt-2">
	<button
		class="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 transition-colors"
		onclick={() => (expanded = !expanded)}
	>
		<svg
			class="w-3.5 h-3.5 transition-transform {expanded ? 'rotate-90' : ''}"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
		</svg>
		SQL
	</button>
	{#if expanded}
		<pre
			class="mt-2 p-3 bg-neutral-900 dark:bg-neutral-950 text-neutral-200 text-xs rounded-lg overflow-x-auto font-mono leading-relaxed"
		>{sql}</pre>
	{/if}
</div>
