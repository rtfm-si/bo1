<script lang="ts">
	/**
	 * NoContextFallback - Prompts user to set up business context before analysis
	 *
	 * Shows when user has no business context AND no objective analysis exists.
	 * Offers: "Set up business context" link, "Analyze anyway" button, and
	 * a quick inline input for a simple goal.
	 */

	interface Props {
		onSetupContext: () => void;
		onAnalyzeAnyway: () => void;
		onQuickGoalSubmit: (goal: string) => void;
		loading?: boolean;
	}

	let { onSetupContext, onAnalyzeAnyway, onQuickGoalSubmit, loading = false }: Props = $props();

	let quickGoal = $state('');
	let showQuickSetup = $state(false);

	function handleQuickSubmit() {
		if (quickGoal.trim()) {
			onQuickGoalSubmit(quickGoal.trim());
		}
	}
</script>

<div class="bg-gradient-to-br from-brand-50 to-purple-50 dark:from-brand-900/20 dark:to-purple-900/20 rounded-lg border border-brand-200 dark:border-brand-800 p-6">
	<!-- Header with lightbulb icon -->
	<div class="flex items-start gap-4 mb-4">
		<div class="flex-shrink-0 p-2.5 rounded-xl bg-brand-100 dark:bg-brand-900/40">
			<svg class="w-6 h-6 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
			</svg>
		</div>
		<div class="flex-1">
			<h3 class="text-lg font-semibold text-brand-900 dark:text-brand-100 mb-1">
				Get More Relevant Insights
			</h3>
			<p class="text-sm text-brand-700 dark:text-brand-300">
				I can analyze this data, but I'll give you better insights if I know what you're trying to achieve.
			</p>
		</div>
	</div>

	<!-- Action buttons -->
	<div class="flex flex-wrap items-center gap-3 mb-4">
		<button
			onclick={onSetupContext}
			disabled={loading}
			class="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:bg-brand-400 text-white rounded-lg text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
			</svg>
			Set up business context
		</button>
		<button
			onclick={onAnalyzeAnyway}
			disabled={loading}
			class="inline-flex items-center gap-2 px-4 py-2 text-brand-700 dark:text-brand-300 hover:bg-brand-100 dark:hover:bg-brand-900/30 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
		>
			{#if loading}
				<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				Analyzing...
			{:else}
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
				</svg>
				Analyze anyway
			{/if}
		</button>
	</div>

	<!-- Quick setup section -->
	<div class="border-t border-brand-200 dark:border-brand-700 pt-4">
		{#if !showQuickSetup}
			<button
				onclick={() => showQuickSetup = true}
				class="text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 font-medium transition-colors"
			>
				Quick setup - just tell me your main goal
			</button>
		{:else}
			<div class="space-y-3">
				<label for="quick-goal" class="block text-sm font-medium text-brand-700 dark:text-brand-300">
					What's your main business goal right now?
				</label>
				<div class="flex gap-2">
					<input
						id="quick-goal"
						type="text"
						bind:value={quickGoal}
						placeholder="e.g., Increase customer retention by 20%"
						disabled={loading}
						class="flex-1 px-4 py-2.5 rounded-lg border border-brand-300 dark:border-brand-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent disabled:opacity-50"
						onkeydown={(e) => e.key === 'Enter' && handleQuickSubmit()}
					/>
					<button
						onclick={handleQuickSubmit}
						disabled={!quickGoal.trim() || loading}
						class="px-4 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:bg-brand-400 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
					>
						{#if loading}
							<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
						{:else}
							Go
						{/if}
					</button>
				</div>
				<p class="text-xs text-brand-500 dark:text-brand-400">
					This will be saved to your business context for future analyses.
				</p>
			</div>
		{/if}
	</div>
</div>
