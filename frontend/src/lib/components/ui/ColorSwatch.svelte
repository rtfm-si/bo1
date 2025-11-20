<script lang="ts">
	/**
	 * ColorSwatch Component - Reusable color display for design system
	 */

	import { textSizeClasses } from './utils';

	interface Props {
		color: string;
		shade: string | number;
		label?: string;
		size?: 'sm' | 'md' | 'lg';
	}

	let { color, shade, label, size = 'md' }: Props = $props();

	const sizeClasses = {
		sm: 'h-12 w-12',
		md: 'h-24 w-24',
		lg: 'h-32 w-32',
	};

	// Convert size to ComponentSize for textSizeClasses
	const textSize = $derived(textSizeClasses(size === 'sm' ? 'xs' : size === 'md' ? 'sm' : 'md'));
</script>

<div class="text-center">
	<div
		class="{sizeClasses[size]} rounded-lg border-2 border-neutral-200 dark:border-neutral-700 mb-2 flex items-center justify-center text-white font-bold {textSize} shadow-md"
		style="background-color: {color};"
	>
		{shade}
	</div>
	<div class="text-xs font-mono text-neutral-600 dark:text-neutral-400">
		{label || color}
	</div>
</div>
