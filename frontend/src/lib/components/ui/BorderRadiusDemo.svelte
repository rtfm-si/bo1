<script lang="ts">
	/**
	 * BorderRadiusDemo Component - Reusable border radius showcase
	 */

	interface Props {
		roundedClass: string;
		label: string;
		pixelValue: string;
	}

	let { roundedClass, label, pixelValue }: Props = $props();
</script>

<div class="text-center">
	<div class="w-24 h-24 bg-brand-500 {roundedClass} mx-auto mb-3 shadow-md"></div>
	<code class="text-xs font-mono text-neutral-600 dark:text-neutral-400 block">{label}</code>
	<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-1">{pixelValue}</p>
</div>
