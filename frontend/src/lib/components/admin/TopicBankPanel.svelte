<script lang="ts">
	/**
	 * TopicBankPanel - Displays researched decision topics with scoring
	 */
	import { SvelteSet } from 'svelte/reactivity';
	import { Button } from '$lib/components/ui';
	import { Trash2, ChevronDown, ChevronUp, ArrowRight } from 'lucide-svelte';
	import { type BankedTopic } from '$lib/api/admin';

	import { formatDate } from '$lib/utils/time-formatting';
	interface Props {
		topics: BankedTopic[];
		ondismiss: (id: string) => void;
		onuse: (id: string) => void;
	}

	let { topics, ondismiss, onuse }: Props = $props();

	let expandedReasoning = new SvelteSet<string>();
	let expandedAlignment = new SvelteSet<string>();

	function toggleReasoning(id: string) {
		if (expandedReasoning.has(id)) expandedReasoning.delete(id);
		else expandedReasoning.add(id);
	}

	function toggleAlignment(id: string) {
		if (expandedAlignment.has(id)) expandedAlignment.delete(id);
		else expandedAlignment.add(id);
	}

	function getSeoColor(score: number) {
		if (score > 0.7) return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400';
		if (score > 0.4) return 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400';
		return 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400';
	}

	function getCategoryColor(category: string) {
		const colors: Record<string, string> = {
			hiring: 'bg-info-100 text-info-700 dark:bg-info-900/30 dark:text-info-400',
			pricing: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
			fundraising: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400',
			marketing: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
			strategy: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
			product: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
			operations: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
			growth: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400'
		};
		return colors[category] || 'bg-neutral-100 text-neutral-600';
	}

</script>

{#if topics.length === 0}
	<div class="text-center py-8 text-neutral-500 dark:text-neutral-400">
		<p class="text-sm">No banked topics yet. Run research to discover topics.</p>
	</div>
{:else}
	<div class="space-y-3">
		{#each topics as topic (topic.id)}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
				<!-- Header -->
				<div class="flex items-start justify-between gap-3">
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 flex-wrap mb-1">
							<span class="px-2 py-0.5 rounded text-xs font-medium {getCategoryColor(topic.category)}">
								{topic.category}
							</span>
							<span class="px-2 py-0.5 rounded text-xs font-medium {getSeoColor(topic.seo_score)}">
								SEO {(topic.seo_score * 100).toFixed(0)}%
							</span>
							<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-neutral-100 text-neutral-500 dark:bg-neutral-700 dark:text-neutral-400">
								{topic.source}
							</span>
							{#if topic.researched_at}
								<span class="text-[10px] text-neutral-400">{formatDate(topic.researched_at)}</span>
							{/if}
						</div>
						<h4 class="text-base font-medium text-neutral-900 dark:text-white">{topic.title}</h4>
						<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1">{topic.description}</p>
					</div>
					<div class="flex items-center gap-1.5 shrink-0">
						<Button size="sm" onclick={() => onuse(topic.id)}>
							<ArrowRight class="w-3.5 h-3.5 mr-1" />
							Use as Draft
						</Button>
						<Button variant="ghost" size="sm" onclick={() => ondismiss(topic.id)} title="Dismiss">
							<Trash2 class="w-3.5 h-3.5 text-error-500" />
						</Button>
					</div>
				</div>

				<!-- Keywords -->
				{#if topic.keywords.length > 0}
					<div class="flex flex-wrap gap-1 mt-2">
						{#each topic.keywords as kw (kw)}
							<span class="px-1.5 py-0.5 text-[10px] rounded bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400">
								{kw}
							</span>
						{/each}
					</div>
				{/if}

				<!-- Expandable sections -->
				<div class="flex gap-3 mt-2">
					<button
						class="text-xs text-brand-600 dark:text-brand-400 hover:underline flex items-center gap-0.5"
						onclick={() => toggleReasoning(topic.id)}
					>
						Why this topic
						{#if expandedReasoning.has(topic.id)}
							<ChevronUp class="w-3 h-3" />
						{:else}
							<ChevronDown class="w-3 h-3" />
						{/if}
					</button>
					<button
						class="text-xs text-brand-600 dark:text-brand-400 hover:underline flex items-center gap-0.5"
						onclick={() => toggleAlignment(topic.id)}
					>
						Bo1 Alignment
						{#if expandedAlignment.has(topic.id)}
							<ChevronUp class="w-3 h-3" />
						{:else}
							<ChevronDown class="w-3 h-3" />
						{/if}
					</button>
				</div>

				{#if expandedReasoning.has(topic.id)}
					<div class="mt-2 p-3 rounded bg-neutral-50 dark:bg-neutral-900 text-sm text-neutral-600 dark:text-neutral-400">
						{topic.reasoning}
					</div>
				{/if}

				{#if expandedAlignment.has(topic.id)}
					<div class="mt-2 p-3 rounded bg-brand-50 dark:bg-brand-900/10 text-sm text-neutral-600 dark:text-neutral-400">
						{topic.bo1_alignment}
					</div>
				{/if}
			</div>
		{/each}
	</div>
{/if}
