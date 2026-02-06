<script lang="ts">
	import { Users } from 'lucide-svelte';

	interface ExpertInfo {
		persona: {
			code: string;
			name: string;
			archetype?: string;
			display_name?: string;
			domain_expertise?: string[];
		};
		rationale: string;
		order: number;
	}

	interface Props {
		experts: ExpertInfo[];
		subProblemGoal?: string;
	}

	let { experts, subProblemGoal }: Props = $props();
</script>

<div class="bg-neutral-50 dark:bg-neutral-900/50 rounded-lg p-5 border border-neutral-200 dark:border-neutral-700 shadow-sm">
	<h3 class="text-base font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
		<Users size={20} class="text-brand-600 dark:text-brand-400" />
		<span>Expert Panel Assembled</span>
	</h3>

	<!-- Sub-problem Context (if available) -->
	{#if subProblemGoal}
		<div class="mb-4 p-3 bg-white/60 dark:bg-slate-800/50 rounded-md border border-blue-200 dark:border-blue-800">
			<p class="text-xs font-medium text-slate-700 dark:text-slate-300">
				<span class="text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wide">Addressing:</span>
				<span class="ml-1">{subProblemGoal}</span>
			</p>
		</div>
	{/if}

	<!-- Expert Grid (columns for better visual hierarchy with 2-5 experts) -->
	<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
		{#each experts as expert}
			<div class="relative bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm p-3 flex flex-col">
				<!-- Order Badge (top-right corner) -->
				<div class="absolute -top-2 -right-2 w-6 h-6 bg-brand-500 dark:bg-brand-600 rounded-full flex items-center justify-center text-white font-semibold text-xs shadow-sm">
					{expert.order}
				</div>

				<!-- Expert Info -->
				<div class="text-center mb-2">
					<h4 class="font-semibold text-slate-900 dark:text-white text-sm truncate">
						{expert.persona.name}
					</h4>

					{#if expert.persona.archetype}
						<p class="text-xs font-medium text-brand-600 dark:text-brand-400 truncate">
							{expert.persona.archetype}
						</p>
					{/if}

				</div>

				<!-- Rationale (expandable on hover/focus) -->
				{#if expert.rationale}
					<div class="flex-1 mt-auto pt-2 border-t border-slate-100 dark:border-slate-700">
						<p class="text-xs text-slate-600 dark:text-slate-300 leading-relaxed line-clamp-3" title={expert.rationale}>
							{expert.rationale}
						</p>
					</div>
				{/if}
			</div>
		{/each}
	</div>
</div>
