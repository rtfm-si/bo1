<script lang="ts">
	import { CheckCircle } from 'lucide-svelte';
	import type { SubProblemTab } from '../../../routes/(app)/meeting/[id]/lib/subProblemTabs';

	interface Props {
		subProblemTabs: SubProblemTab[];
		showConclusionTab: boolean;
		activeSubProblemTab: string | undefined;
		onTabChange: (tabId: string) => void;
	}

	let { subProblemTabs, showConclusionTab, activeSubProblemTab, onTabChange }: Props = $props();
</script>

{#if subProblemTabs.length > 1}
	<div class="border-b border-slate-200 dark:border-slate-700">
		<div class="flex overflow-x-auto px-4 pt-3" role="tablist" aria-label="Focus area tabs">
			{#each subProblemTabs as tab}
				{@const isActive = activeSubProblemTab === tab.id}
				<button
					type="button"
					role="tab"
					aria-selected={isActive}
					aria-controls="tabpanel-{tab.id}"
					id="tab-{tab.id}"
					class={[
						'flex-shrink-0 px-4 py-2 border-b-2 -mb-px transition-all text-sm font-medium',
						isActive
							? 'border-brand-600 text-brand-700 dark:border-brand-400 dark:text-brand-400'
							: 'border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:border-slate-300 dark:hover:border-slate-600',
					].join(' ')}
					onclick={() => onTabChange(tab.id)}
				>
					<div class="flex items-center gap-2">
						<span>{tab.label}</span>
						{#if tab.status === 'complete'}
							<CheckCircle size={14} class="text-current" />
						{/if}
					</div>
				</button>
			{/each}
			<!-- Conclusion tab (appears when meta-synthesis is complete) -->
			{#if showConclusionTab}
				{@const isActive = activeSubProblemTab === 'conclusion'}
				<button
					type="button"
					role="tab"
					aria-selected={isActive}
					aria-controls="tabpanel-conclusion"
					id="tab-conclusion"
					class={[
						'flex-shrink-0 px-4 py-2 border-b-2 -mb-px transition-all text-sm font-medium',
						isActive
							? 'border-success-600 text-success-700 dark:border-success-400 dark:text-success-400'
							: 'border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:border-slate-300 dark:hover:border-slate-600',
					].join(' ')}
					onclick={() => onTabChange('conclusion')}
				>
					<div class="flex items-center gap-2">
						<span>Summary</span>
						<CheckCircle size={14} class="text-success-600 dark:text-success-400" />
					</div>
				</button>
			{/if}
		</div>
	</div>
{/if}
