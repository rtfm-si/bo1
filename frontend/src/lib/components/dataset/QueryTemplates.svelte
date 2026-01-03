<script lang="ts">
	/**
	 * QueryTemplates - Expandable query template chips for common analysis patterns
	 * Auto-fills templates with actual column names from semantics
	 */
	import type { ColumnSemantic } from '$lib/api/types';

	interface Props {
		columnSemantics: ColumnSemantic[];
		onSelectTemplate: (query: string) => void;
	}

	let { columnSemantics, onSelectTemplate }: Props = $props();

	// Expand/collapse state
	let isExpanded = $state(false);

	// Categorize columns
	const numericColumns = $derived(
		columnSemantics.filter(c =>
			['metric', 'numeric', 'currency', 'percentage'].includes(c.semantic_type.toLowerCase())
		)
	);

	const dimensionColumns = $derived(
		columnSemantics.filter(c =>
			['dimension', 'category', 'categorical'].includes(c.semantic_type.toLowerCase())
		)
	);

	const dateColumns = $derived(
		columnSemantics.filter(c =>
			['date', 'datetime', 'timestamp'].includes(c.semantic_type.toLowerCase())
		)
	);

	// Template categories with auto-filled queries
	interface Template {
		label: string;
		query: string;
		icon: string;
		available: boolean;
	}

	const templates = $derived.by<Template[]>(() => {
		const numCol = numericColumns[0]?.column_name;
		const dimCol = dimensionColumns[0]?.column_name;
		const dateCol = dateColumns[0]?.column_name;
		const numCol2 = numericColumns[1]?.column_name;

		return [
			{
				label: 'Ranking',
				query: numCol && dimCol
					? `Top 10 ${dimCol} by ${numCol}`
					: numCol
						? `Top values by ${numCol}`
						: 'Top items by value',
				icon: '🏆',
				available: !!numCol
			},
			{
				label: 'Trends',
				query: numCol && dateCol
					? `${numCol} trend over ${dateCol}`
					: dateCol
						? `Trend over ${dateCol}`
						: 'Show trend over time',
				icon: '📈',
				available: !!dateCol
			},
			{
				label: 'Comparison',
				query: numCol && dimCol
					? `Compare ${numCol} across ${dimCol}`
					: dimCol
						? `Compare values across ${dimCol}`
						: 'Compare categories',
				icon: '⚖️',
				available: !!dimCol
			},
			{
				label: 'Distribution',
				query: numCol
					? `Distribution of ${numCol}`
					: dimCol
						? `Distribution of ${dimCol}`
						: 'Show distribution',
				icon: '📊',
				available: !!(numCol || dimCol)
			},
			{
				label: 'Correlation',
				query: numCol && numCol2
					? `Correlation between ${numCol} and ${numCol2}`
					: 'Correlation between numeric fields',
				icon: '🔗',
				available: !!(numCol && numCol2)
			},
			{
				label: 'Segments',
				query: dimCol && numCol
					? `${dimCol} segments by ${numCol}`
					: dimCol
						? `Segment by ${dimCol}`
						: 'Group by category',
				icon: '📁',
				available: !!dimCol
			}
		];
	});

	// Filter to available templates
	const availableTemplates = $derived(
		templates.filter((t: Template) => t.available)
	);

	const hasTemplates = $derived(availableTemplates.length > 0);
</script>

{#if hasTemplates}
	<div class="bg-neutral-50 dark:bg-neutral-700/30 rounded-lg border border-neutral-200 dark:border-neutral-600">
		<!-- Header / Toggle -->
		<button
			onclick={() => isExpanded = !isExpanded}
			class="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 rounded-lg transition-colors"
		>
			<span class="flex items-center gap-2">
				<svg class="w-4 h-4 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
				</svg>
				Quick Queries
			</span>
			<svg
				class="w-4 h-4 text-neutral-400 transition-transform {isExpanded ? 'rotate-180' : ''}"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</button>

		{#if isExpanded}
			<div class="px-3 pb-3">
				<div class="flex flex-wrap gap-2">
					{#each availableTemplates as template (template.label)}
						<button
							onclick={() => onSelectTemplate(template.query)}
							class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-full bg-white dark:bg-neutral-700 border border-neutral-200 dark:border-neutral-600 text-neutral-700 dark:text-neutral-200 hover:bg-brand-50 dark:hover:bg-brand-900/20 hover:border-brand-300 dark:hover:border-brand-700 hover:text-brand-700 dark:hover:text-brand-300 transition-colors"
							title={template.query}
						>
							<span>{template.icon}</span>
							<span>{template.label}</span>
						</button>
					{/each}
				</div>

				<!-- Show query preview on hover - using last hovered -->
				<p class="mt-2 text-[10px] text-neutral-400 dark:text-neutral-500 italic">
					Click a template to fill the question input
				</p>
			</div>
		{/if}
	</div>
{/if}
