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

	<!-- Expert List (no individual cards, just rows) -->
	<div class="space-y-3">
		{#each experts as expert}
			<div class="flex flex-col md:flex-row md:items-start gap-2 md:gap-3">
				<!-- Left side: Order badge + Name + Expertise (fixed width for alignment on desktop) -->
				<div class="flex items-start gap-3 md:w-44 md:flex-shrink-0">
					<!-- Order Badge -->
					<div class="flex-shrink-0 w-8 h-8 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center text-brand-700 dark:text-brand-300 font-semibold text-sm border border-brand-200 dark:border-brand-800">
						{expert.order}
					</div>

					<!-- Name + Role + Expertise stacked -->
					<div class="flex flex-col min-w-0">
						<h4 class="font-semibold text-slate-900 dark:text-white text-sm">
							{expert.persona.name}
						</h4>

						{#if expert.persona.archetype}
							<p class="text-xs font-medium text-slate-700 dark:text-slate-300">
								{expert.persona.archetype}
							</p>
						{/if}

						{#if expert.persona.domain_expertise && expert.persona.domain_expertise.length > 0}
							<p class="text-xs text-slate-600 dark:text-slate-400">
								{expert.persona.domain_expertise.slice(0, 2).join(', ')}
							</p>
						{/if}
					</div>
				</div>

				<!-- Right side: Rationale in elevated card (stacks below on mobile, side-by-side on desktop) -->
				{#if expert.rationale}
					<div class="flex-1 p-2.5 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-200 dark:border-blue-800 shadow-sm ml-11 md:ml-0">
						<p class="text-xs text-blue-800 dark:text-blue-200 leading-relaxed">
							{expert.rationale}
						</p>
					</div>
				{/if}
			</div>
		{/each}
	</div>
</div>
