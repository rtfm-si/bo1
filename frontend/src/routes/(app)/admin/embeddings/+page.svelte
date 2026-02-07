<script lang="ts">
	import { onMount } from 'svelte';
	import { Database, RefreshCw, Filter, Info } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';
	import {
		adminApi,
		type EmbeddingStatsResponse,
		type EmbeddingSampleResponse,
		type EmbeddingPoint,
		type ClusterInfo
	} from '$lib/api/admin';

	// State
	let stats = $state<EmbeddingStatsResponse | null>(null);
	let sampleData = $state<EmbeddingSampleResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let selectedType = $state<'all' | 'contributions' | 'research' | 'context'>('all');
	let selectedMethod = $state<'pca' | 'umap'>('pca');
	let sampleLimit = $state(200);
	let hoveredPoint = $state<EmbeddingPoint | null>(null);
	let tooltipPosition = $state({ x: 0, y: 0 });

	// Color mapping for embedding types (fallback when no clusters)
	const typeColors: Record<string, string> = {
		contribution: '#3b82f6', // blue
		research: '#10b981', // green
		context: '#f59e0b' // amber
	};

	// Color palette for clusters (10 distinct colors)
	const clusterColors = [
		'#3b82f6', // blue
		'#10b981', // emerald
		'#f59e0b', // amber
		'#ef4444', // red
		'#8b5cf6', // violet
		'#ec4899', // pink
		'#06b6d4', // cyan
		'#84cc16', // lime
		'#f97316', // orange
		'#6366f1' // indigo
	];

	function getClusterColor(clusterId: number): string {
		return clusterColors[clusterId % clusterColors.length];
	}

	async function loadStats() {
		try {
			stats = await adminApi.getEmbeddingStats();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load stats';
		}
	}

	async function loadSample() {
		try {
			loading = true;
			error = null;
			sampleData = await adminApi.getEmbeddingSample({
				embedding_type: selectedType,
				limit: sampleLimit,
				method: selectedMethod
			});
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load embeddings';
		} finally {
			loading = false;
		}
	}

	function handlePointHover(event: MouseEvent, point: EmbeddingPoint | null) {
		if (point) {
			tooltipPosition = { x: event.clientX, y: event.clientY };
			hoveredPoint = point;
		} else {
			hoveredPoint = null;
		}
	}

	// Compute SVG viewBox and point positions
	function getScatterData(points: EmbeddingPoint[], clusters: ClusterInfo[]) {
		if (!points.length) return { viewBox: '0 0 100 100', scaled: [], scaledClusters: [] };

		const xs = points.map((p) => p.x);
		const ys = points.map((p) => p.y);
		const minX = Math.min(...xs);
		const maxX = Math.max(...xs);
		const minY = Math.min(...ys);
		const maxY = Math.max(...ys);

		const padding = 10;
		const width = maxX - minX || 1;
		const height = maxY - minY || 1;

		const scaled = points.map((p) => ({
			...p,
			cx: padding + ((p.x - minX) / width) * (100 - 2 * padding),
			cy: padding + ((p.y - minY) / height) * (100 - 2 * padding)
		}));

		// Scale cluster centroids to same coordinate space
		const scaledClusters = clusters.map((c) => ({
			...c,
			cx: padding + ((c.centroid.x - minX) / width) * (100 - 2 * padding),
			cy: padding + ((c.centroid.y - minY) / height) * (100 - 2 * padding)
		}));

		return { viewBox: '0 0 100 100', scaled, scaledClusters };
	}

	// Track previous filter values to avoid double-fire on mount
	let prevType = $state(selectedType);
	let prevMethod = $state(selectedMethod);
	let prevLimit = $state(sampleLimit);

	onMount(() => {
		loadStats();
		loadSample();
	});

	// Reload only when filters actually change (not on initial mount)
	$effect(() => {
		const typeChanged = selectedType !== prevType;
		const methodChanged = selectedMethod !== prevMethod;
		const limitChanged = sampleLimit !== prevLimit;
		if (typeChanged || methodChanged || limitChanged) {
			prevType = selectedType;
			prevMethod = selectedMethod;
			prevLimit = sampleLimit;
			loadSample();
		}
	});

	const scatterData = $derived(
		sampleData ? getScatterData(sampleData.points, sampleData.clusters || []) : null
	);
	const hasClusters = $derived(sampleData?.clusters && sampleData.clusters.length > 0);
</script>

<svelte:head>
	<title>Embeddings Visualization - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="Embeddings Visualization" icon={Database}>
		{#snippet actions()}
			<Button variant="secondary" size="sm" onclick={loadSample} disabled={loading}>
				<RefreshCw class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
				Refresh
			</Button>
		{/snippet}
	</AdminPageHeader>

	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-6">
		{#if error}
			<Alert variant="error" class="mb-6">{error}</Alert>
		{/if}

		<!-- Stats Cards -->
		{#if stats}
			<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="text-sm text-neutral-500 dark:text-neutral-400">Total Embeddings</div>
					<div class="text-2xl font-semibold text-neutral-900 dark:text-white">
						{stats.total_embeddings.toLocaleString()}
					</div>
				</div>
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="text-sm text-neutral-500 dark:text-neutral-400">Contributions</div>
					<div class="text-2xl font-semibold text-info-600">
						{stats.by_type.contributions.toLocaleString()}
					</div>
				</div>
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="text-sm text-neutral-500 dark:text-neutral-400">Research Cache</div>
					<div class="text-2xl font-semibold text-success-600">
						{stats.by_type.research_cache.toLocaleString()}
					</div>
				</div>
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="text-sm text-neutral-500 dark:text-neutral-400">Storage</div>
					<div class="text-2xl font-semibold text-neutral-900 dark:text-white">
						{stats.storage_estimate_mb.toFixed(1)} MB
					</div>
				</div>
			</div>
		{/if}

		<!-- Filters -->
		<div
			class="bg-white dark:bg-neutral-800 rounded-lg p-4 mb-6 border border-neutral-200 dark:border-neutral-700"
		>
			<div class="flex flex-wrap items-center gap-4">
				<div class="flex items-center gap-2">
					<Filter class="w-4 h-4 text-neutral-500" />
					<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">Filters:</span>
				</div>

				<select
					bind:value={selectedType}
					class="px-3 py-2 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
				>
					<option value="all">All Types</option>
					<option value="contributions">Contributions</option>
					<option value="research">Research</option>
					<option value="context">Context</option>
				</select>

				<select
					bind:value={selectedMethod}
					class="px-3 py-2 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
				>
					<option value="pca">PCA (fast)</option>
					<option value="umap" disabled={!stats?.umap_available}>
						UMAP {stats?.umap_available ? '' : '(unavailable)'}
					</option>
				</select>

				<select
					bind:value={sampleLimit}
					class="px-3 py-2 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
				>
					<option value={100}>100 points</option>
					<option value={250}>250 points</option>
					<option value={500}>500 points</option>
					<option value={1000}>1000 points</option>
				</select>

				{#if sampleData}
					<span class="text-sm text-neutral-500 dark:text-neutral-400">
						Showing {sampleData.points.length} of {sampleData.total_available.toLocaleString()}
					</span>
				{/if}
			</div>
		</div>

		<!-- Scatter Plot -->
		<div
			class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
		>
			<div class="flex items-center justify-between mb-4">
				<h2 class="text-lg font-medium text-neutral-900 dark:text-white">
					2D Projection ({sampleData?.method.toUpperCase() || 'PCA'})
					{#if hasClusters}
						<span class="text-sm font-normal text-neutral-500 ml-2">
							{sampleData?.clusters.length} clusters
						</span>
					{/if}
				</h2>
				{#if !hasClusters}
					<div class="flex items-center gap-4 text-sm">
						<div class="flex items-center gap-2">
							<span
								class="w-3 h-3 rounded-full"
								style="background-color: {typeColors.contribution}"
							></span>
							<span class="text-neutral-600 dark:text-neutral-400">Contributions</span>
						</div>
						<div class="flex items-center gap-2">
							<span class="w-3 h-3 rounded-full" style="background-color: {typeColors.research}"
							></span>
							<span class="text-neutral-600 dark:text-neutral-400">Research</span>
						</div>
						<div class="flex items-center gap-2">
							<span class="w-3 h-3 rounded-full" style="background-color: {typeColors.context}"
							></span>
							<span class="text-neutral-600 dark:text-neutral-400">Context</span>
						</div>
					</div>
				{/if}
			</div>

			{#if loading}
				<div class="h-[500px] flex items-center justify-center">
					<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
				</div>
			{:else if scatterData && scatterData.scaled.length > 0}
				<div class="relative">
					<svg viewBox={scatterData.viewBox} class="w-full h-[500px]" preserveAspectRatio="xMidYMid">
						<!-- Points colored by cluster -->
						{#each scatterData.scaled as point}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<circle
								cx={point.cx}
								cy={point.cy}
								r="0.8"
								fill={hasClusters ? getClusterColor(point.cluster_id) : typeColors[point.type] || '#6b7280'}
								opacity="0.7"
								class="cursor-pointer hover:opacity-100 transition-opacity"
								role="img"
								aria-label={point.preview || point.type}
								onmouseenter={(e) => handlePointHover(e, point)}
								onmouseleave={() => handlePointHover(new MouseEvent('mouseleave'), null)}
							/>
						{/each}
						<!-- Cluster labels at centroids -->
						{#if hasClusters}
							{#each scatterData.scaledClusters as cluster}
								<text
									x={cluster.cx}
									y={cluster.cy}
									text-anchor="middle"
									dominant-baseline="middle"
									font-size="2.5"
									font-weight="600"
									fill={getClusterColor(cluster.id)}
									class="pointer-events-none select-none"
									style="text-shadow: 0 0 3px white, 0 0 3px white, 0 0 3px white;"
								>
									{cluster.label.length > 20 ? cluster.label.slice(0, 20) + '...' : cluster.label}
								</text>
							{/each}
						{/if}
					</svg>
				</div>
			{:else}
				<div class="h-[500px] flex items-center justify-center">
					<EmptyState title="No embeddings found" icon={Info} />
				</div>
			{/if}
		</div>

		<!-- Cluster Legend -->
		{#if hasClusters && sampleData?.clusters}
			<div
				class="mt-6 bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
			>
				<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-4">Topic Clusters</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					{#each sampleData.clusters as cluster}
						<div
							class="flex items-start gap-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-700/50"
						>
							<span
								class="w-4 h-4 rounded-full flex-shrink-0 mt-0.5"
								style="background-color: {getClusterColor(cluster.id)}"
							></span>
							<div class="min-w-0">
								<div class="font-medium text-sm text-neutral-900 dark:text-white truncate">
									{cluster.label}
								</div>
								<div class="text-xs text-neutral-500 dark:text-neutral-400">
									{cluster.count} items
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Tooltip -->
		{#if hoveredPoint}
			{@const point = hoveredPoint}
			{@const clusterLabel = hasClusters && point
				? sampleData?.clusters.find((c) => c.id === point.cluster_id)?.label
				: null}
			<div
				class="fixed z-50 pointer-events-none bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg p-3 max-w-xs"
				style="left: {tooltipPosition.x + 10}px; top: {tooltipPosition.y + 10}px;"
			>
				<div class="text-xs text-neutral-500 dark:text-neutral-400 mb-1">
					{hoveredPoint.type.charAt(0).toUpperCase() + hoveredPoint.type.slice(1)}
				</div>
				<div class="text-sm text-neutral-900 dark:text-white line-clamp-3">
					{hoveredPoint.preview}...
				</div>
				{#if clusterLabel}
					<div class="flex items-center gap-1.5 mt-2">
						<span
							class="w-2.5 h-2.5 rounded-full"
							style="background-color: {getClusterColor(hoveredPoint.cluster_id)}"
						></span>
						<span class="text-xs font-medium text-neutral-700 dark:text-neutral-300">
							{clusterLabel}
						</span>
					</div>
				{/if}
				{#if hoveredPoint.metadata}
					<div class="text-xs text-neutral-500 dark:text-neutral-400 mt-2">
						{#each Object.entries(hoveredPoint.metadata) as [key, value]}
							<span class="mr-2">{key}: {value}</span>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</main>
</div>
