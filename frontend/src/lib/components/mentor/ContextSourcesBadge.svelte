<script lang="ts">
	/**
	 * ContextSourcesBadge - Shows which context sources are being used
	 */
	import { Briefcase, Calendar, CheckSquare, Database } from 'lucide-svelte';

	let {
		sources = []
	}: {
		sources: string[];
	} = $props();

	const sourceConfig = {
		business_context: {
			label: 'Business',
			icon: Briefcase,
			color: 'text-info-600 dark:text-info-400'
		},
		recent_meetings: {
			label: 'Meetings',
			icon: Calendar,
			color: 'text-purple-600 dark:text-purple-400'
		},
		active_actions: {
			label: 'Actions',
			icon: CheckSquare,
			color: 'text-success-600 dark:text-success-400'
		},
		datasets: {
			label: 'Data',
			icon: Database,
			color: 'text-warning-600 dark:text-warning-400'
		}
	} as const;

	function getSourceInfo(source: string) {
		return sourceConfig[source as keyof typeof sourceConfig] || null;
	}
</script>

{#if sources.length > 0}
	<div class="flex flex-wrap items-center gap-2 text-xs">
		<span class="text-neutral-500 dark:text-neutral-400">Using:</span>
		{#each sources as source}
			{@const info = getSourceInfo(source)}
			{#if info}
				<span
					class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 {info.color}"
				>
					<info.icon class="w-3 h-3" />
					<span>{info.label}</span>
				</span>
			{/if}
		{/each}
	</div>
{/if}
