<script lang="ts">
	import { CheckCircle, ClipboardList } from 'lucide-svelte';
	import type { SubProblemTab } from '../../../routes/(app)/meeting/[id]/lib/subProblemTabs';

	interface Props {
		subProblemTabs: SubProblemTab[];
		showConclusionTab: boolean;
		showActionsTab?: boolean;
		hasActions?: boolean;
		activeSubProblemTab: string | undefined;
		onTabChange: (tabId: string) => void;
	}

	let { subProblemTabs, showConclusionTab, showActionsTab = false, hasActions = false, activeSubProblemTab, onTabChange }: Props = $props();
</script>

{#if subProblemTabs.length > 1}
	<div class="border-b border-neutral-200 dark:border-neutral-700">
		<div class="flex overflow-x-auto px-4 pt-3" role="tablist" aria-label="Focus area tabs">
			{#each subProblemTabs as tab}
				{@const isActive = activeSubProblemTab === tab.id}
				{@const statusColors = {
					pending: 'bg-neutral-400',
					blocked: 'bg-neutral-400',
					active: 'bg-info-500 animate-pulse',
					voting: 'bg-purple-500 animate-pulse',
					synthesis: 'bg-orange-500 animate-pulse',
					complete: 'bg-success-500'
				}}
				{@const statusLabels = {
					pending: 'Waiting',
					blocked: 'Blocked',
					active: 'Discussing',
					voting: 'Voting',
					synthesis: 'Synthesizing',
					complete: 'Complete'
				}}
				<button
					type="button"
					role="tab"
					aria-selected={isActive}
					aria-controls="tabpanel-{tab.id}"
					aria-label={tab.goal}
					title={tab.goal}
					id="tab-{tab.id}"
					class={[
						'flex-shrink-0 px-4 py-2 border-b-2 -mb-px transition-all text-sm font-medium',
						isActive
							? 'border-brand-600 text-brand-700 dark:border-brand-400 dark:text-brand-400'
							: 'border-transparent text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100 hover:border-neutral-300 dark:hover:border-neutral-600',
					].join(' ')}
					onclick={() => onTabChange(tab.id)}
				>
					<div class="flex items-center gap-2">
						<span>{tab.label}</span>
						{#if tab.status === 'complete'}
							<CheckCircle size={14} class="text-success-600 dark:text-success-400" />
						{:else if tab.status !== 'pending'}
							<span
								class="w-2 h-2 rounded-full {statusColors[tab.status]}"
								title={statusLabels[tab.status]}
							></span>
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
							: 'border-transparent text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100 hover:border-neutral-300 dark:hover:border-neutral-600',
					].join(' ')}
					onclick={() => onTabChange('conclusion')}
				>
					<div class="flex items-center gap-2">
						<span>Summary</span>
						<CheckCircle size={14} class="text-success-600 dark:text-success-400" />
					</div>
				</button>
			{/if}
			<!-- Actions tab (appears when meeting has actions) -->
			{#if showActionsTab}
				{@const isActive = activeSubProblemTab === 'actions'}
				<button
					type="button"
					role="tab"
					aria-selected={isActive}
					aria-controls="tabpanel-actions"
					id="tab-actions"
					class={[
						'flex-shrink-0 px-4 py-2 border-b-2 -mb-px transition-all text-sm font-medium',
						isActive
							? 'border-brand-600 text-brand-700 dark:border-brand-400 dark:text-brand-400'
							: 'border-transparent text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100 hover:border-neutral-300 dark:hover:border-neutral-600',
					].join(' ')}
					onclick={() => onTabChange('actions')}
				>
					<div class="flex items-center gap-2">
						<ClipboardList size={14} class="text-current" />
						<span>Actions</span>
						{#if hasActions}
							<CheckCircle size={14} class="text-brand-600 dark:text-brand-400" />
						{/if}
					</div>
				</button>
			{/if}
		</div>
	</div>
{/if}
