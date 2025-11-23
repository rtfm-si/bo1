<script lang="ts">
	import { Users } from 'lucide-svelte';

	interface ExpertInfo {
		persona: {
			code: string;
			name: string;
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

	<!-- Expert Cards -->
	<div class="space-y-2.5">
		{#each experts as expert}
			<div class="flex items-start gap-3 p-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
				<!-- Order Badge (remove redundant avatar with first letter) -->
				<div class="flex-shrink-0 w-8 h-8 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center text-brand-700 dark:text-brand-300 font-semibold text-sm border border-brand-200 dark:border-brand-800">
					{expert.order}
				</div>

				<!-- Expert Info -->
				<div class="flex-1 min-w-0">
					<h4 class="font-semibold text-slate-900 dark:text-white text-sm">
						{expert.persona.name}
					</h4>

					{#if expert.persona.domain_expertise && expert.persona.domain_expertise.length > 0}
						<p class="text-xs text-slate-600 dark:text-slate-400 mb-2">
							{expert.persona.domain_expertise.slice(0, 2).join(', ')}
						</p>
					{/if}

					<!-- WHY this expert for THIS sub-problem -->
					{#if expert.rationale}
						<div class="mt-2 p-2.5 bg-blue-50 dark:bg-blue-900/30 rounded-md border-l-3 border-blue-500">
							<p class="text-xs font-medium text-blue-900 dark:text-blue-100 mb-0.5">
								Why {expert.persona.name.split(' ')[0]}?
							</p>
							<p class="text-xs text-blue-800 dark:text-blue-200 leading-relaxed">
								{expert.rationale}
							</p>
						</div>
					{/if}
				</div>
			</div>
		{/each}
	</div>
</div>
