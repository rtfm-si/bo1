<script lang="ts">
	/**
	 * Research Insights Widget - Scatter plot visualization of user's research topics
	 *
	 * Features:
	 * - 2D scatter plot of research embeddings (PCA-reduced)
	 * - Color-coded by category
	 * - Hover tooltips showing question preview
	 * - Category legend
	 * - Empty state for users without research
	 */
	import { apiClient } from '$lib/api/client';
	import type { ResearchEmbeddingsResponse, ResearchPoint, ResearchCategory } from '$lib/api/types';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { onMount } from 'svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';

	// Fetch research embeddings from context API
	const researchData = useDataFetch(() => apiClient.getResearchEmbeddings());

	// Expose fetch method for parent component to trigger refresh
	export function refresh() {
		researchData.fetch();
	}

	// Derived state
	const points = $derived<ResearchPoint[]>(researchData.data?.points ?? []);
	const categories = $derived<ResearchCategory[]>(researchData.data?.categories ?? []);
	const totalCount = $derived(researchData.data?.total_count ?? 0);
	const isLoading = $derived(researchData.isLoading);
	const hasData = $derived(points.length > 0);

	// SVG dimensions
	const width = 400;
	const height = 250;
	const padding = 30;

	// Hover state
	let hoveredPoint = $state<ResearchPoint | null>(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	// Category color mapping (consistent colors)
	const categoryColors: Record<string, string> = {
		saas_metrics: '#6366F1', // indigo
		pricing: '#8B5CF6', // violet
		marketing: '#EC4899', // pink
		competitors: '#F59E0B', // amber
		operations: '#10B981', // emerald
		finance: '#3B82F6', // blue
		product: '#F97316', // orange
		uncategorized: '#6B7280' // gray
	};

	function getCategoryColor(category: string | null): string {
		if (!category) return categoryColors.uncategorized;
		return categoryColors[category.toLowerCase()] ?? categoryColors.uncategorized;
	}

	// Scale coordinates to SVG space
	function scaleX(x: number): number {
		const allX = points.map((p) => p.x);
		const minX = Math.min(...allX);
		const maxX = Math.max(...allX);
		const range = maxX - minX || 1;
		return padding + ((x - minX) / range) * (width - 2 * padding);
	}

	function scaleY(y: number): number {
		const allY = points.map((p) => p.y);
		const minY = Math.min(...allY);
		const maxY = Math.max(...allY);
		const range = maxY - minY || 1;
		// Invert Y axis (SVG y increases downward)
		return height - padding - ((y - minY) / range) * (height - 2 * padding);
	}

	function handleMouseEnter(event: MouseEvent, point: ResearchPoint) {
		hoveredPoint = point;
		const rect = (event.currentTarget as SVGElement).getBoundingClientRect();
		const parentRect = (event.currentTarget as SVGElement).ownerSVGElement?.getBoundingClientRect();
		if (parentRect) {
			tooltipX = rect.left - parentRect.left + rect.width / 2;
			tooltipY = rect.top - parentRect.top - 10;
		}
	}

	function handleMouseLeave() {
		hoveredPoint = null;
	}

	onMount(() => {
		researchData.fetch();
	});
</script>

<BoCard class="overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
		<div class="flex items-center gap-2">
			<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
				/>
			</svg>
			<h2 class="text-base font-semibold text-neutral-900 dark:text-white">Research Topics</h2>
			{#if totalCount > 0}
				<span class="inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-400">
					{totalCount} topics
				</span>
			{/if}
		</div>
	</div>

	{#if isLoading}
		<!-- Loading skeleton -->
		<div class="p-4 flex items-center justify-center" style="height: {height + 40}px">
			<div class="animate-pulse space-y-4 w-full">
				<div class="h-[{height}px] bg-neutral-200 dark:bg-neutral-700 rounded"></div>
				<div class="flex gap-4 justify-center">
					{#each [1, 2, 3] as idx (idx)}
						<div class="flex items-center gap-1.5">
							<div class="w-3 h-3 bg-neutral-200 dark:bg-neutral-700 rounded-full"></div>
							<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-12"></div>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{:else if !hasData}
		<!-- Empty state -->
		<div class="p-6 text-center" style="min-height: {height + 40}px">
			<div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-neutral-100 dark:bg-neutral-700 mb-3">
				<svg class="w-6 h-6 text-neutral-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
					/>
				</svg>
			</div>
			<h3 class="text-sm font-medium text-neutral-900 dark:text-white mb-1">No research yet</h3>
			<p class="text-xs text-neutral-500 dark:text-neutral-400 max-w-xs mx-auto">
				Your research topics will appear here after you run meetings. Each point represents a topic explored by your board.
			</p>
		</div>
	{:else}
		<!-- Scatter plot -->
		<div class="p-4">
			<div class="relative">
				<svg {width} {height} class="w-full h-auto" viewBox="0 0 {width} {height}">
					<!-- Background grid (subtle) -->
					<g class="opacity-20">
						{#each [0.25, 0.5, 0.75] as ratio (ratio)}
							<line
								x1={padding}
								y1={padding + ratio * (height - 2 * padding)}
								x2={width - padding}
								y2={padding + ratio * (height - 2 * padding)}
								stroke="currentColor"
								stroke-dasharray="4,4"
								class="text-neutral-400 dark:text-neutral-600"
							/>
							<line
								x1={padding + ratio * (width - 2 * padding)}
								y1={padding}
								x2={padding + ratio * (width - 2 * padding)}
								y2={height - padding}
								stroke="currentColor"
								stroke-dasharray="4,4"
								class="text-neutral-400 dark:text-neutral-600"
							/>
						{/each}
					</g>

					<!-- Data points -->
					{#each points as point (point.preview + point.created_at)}
						<circle
							cx={scaleX(point.x)}
							cy={scaleY(point.y)}
							r={hoveredPoint === point ? 8 : 6}
							fill={getCategoryColor(point.category)}
							class="cursor-pointer transition-all duration-150 opacity-80 hover:opacity-100"
							role="img"
							aria-label={point.preview}
							onmouseenter={(e) => handleMouseEnter(e, point)}
							onmouseleave={handleMouseLeave}
						/>
					{/each}
				</svg>

				<!-- Tooltip -->
				{#if hoveredPoint}
					<div
						class="absolute pointer-events-none z-10 px-3 py-2 text-xs rounded-lg shadow-lg bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900 max-w-[200px]"
						style="left: {tooltipX}px; top: {tooltipY}px; transform: translate(-50%, -100%);"
					>
						<p class="font-medium truncate">{hoveredPoint.preview}</p>
						{#if hoveredPoint.category}
							<p class="text-neutral-400 dark:text-neutral-600 mt-0.5 capitalize">{hoveredPoint.category}</p>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Category legend -->
			{#if categories.length > 0}
				<div class="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700">
					<div class="flex flex-wrap gap-3 justify-center">
						{#each categories.slice(0, 6) as cat (cat.name)}
							<div class="flex items-center gap-1.5">
								<span class="w-3 h-3 rounded-full" style="background-color: {getCategoryColor(cat.name)}"></span>
								<span class="text-xs text-neutral-600 dark:text-neutral-400 capitalize">{cat.name}</span>
								<span class="text-xs text-neutral-400 dark:text-neutral-500">({cat.count})</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</BoCard>
