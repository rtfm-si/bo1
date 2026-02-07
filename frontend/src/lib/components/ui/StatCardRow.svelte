<script lang="ts">
	/**
	 * StatCardRow - A label/value row for use inside StatCard
	 */
	interface Props {
		label: string;
		value: string | number;
		valueColorClass?: string;
		prominent?: boolean;
	}

	let {
		label,
		value,
		valueColorClass = '',
		prominent = false
	}: Props = $props();
</script>

<div class="flex justify-between items-center">
	<span class="text-sm text-neutral-600 dark:text-neutral-400">{label}</span>
	<span
		class="{prominent
			? 'text-lg font-semibold text-neutral-900 dark:text-white'
			: 'text-sm font-medium text-neutral-700 dark:text-neutral-300'} {valueColorClass}"
	>
		{value}
	</span>
</div>
