<script lang="ts">
	import { Signal, SignalHigh, SignalLow, SignalZero, ExternalLink } from 'lucide-svelte';

	interface Props {
		/** UptimeRobot public status page URL (e.g., https://stats.uptimerobot.com/xxx) */
		statusPageUrl?: string | null;
		/** UptimeRobot monitor API key (read-only) for fetching status */
		monitorApiKey?: string | null;
	}

	let { statusPageUrl, monitorApiKey }: Props = $props();

	// Status states
	type UptimeStatus = 'up' | 'down' | 'paused' | 'unknown' | 'loading';

	let status = $state<UptimeStatus>('unknown');
	let uptimeRatio = $state<string | null>(null);
	let lastChecked = $state<Date | null>(null);
	let error = $state<string | null>(null);

	// If no configuration provided, show placeholder
	const isConfigured = $derived(statusPageUrl || monitorApiKey);
</script>

{#if isConfigured}
	<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-3">
				<div class="p-2 rounded-lg {status === 'up' ? 'bg-success-100 dark:bg-success-900/30' : status === 'down' ? 'bg-error-100 dark:bg-error-900/30' : 'bg-neutral-100 dark:bg-neutral-700'}">
					{#if status === 'up'}
						<SignalHigh class="w-5 h-5 text-success-600 dark:text-success-400" />
					{:else if status === 'down'}
						<SignalZero class="w-5 h-5 text-error-600 dark:text-error-400" />
					{:else if status === 'paused'}
						<SignalLow class="w-5 h-5 text-warning-600 dark:text-warning-400" />
					{:else}
						<Signal class="w-5 h-5 text-neutral-500 dark:text-neutral-400" />
					{/if}
				</div>
				<div>
					<div class="flex items-center gap-2">
						<p class="font-medium text-neutral-900 dark:text-white">External Monitoring</p>
						{#if status === 'up'}
							<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-400">
								Operational
							</span>
						{:else if status === 'down'}
							<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-400">
								Down
							</span>
						{:else if status === 'paused'}
							<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-400">
								Paused
							</span>
						{:else}
							<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400">
								Check Status Page
							</span>
						{/if}
					</div>
					<p class="text-xs text-neutral-500 dark:text-neutral-400">
						{#if uptimeRatio}
							{uptimeRatio}% uptime (30 days)
						{:else}
							UptimeRobot monitoring
						{/if}
					</p>
				</div>
			</div>

			{#if statusPageUrl}
				<a
					href={statusPageUrl}
					target="_blank"
					rel="noopener noreferrer"
					class="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded-lg transition-colors"
				>
					Status Page
					<ExternalLink class="w-4 h-4" />
				</a>
			{/if}
		</div>

		{#if error}
			<p class="mt-2 text-xs text-error-600 dark:text-error-400">{error}</p>
		{/if}
	</div>
{:else}
	<!-- Placeholder when not configured -->
	<div class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg border border-dashed border-neutral-300 dark:border-neutral-600 p-4">
		<div class="flex items-center gap-3">
			<div class="p-2 bg-neutral-100 dark:bg-neutral-700 rounded-lg">
				<Signal class="w-5 h-5 text-neutral-400 dark:text-neutral-500" />
			</div>
			<div>
				<p class="font-medium text-neutral-500 dark:text-neutral-400">External Monitoring</p>
				<p class="text-xs text-neutral-400 dark:text-neutral-500">
					Configure UptimeRobot to enable status badge
				</p>
			</div>
		</div>
	</div>
{/if}
