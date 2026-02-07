<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { slide } from 'svelte/transition';
	import { env } from '$env/dynamic/public';
	import { createLogger } from '$lib/utils/debug';
	import { AlertTriangle, X, XCircle } from 'lucide-svelte';

	const log = createLogger('ServiceStatusBanner');

	interface ServiceStatus {
		status: 'operational' | 'degraded' | 'outage';
		message: string | null;
		services: Array<{ name: string; status: string }> | null;
		timestamp: string;
	}

	// State
	let status = $state<ServiceStatus | null>(null);
	let dismissed = $state(false);
	let lastStatus = $state<string | null>(null);
	let pollInterval: ReturnType<typeof setInterval> | null = null;

	// Derived
	const showBanner = $derived(
		status !== null &&
			status.status !== 'operational' &&
			!dismissed
	);

	const isOutage = $derived(status?.status === 'outage');
	const isDegraded = $derived(status?.status === 'degraded');

	async function fetchStatus() {
		try {
			const response = await fetch(`${env.PUBLIC_API_URL}/api/v1/status`);
			if (!response.ok) {
				log.error('Failed to fetch status:', response.status);
				return;
			}
			const data: ServiceStatus = await response.json();

			// Check if status changed (to show banner again after dismissal)
			if (lastStatus !== null && lastStatus !== data.status) {
				log.log('Status changed:', lastStatus, '->', data.status);
				dismissed = false; // Reset dismissal on status change
			}

			lastStatus = data.status;
			status = data;
		} catch (err) {
			log.error('Error fetching status:', err);
			// On network error, assume degraded (can't reach API)
			if (status === null) {
				status = {
					status: 'degraded',
					message: 'Unable to check service status',
					services: null,
					timestamp: new Date().toISOString()
				};
			}
		}
	}

	function dismiss() {
		dismissed = true;
	}

	onMount(() => {
		// Initial fetch
		fetchStatus();

		// Poll every 60 seconds
		pollInterval = setInterval(fetchStatus, 60000);
	});

	onDestroy(() => {
		if (pollInterval) {
			clearInterval(pollInterval);
		}
	});
</script>

{#if showBanner}
	<div
		class="sticky top-0 z-50"
		transition:slide={{ duration: 200 }}
	>
		<div
			class={[
				'px-4 py-3 text-sm font-medium flex items-center justify-between gap-4',
				isOutage
					? 'bg-error-600 text-white dark:bg-error-700'
					: 'bg-warning-500 text-warning-950 dark:bg-warning-600 dark:text-warning-50'
			].join(' ')}
			role="alert"
			aria-live="polite"
		>
			<div class="flex items-center gap-3 flex-1">
				{#if isOutage}
					<XCircle class="h-5 w-5 flex-shrink-0" aria-hidden="true" />
				{:else}
					<AlertTriangle class="h-5 w-5 flex-shrink-0" aria-hidden="true" />
				{/if}
				<span>
					{status?.message || (isOutage
						? 'Some services are currently unavailable. We\'re working to restore them.'
						: 'Some features may be slow or unavailable. We\'re working on it.')}
				</span>
			</div>
			<button
				onclick={dismiss}
				class={[
					'p-1 rounded-md transition-colors flex-shrink-0',
					isOutage
						? 'hover:bg-error-700 dark:hover:bg-error-800'
						: 'hover:bg-warning-600 dark:hover:bg-warning-700'
				].join(' ')}
				aria-label="Dismiss status message"
			>
				<X class="h-4 w-4" aria-hidden="true" />
			</button>
		</div>
	</div>
{/if}
