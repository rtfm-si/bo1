<script lang="ts">
	import { onMount } from 'svelte';
	import { Database, RefreshCw, Filter, Info } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import {
		adminApi,
		type EmbeddingStatsResponse,
		type EmbeddingSampleResponse,
		type EmbeddingPoint
	} from '$lib/api/admin';

	// State
	let stats = $state<EmbeddingStatsResponse | null>(null);
	let sampleData = $state<EmbeddingSampleResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let selectedType = $state<'all' | 'contributions' | 'research' | 'context'>('all');
	let selectedMethod = $state<'pca' | 'umap'>('pca');
	let sampleLimit = $state(500);
	let hoveredPoint = $state<EmbeddingPoint | null>(null);
	let tooltipPosition = $state({ x: 0, y: 0 });

	// Color mapping for embedding types
	const typeColors: Record<string, string> = {
		contribution: '#3b82f6', // blue
		research: '#10b981', // green
		context: '#f59e0b' // amber
	};

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
	function getScatterData(points: EmbeddingPoint[]) {
		if (!points.length) return { viewBox: '0 0 100 100', scaled: [] };

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

		return { viewBox: '0 0 100 100', scaled };
	}

	onMount(() => {
		loadStats();
		loadSample();
	});

	// Reload when filters change
	$effect(() => {
		if (selectedType || selectedMethod || sampleLimit) {
			loadSample();
		}
	});

	const scatterData = $derived(sampleData ? getScatterData(sampleData.points) : null);
</script>

<svelte:head>
	<title>Embeddings Visualization - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/admin"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
						aria-label="Back to admin"
					>
						<svg
							class="w-5 h-5 text-neutral-600 dark:text-neutral-400"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 19l-7-7m0 0l7-7m-7 7h18"
							/>
						</svg>
					</a>
					<div class="flex items-center gap-3">
						<Database class="w-6 h-6 text-brand-600 dark:text-brand-400" />
						<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
							Embeddings Visualization
						</h1>
					</div>
				</div>
				<Button variant="secondary" size="sm" onclick={loadSample} disabled={loading}>
					<RefreshCw class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
					Refresh
				</Button>
			</div>
		</div>
	</header>

	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
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
					<div class="text-2xl font-semibold text-blue-600">
						{stats.by_type.contributions.toLocaleString()}
					</div>
				</div>
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="text-sm text-neutral-500 dark:text-neutral-400">Research Cache</div>
					<div class="text-2xl font-semibold text-green-600">
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
				</h2>
				<div class="flex items-center gap-4 text-sm">
					<div class="flex items-center gap-2">
						<span class="w-3 h-3 rounded-full" style="background-color: {typeColors.contribution}"
						></span>
						<span class="text-neutral-600 dark:text-neutral-400">Contributions</span>
					</div>
					<div class="flex items-center gap-2">
						<span class="w-3 h-3 rounded-full" style="background-color: {typeColors.research}"
						></span>
						<span class="text-neutral-600 dark:text-neutral-400">Research</span>
					</div>
					<div class="flex items-center gap-2">
						<span class="w-3 h-3 rounded-full" style="background-color: {typeColors.context}"></span
						>
						<span class="text-neutral-600 dark:text-neutral-400">Context</span>
					</div>
				</div>
			</div>

			{#if loading}
				<div class="h-[500px] flex items-center justify-center">
					<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
				</div>
			{:else if scatterData && scatterData.scaled.length > 0}
				<div class="relative">
					<svg viewBox={scatterData.viewBox} class="w-full h-[500px]" preserveAspectRatio="xMidYMid">
						{#each scatterData.scaled as point}
							<circle
								cx={point.cx}
								cy={point.cy}
								r="0.8"
								fill={typeColors[point.type] || '#6b7280'}
								opacity="0.7"
								class="cursor-pointer hover:opacity-100 transition-opacity"
								onmouseenter={(e) => handlePointHover(e, point)}
								onmouseleave={() => handlePointHover(new MouseEvent('mouseleave'), null)}
							/>
						{/each}
					</svg>
				</div>
			{:else}
				<div
					class="h-[500px] flex items-center justify-center text-neutral-500 dark:text-neutral-400"
				>
					<div class="text-center">
						<Info class="w-12 h-12 mx-auto mb-2 opacity-50" />
						<p>No embeddings found</p>
					</div>
				</div>
			{/if}
		</div>

		<!-- Tooltip -->
		{#if hoveredPoint}
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
