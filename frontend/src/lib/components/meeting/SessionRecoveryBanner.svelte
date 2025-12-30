<script lang="ts">
	/**
	 * SessionRecoveryBanner Component
	 * Shows when a session has incomplete sub-problems with a valid checkpoint.
	 * Allows user to resume from last checkpoint or start over.
	 */
	import { RefreshCw, Play, RotateCcw } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';

	interface Props {
		/** Session ID */
		sessionId: string;
		/** Number of completed sub-problems */
		completedSubProblems: number;
		/** Total number of sub-problems */
		totalSubProblems: number;
		/** When the checkpoint was saved */
		lastCheckpointAt: string | null;
		/** Whether resume operation is in progress */
		resuming?: boolean;
		/** Callback when user clicks Resume */
		onResume: () => void;
		/** Callback when user clicks Start Over */
		onStartOver: () => void;
	}

	let {
		sessionId,
		completedSubProblems,
		totalSubProblems,
		lastCheckpointAt,
		resuming = false,
		onResume,
		onStartOver
	}: Props = $props();

	// Format checkpoint time
	const formattedTime = $derived.by(() => {
		if (!lastCheckpointAt) return 'Unknown';
		const date = new Date(lastCheckpointAt);
		return date.toLocaleTimeString(undefined, {
			hour: '2-digit',
			minute: '2-digit'
		});
	});

	const nextSubProblemNumber = $derived(completedSubProblems + 1);
</script>

<div
	class="bg-warning-50 dark:bg-warning-900/30 border border-warning-200 dark:border-warning-800 rounded-lg p-4"
	role="alert"
	aria-live="polite"
>
	<div class="flex items-start gap-4">
		<div class="flex-shrink-0 mt-0.5">
			<RefreshCw size={20} class="text-warning-600 dark:text-warning-400" />
		</div>

		<div class="flex-1 min-w-0">
			<h4 class="text-sm font-medium text-warning-900 dark:text-warning-100">
				Session can be resumed
			</h4>
			<p class="text-sm text-warning-700 dark:text-warning-300 mt-1">
				{completedSubProblems} of {totalSubProblems} focus areas completed.
				Resume from focus area {nextSubProblemNumber}?
			</p>
			{#if lastCheckpointAt}
				<p class="text-xs text-warning-600 dark:text-warning-400 mt-1">
					Last checkpoint: {formattedTime}
				</p>
			{/if}
		</div>

		<div class="flex-shrink-0 flex gap-2">
			<Button
				variant="outline"
				size="sm"
				onclick={onStartOver}
				disabled={resuming}
			>
				<RotateCcw size={14} class="mr-1" />
				Start Over
			</Button>
			<Button
				variant="brand"
				size="sm"
				onclick={onResume}
				disabled={resuming}
			>
				{#if resuming}
					<RefreshCw size={14} class="mr-1 animate-spin" />
					Resuming...
				{:else}
					<Play size={14} class="mr-1" />
					Resume
				{/if}
			</Button>
		</div>
	</div>
</div>
