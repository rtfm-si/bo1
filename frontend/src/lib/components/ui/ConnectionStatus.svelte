<script lang="ts">
	/**
	 * ConnectionStatus - Compact inline connection state indicator
	 *
	 * Shows current connection state (connecting, connected, retrying, error)
	 * with visual indicators and optional retry functionality.
	 *
	 * Props:
	 * - status: 'connecting' | 'connected' | 'retrying' | 'error'
	 * - retryCount?: number - Current retry attempt (shown during retrying state)
	 * - maxRetries?: number - Maximum retry attempts (shown during retrying state)
	 * - onRetry?: () => void - Callback for manual retry button
	 */

	import { Wifi, WifiOff, RotateCw, AlertCircle } from 'lucide-svelte';

	interface Props {
		status: 'connecting' | 'connected' | 'retrying' | 'error';
		retryCount?: number;
		maxRetries?: number;
		onRetry?: () => void;
	}

	let { status, retryCount = 0, maxRetries = 3, onRetry }: Props = $props();

	// Derive visual state based on status
	const statusConfig = $derived.by(() => {
		switch (status) {
			case 'connecting':
				return {
					icon: Wifi,
					label: 'Connecting...',
					color: 'text-neutral-500 dark:text-neutral-400',
					bgColor: 'bg-neutral-100 dark:bg-neutral-800',
					animate: true,
				};
			case 'connected':
				return {
					icon: Wifi,
					label: 'Connected',
					color: 'text-[hsl(142,76%,36%)] dark:text-[hsl(142,76%,60%)]',
					bgColor: 'bg-[hsl(142,76%,95%)] dark:bg-[hsl(142,76%,20%)]',
					animate: false,
				};
			case 'retrying':
				return {
					icon: RotateCw,
					label: `Retrying (${retryCount}/${maxRetries})`,
					color: 'text-[hsl(38,92%,50%)] dark:text-[hsl(38,92%,70%)]',
					bgColor: 'bg-[hsl(38,92%,95%)] dark:bg-[hsl(38,92%,20%)]',
					animate: true,
				};
			case 'error':
				return {
					icon: WifiOff,
					label: 'Connection Lost',
					color: 'text-[hsl(0,84%,60%)] dark:text-[hsl(0,84%,70%)]',
					bgColor: 'bg-[hsl(0,84%,95%)] dark:bg-[hsl(0,84%,20%)]',
					animate: false,
				};
		}
	});
</script>

{#if statusConfig}
	{@const Icon = statusConfig.icon}
	<div
		class="inline-flex items-center gap-2 px-3 py-1.5 rounded-md {statusConfig.bgColor} transition-all duration-300"
	>
		<!-- Icon -->
		<Icon
			size={14}
			class="{statusConfig.color} {statusConfig.animate ? 'animate-pulse' : ''}"
		/>

		<!-- Label -->
		<span class="text-[0.75rem] font-medium {statusConfig.color}">
			{statusConfig.label}
		</span>

		<!-- Retry Button (only shown in error state with onRetry callback) -->
		{#if status === 'error' && onRetry}
			<button
				onclick={onRetry}
				class="ml-1 p-1 rounded hover:bg-black/5 dark:hover:bg-white/5 transition-colors duration-150"
				aria-label="Retry connection"
			>
				<RotateCw size={12} class={statusConfig.color} />
			</button>
		{/if}
	</div>
{/if}
