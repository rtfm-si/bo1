<script lang="ts" module>
	export { cardVariants, type CardVariant, type CardPadding } from './card-variants';
</script>

<script lang="ts">
	import type { HTMLAttributes } from "svelte/elements";
	import { cn, type WithElementRef } from "$lib/utils.js";
	import { cardVariants, type CardVariant, type CardPadding } from './card-variants';

	let {
		ref = $bindable(null),
		class: className,
		variant = "default" as CardVariant,
		padding = "default" as CardPadding,
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		variant?: CardVariant;
		padding?: CardPadding;
	} = $props();
</script>

<div
	bind:this={ref}
	data-slot="card"
	class={cn(cardVariants({ variant, padding }), className)}
	{...restProps}
>
	{@render children?.()}
</div>
