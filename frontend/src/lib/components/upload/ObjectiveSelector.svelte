<script lang="ts">
	/**
	 * ObjectiveSelector - Radio-style list of user objectives for pre-selection
	 * Used on the upload page for the "What data do I need?" flow
	 */

	interface Objective {
		index: number;
		name: string;
		requirements_summary?: string;
		current_value?: string | null;
		target_value?: string | null;
	}

	let {
		objectives = [],
		selectedIndex = null,
		onSelect,
		loading = false,
	}: {
		objectives: Objective[];
		selectedIndex: number | null;
		onSelect: (index: number) => void;
		loading?: boolean;
	} = $props();

	function handleKeyDown(event: KeyboardEvent, index: number) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			onSelect(index);
		}
	}
</script>

<div class="space-y-2" role="radiogroup" aria-label="Select an objective">
	{#if loading}
		<div class="flex items-center justify-center py-8">
			<svg
				class="w-6 h-6 text-brand-500 animate-spin"
				fill="none"
				viewBox="0 0 24 24"
			>
				<circle
					class="opacity-25"
					cx="12"
					cy="12"
					r="10"
					stroke="currentColor"
					stroke-width="4"
				></circle>
				<path
					class="opacity-75"
					fill="currentColor"
					d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
				></path>
			</svg>
			<span class="ml-2 text-neutral-600 dark:text-neutral-400">Loading objectives...</span>
		</div>
	{:else if objectives.length === 0}
		<div class="text-center py-8 text-neutral-600 dark:text-neutral-400">
			<p>No objectives found.</p>
			<p class="text-sm mt-1">Set up your business context to see objectives.</p>
		</div>
	{:else}
		{#each objectives as objective (objective.index)}
			{@const isSelected = selectedIndex === objective.index}
			<button
				type="button"
				role="radio"
				aria-checked={isSelected}
				tabindex={0}
				onclick={() => onSelect(objective.index)}
				onkeydown={(e) => handleKeyDown(e, objective.index)}
				class="w-full text-left px-4 py-3 rounded-lg border transition-all duration-150
					{isSelected
					? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20 ring-2 ring-brand-500/20'
					: 'border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 bg-white dark:bg-neutral-800'}"
			>
				<div class="flex items-start gap-3">
					<!-- Radio indicator -->
					<span
						class="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center
							{isSelected
							? 'border-brand-500 bg-brand-500'
							: 'border-neutral-300 dark:border-neutral-600'}"
					>
						{#if isSelected}
							<span class="w-2 h-2 rounded-full bg-white"></span>
						{/if}
					</span>

					<!-- Objective content -->
					<div class="flex-1 min-w-0">
						<p class="font-medium text-neutral-900 dark:text-white truncate">
							{objective.name}
						</p>
						{#if objective.current_value || objective.target_value}
							<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
								{#if objective.current_value && objective.target_value}
									{objective.current_value} / {objective.target_value}
								{:else if objective.target_value}
									Target: {objective.target_value}
								{:else if objective.current_value}
									Current: {objective.current_value}
								{/if}
							</p>
						{/if}
						{#if objective.requirements_summary}
							<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-2">
								{objective.requirements_summary}
							</p>
						{/if}
					</div>
				</div>
			</button>
		{/each}
	{/if}
</div>
