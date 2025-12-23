<script lang="ts">
	import { AlertTriangle, RotateCcw, Plus, AlertCircle } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';
	import { goto } from '$app/navigation';
	import PartialResultsPanel from './PartialResultsPanel.svelte';

	/**
	 * SubProblemResult from session state for partial success display
	 */
	export interface SubProblemResult {
		id: string;
		goal: string;
		synthesis: string;
		status: 'complete' | 'in_progress' | 'failed' | 'pending';
	}

	interface Props {
		errorType: string;
		errorMessage: string;
		sessionId: string;
		onRetry?: () => void;
		canRetry?: boolean;
		/** Partial results from completed sub-problems */
		subProblemResults?: SubProblemResult[];
		/** Total number of sub-problems in the meeting */
		totalSubProblems?: number;
		/** Current sub-problem index when failure occurred */
		currentSubProblemIndex?: number;
	}

	let {
		errorType,
		errorMessage,
		sessionId,
		onRetry,
		canRetry = true,
		subProblemResults = [],
		totalSubProblems = 0,
		currentSubProblemIndex = 0
	}: Props = $props();

	// Check if we have partial results to show
	const hasPartialResults = $derived(
		subProblemResults.length > 0 &&
		subProblemResults.some(r => r.status === 'complete' && r.synthesis)
	);

	// Calculate completed count
	const completedCount = $derived(
		subProblemResults.filter(r => r.status === 'complete').length
	);

	// Map error types to user-friendly messages
	const errorDisplayMap: Record<string, { title: string; description: string }> = {
		LLMError: {
			title: 'AI Service Unavailable',
			description: 'The AI service encountered an error. This is usually temporary.',
		},
		RateLimitError: {
			title: 'Rate Limit Reached',
			description: 'Too many requests. Please wait a moment before trying again.',
		},
		TimeoutError: {
			title: 'Request Timed Out',
			description: 'The operation took too long. The server may be under heavy load.',
		},
		ValidationError: {
			title: 'Invalid Request',
			description: 'There was a problem with the meeting configuration.',
		},
		default: {
			title: 'Meeting Failed',
			description: 'An unexpected error occurred during the meeting.',
		},
	};

	// Use partial success messaging when partial results are available
	const errorDisplay = $derived.by(() => {
		if (hasPartialResults) {
			return {
				title: 'Meeting Partially Complete',
				description: `${completedCount} of ${totalSubProblems || subProblemResults.length} focus areas completed successfully. You can view and use the completed results below.`,
			};
		}
		return errorDisplayMap[errorType] || errorDisplayMap['default'];
	});

	function handleStartNewMeeting() {
		goto('/meeting/new');
	}
</script>

<div class="space-y-6">
	<!-- Partial Results Panel (shown above error when available) -->
	{#if hasPartialResults}
		<PartialResultsPanel
			results={subProblemResults}
			{totalSubProblems}
		/>
	{/if}

	<!-- Error/Status Banner -->
	<div
		class="{hasPartialResults
			? 'bg-warning-50 dark:bg-warning-900/20 border-warning-200 dark:border-warning-800'
			: 'bg-error-50 dark:bg-error-900/20 border-error-200 dark:border-error-800'
		} border rounded-xl p-8 text-center"
		role="alert"
		aria-live="assertive"
	>
		<div class="flex flex-col items-center gap-4">
			<div class="w-16 h-16 rounded-full {hasPartialResults
				? 'bg-warning-100 dark:bg-warning-900/40'
				: 'bg-error-100 dark:bg-error-900/40'
			} flex items-center justify-center">
				{#if hasPartialResults}
					<AlertCircle size={32} class="text-warning-600 dark:text-warning-400" />
				{:else}
					<AlertTriangle size={32} class="text-error-600 dark:text-error-400" />
				{/if}
			</div>

			<div class="space-y-2">
				<h2 class="text-xl font-semibold {hasPartialResults
					? 'text-warning-900 dark:text-warning-100'
					: 'text-error-900 dark:text-error-100'
				}">
					{errorDisplay.title}
				</h2>
				<p class="text-sm {hasPartialResults
					? 'text-warning-700 dark:text-warning-300'
					: 'text-error-700 dark:text-error-300'
				} max-w-md mx-auto">
					{errorDisplay.description}
				</p>
			</div>

			{#if errorMessage}
				<details class="w-full max-w-md text-left">
					<summary class="text-xs {hasPartialResults
						? 'text-warning-600 dark:text-warning-400'
						: 'text-error-600 dark:text-error-400'
					} cursor-pointer hover:underline">
						Show technical details
					</summary>
					<pre class="mt-2 p-3 {hasPartialResults
						? 'bg-warning-100 dark:bg-warning-900/40 text-warning-800 dark:text-warning-200'
						: 'bg-error-100 dark:bg-error-900/40 text-error-800 dark:text-error-200'
					} rounded-lg text-xs overflow-x-auto whitespace-pre-wrap">{errorMessage}</pre>
				</details>
			{/if}

			<div class="flex items-center gap-3 mt-4">
				{#if canRetry && onRetry}
					<Button variant="brand" size="md" onclick={onRetry}>
						<RotateCcw size={16} />
						<span>Try Again</span>
					</Button>
				{/if}
				<Button variant="secondary" size="md" onclick={handleStartNewMeeting}>
					<Plus size={16} />
					<span>Start New Meeting</span>
				</Button>
			</div>

			<p class="text-xs {hasPartialResults
				? 'text-warning-500 dark:text-warning-400'
				: 'text-error-500 dark:text-error-400'
			} mt-2">
				Session ID: {sessionId}
			</p>
		</div>
	</div>
</div>
