<script lang="ts">
	interface Props {
		disabled?: boolean;
		model?: string;
		onSend: (question: string) => void;
		onModelChange?: (model: string) => void;
		onSave?: () => void;
	}

	let { disabled = false, model = $bindable('sonnet'), onSend, onModelChange, onSave }: Props = $props();

	let input = $state('');

	function handleSubmit() {
		const q = input.trim();
		if (!q || disabled) return;
		onSend(q);
		input = '';
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit();
		}
	}

	const suggestions = [
		'Daily signups this month',
		'Cost by provider, last 30 days',
		'Top 10 users by sessions',
		'Cache hit rate trend',
	];
</script>

<div class="border-t border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-4">
	<!-- Suggestion chips (only when empty) -->
	{#if !input}
		<div class="flex flex-wrap gap-1.5 mb-3">
			{#each suggestions as s}
				<button
					class="text-xs px-2.5 py-1 rounded-full border border-neutral-200 dark:border-neutral-600 text-neutral-500 dark:text-neutral-400 hover:border-accent-300 dark:hover:border-accent-600 hover:text-accent-600 dark:hover:text-accent-400 transition-colors"
					{disabled}
					onclick={() => {
						input = s;
					}}
				>
					{s}
				</button>
			{/each}
		</div>
	{/if}

	<div class="flex items-end gap-2">
		<!-- Model toggle -->
		<div class="flex items-center gap-1 shrink-0">
			<button
				class="text-xs px-2 py-1.5 rounded {model === 'sonnet'
					? 'bg-accent-100 dark:bg-accent-900/30 text-accent-700 dark:text-accent-300 font-medium'
					: 'text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300'} transition-colors"
				onclick={() => {
					model = 'sonnet';
					onModelChange?.('sonnet');
				}}
			>
				Sonnet
			</button>
			<button
				class="text-xs px-2 py-1.5 rounded {model === 'opus'
					? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 font-medium'
					: 'text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300'} transition-colors"
				onclick={() => {
					model = 'opus';
					onModelChange?.('opus');
				}}
			>
				Opus
			</button>
		</div>

		<!-- Input -->
		<textarea
			bind:value={input}
			onkeydown={handleKeydown}
			placeholder="Ask about your data..."
			{disabled}
			rows="1"
			class="flex-1 resize-none rounded-lg border border-neutral-200 dark:border-neutral-600 bg-neutral-50 dark:bg-neutral-900 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-accent-500/30 focus:border-accent-400 disabled:opacity-50"
		></textarea>

		<!-- Send -->
		<button
			class="shrink-0 px-4 py-2 rounded-lg bg-accent-600 text-white text-sm font-medium hover:bg-accent-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
			{disabled}
			onclick={handleSubmit}
		>
			Send
		</button>

		<!-- Save -->
		{#if onSave}
			<button
				class="shrink-0 px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 text-neutral-600 dark:text-neutral-400 text-sm hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
				{disabled}
				onclick={onSave}
				title="Save analysis"
			>
				<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
					/>
				</svg>
			</button>
		{/if}
	</div>
</div>
