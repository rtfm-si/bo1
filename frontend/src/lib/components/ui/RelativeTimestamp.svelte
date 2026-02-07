<script lang="ts">
	/**
	 * RelativeTimestamp Component
	 * Displays time relative to now (e.g., "2 minutes ago")
	 * with hover tooltip showing absolute time
	 */
	import { onMount } from 'svelte';
	import { formatRelativeTime, formatAbsoluteTime } from '$lib/utils/time-formatting';

	interface Props {
		timestamp: string;
	}

	let { timestamp }: Props = $props();

	// Counter to trigger periodic recalculation of relative time
	let refreshCounter = $state(0);

	// Set up periodic updates every minute
	onMount(() => {
		const interval = setInterval(() => {
			refreshCounter++;
		}, 60000);
		return () => clearInterval(interval);
	});

	// Derive relative time - recalculates when timestamp or refreshCounter changes
	const relativeTime = $derived.by(() => {
		void refreshCounter; // Create dependency on refresh counter
		return formatRelativeTime(timestamp);
	});
</script>

<span
	class="text-xs text-neutral-500 dark:text-neutral-400 cursor-help"
	title={formatAbsoluteTime(timestamp)}
>
	{relativeTime}
</span>
