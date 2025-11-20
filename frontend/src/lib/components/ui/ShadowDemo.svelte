<script lang="ts">
	/**
	 * ShadowDemo Component - Reusable shadow showcase
	 */

	interface Props {
		shadowClass: string;
		label: string;
		description?: string;
	}

	let { shadowClass, label, description }: Props = $props();
</script>

<div class="bg-white dark:bg-neutral-900 p-8 rounded-lg {shadowClass} text-center">
	<code class="text-sm font-mono text-brand-600 dark:text-brand-400">{label}</code>
	{#if description}
		<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-2">{description}</p>
	{/if}
</div>
