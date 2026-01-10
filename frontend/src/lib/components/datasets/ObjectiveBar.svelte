<script lang="ts">
	/**
	 * ObjectiveBar - Shows which objectives are being analyzed
	 *
	 * Collapsible bar that displays the objectives linked to this analysis
	 * with an option to change objectives.
	 */
	import { slide } from 'svelte/transition';

	interface Props {
		objectives: string[];
		relevanceScore?: number | null;
		analysisMode?: 'objective_focused' | 'open_exploration';
		loading?: boolean;
		onChangeObjectives?: () => void;
	}

	let { objectives, relevanceScore = null, analysisMode = 'objective_focused', loading = false, onChangeObjectives }: Props = $props();

	let collapsed = $state(false);

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			collapsed = !collapsed;
		} else if (event.key === 'Escape') {
			collapsed = true;
		}
	}

	function getRelevanceColor(score: number): string {
		if (score >= 70) return 'text-success-600 dark:text-success-400';
		if (score >= 40) return 'text-warning-600 dark:text-warning-400';
		return 'text-neutral-500 dark:text-neutral-400';
	}

	function getRelevanceBg(score: number): string {
		if (score >= 70) return 'bg-success-100 dark:bg-success-900/30';
		if (score >= 40) return 'bg-warning-100 dark:bg-warning-900/30';
		return 'bg-neutral-100 dark:bg-neutral-700';
	}
</script>

{#if loading}
	<!-- Loading state -->
	<div class="bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-800 p-4 animate-pulse">
		<div class="flex items-center gap-3">
			<div class="w-8 h-8 rounded-lg bg-brand-100 dark:bg-brand-900/40"></div>
			<div class="space-y-2 flex-1">
				<div class="h-4 w-24 bg-brand-100 dark:bg-brand-900/40 rounded"></div>
				<div class="h-3 w-48 bg-brand-100 dark:bg-brand-900/40 rounded"></div>
			</div>
		</div>
	</div>
{:else}
<div class="bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-800 overflow-hidden">
	<!-- Header (always visible) -->
	<button
		onclick={() => (collapsed = !collapsed)}
		onkeydown={handleKeyDown}
		aria-expanded={!collapsed}
		aria-controls="objective-bar-content"
		class="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-brand-100/50 dark:hover:bg-brand-900/30 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-inset"
	>
		<div class="flex items-center gap-3">
			<div class="p-1.5 rounded-lg bg-brand-100 dark:bg-brand-900/40">
				<svg class="w-4 h-4 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
				</svg>
			</div>
			<div>
				<span class="text-sm font-medium text-brand-700 dark:text-brand-300">
					{#if analysisMode === 'objective_focused'}
						Analyzing for:
					{:else}
						Open exploration
					{/if}
				</span>
				{#if objectives.length > 0 && !collapsed}
					<span class="text-sm text-brand-600 dark:text-brand-400 ml-1">
						{objectives.slice(0, 2).join(' | ')}
						{#if objectives.length > 2}
							<span class="text-brand-500"> +{objectives.length - 2} more</span>
						{/if}
					</span>
				{/if}
			</div>
		</div>
		<div class="flex items-center gap-3">
			{#if relevanceScore !== null}
				<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {getRelevanceBg(relevanceScore)} {getRelevanceColor(relevanceScore)}">
					{relevanceScore}% aligned
				</span>
			{/if}
			<svg
				class="w-5 h-5 text-brand-500 transition-transform {collapsed ? '' : 'rotate-180'}"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</div>
	</button>

	<!-- Expanded content -->
	{#if !collapsed}
		<div id="objective-bar-content" class="px-4 pb-4 pt-1 border-t border-brand-200 dark:border-brand-800" transition:slide={{ duration: 200 }}>
			{#if analysisMode === 'objective_focused' && objectives.length > 0}
				<div class="flex flex-wrap gap-2 mb-3">
					{#each objectives as objective, i}
						<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300">
							<span class="w-4 h-4 flex items-center justify-center rounded-full bg-brand-200 dark:bg-brand-800 text-[10px]">
								{i + 1}
							</span>
							{objective}
						</span>
					{/each}
				</div>
			{:else if analysisMode === 'open_exploration'}
				<p class="text-xs text-brand-600 dark:text-brand-400 mb-3">
					No specific objectives linked. Analyzing for general patterns and insights.
				</p>
			{:else}
				<p class="text-xs text-brand-600 dark:text-brand-400 mb-3">
					No objectives configured. Set up your business context to get objective-aligned insights.
				</p>
			{/if}

			{#if onChangeObjectives}
				<button
					onclick={onChangeObjectives}
					class="inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 transition-colors focus:outline-none focus-visible:underline"
				>
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
					Change objectives
				</button>
			{/if}
		</div>
	{/if}
</div>
{/if}
