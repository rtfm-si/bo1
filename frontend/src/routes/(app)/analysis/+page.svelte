<script lang="ts">
	/**
	 * Data Analysis Page
	 *
	 * Unified interface for dataset Q&A and general data guidance.
	 * Accessible from "Board" nav dropdown.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { Dataset } from '$lib/api/types';
	import AnalysisChat from '$lib/components/analysis/AnalysisChat.svelte';
	import Breadcrumb from '$lib/components/ui/Breadcrumb.svelte';
	import ShimmerSkeleton from '$lib/components/ui/loading/ShimmerSkeleton.svelte';
	import { toast } from '$lib/stores/toast';

	let datasets = $state<Dataset[]>([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			const response = await apiClient.getDatasets();
			datasets = response.datasets || [];
		} catch (err) {
			console.error('Failed to load datasets:', err);
			toast.error('Failed to load datasets');
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>Data Analysis | Board of One</title>
	<meta
		name="description"
		content="Analyze your data with AI-powered insights and natural language queries"
	/>
</svelte:head>

<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
	<!-- Breadcrumb -->
	<div class="mb-6">
		<Breadcrumb
			items={[
				{ label: 'Dashboard', href: '/dashboard' },
				{ label: 'Analysis', href: '/analysis' }
			]}
		/>
	</div>

	<!-- Page Header -->
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">
			Data Analysis
		</h1>
		<p class="mt-1 text-neutral-600 dark:text-neutral-400">
			Ask questions about your datasets or get general data analysis guidance.
		</p>
	</div>

	<!-- Chat Interface -->
	{#if loading}
		<div class="h-[600px] bg-white dark:bg-neutral-900 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-4">
			<ShimmerSkeleton type="chart" />
		</div>
	{:else}
		<AnalysisChat {datasets} />
	{/if}

	<!-- Tips -->
	<div class="mt-6 p-4 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
		<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
			Analysis tips
		</h3>
		<ul class="text-sm text-neutral-600 dark:text-neutral-400 space-y-1">
			<li>Select a dataset above to ask specific questions about your data</li>
			<li>Without a dataset, get general guidance on data analysis best practices</li>
			<li>Ask about trends, comparisons, correlations, or specific metrics</li>
			<li>The analyst considers your business context automatically</li>
		</ul>
	</div>
</div>
