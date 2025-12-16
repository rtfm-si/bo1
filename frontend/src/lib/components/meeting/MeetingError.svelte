<script lang="ts">
	import { AlertTriangle, RotateCcw, Plus } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';
	import { goto } from '$app/navigation';

	interface Props {
		errorType: string;
		errorMessage: string;
		sessionId: string;
		onRetry?: () => void;
		canRetry?: boolean;
	}

	let { errorType, errorMessage, sessionId, onRetry, canRetry = true }: Props = $props();

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

	const errorDisplay = $derived(errorDisplayMap[errorType] || errorDisplayMap['default']);

	function handleStartNewMeeting() {
		goto('/meeting/new');
	}
</script>

<div
	class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-xl p-8 text-center"
	role="alert"
	aria-live="assertive"
>
	<div class="flex flex-col items-center gap-4">
		<div class="w-16 h-16 rounded-full bg-error-100 dark:bg-error-900/40 flex items-center justify-center">
			<AlertTriangle size={32} class="text-error-600 dark:text-error-400" />
		</div>

		<div class="space-y-2">
			<h2 class="text-xl font-semibold text-error-900 dark:text-error-100">
				{errorDisplay.title}
			</h2>
			<p class="text-sm text-error-700 dark:text-error-300 max-w-md mx-auto">
				{errorDisplay.description}
			</p>
		</div>

		{#if errorMessage}
			<details class="w-full max-w-md text-left">
				<summary class="text-xs text-error-600 dark:text-error-400 cursor-pointer hover:underline">
					Show technical details
				</summary>
				<pre class="mt-2 p-3 bg-error-100 dark:bg-error-900/40 rounded-lg text-xs text-error-800 dark:text-error-200 overflow-x-auto whitespace-pre-wrap">{errorMessage}</pre>
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

		<p class="text-xs text-error-500 dark:text-error-400 mt-2">
			Session ID: {sessionId}
		</p>
	</div>
</div>
