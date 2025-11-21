<script lang="ts">
	/**
	 * RelativeTimestamp Component
	 * Displays time relative to now (e.g., "2 minutes ago")
	 * with hover tooltip showing absolute time
	 */
	import { formatRelativeTime, formatAbsoluteTime } from '$lib/utils/time-formatting';

	interface Props {
		timestamp: string;
	}

	let { timestamp }: Props = $props();

	let relativeTime = $state(formatRelativeTime(timestamp));

	// Update every minute
	$effect(() => {
		const interval = setInterval(() => {
			relativeTime = formatRelativeTime(timestamp);
		}, 60000); // 60 seconds

		return () => clearInterval(interval);
	});
</script>

<span
	class="text-xs text-slate-500 dark:text-slate-400 cursor-help"
	title={formatAbsoluteTime(timestamp)}
>
	{relativeTime}
</span>
