<script lang="ts">
	/**
	 * ChartsTab - Chart builder and favourites
	 */
	import type { DatasetDetailResponse, DatasetReport } from '$lib/api/types';
	import FavouritesTab from '../FavouritesTab.svelte';

	// Use the profiles type from DatasetDetailResponse to match what's passed from the page
	type ProfileType = NonNullable<DatasetDetailResponse['profiles']>[number];

	interface Props {
		datasetId: string;
		profiles: ProfileType[];
		onReportGenerated?: (report: DatasetReport) => void;
	}

	let { datasetId, profiles, onReportGenerated }: Props = $props();

	// Sub-tab state
	let activeSubTab = $state<'build' | 'favourites'>('build');

	const subTabs = [
		{ id: 'build' as const, label: 'Build Chart' },
		{ id: 'favourites' as const, label: 'Favourites' }
	];

	// Get column options from profiles
	const numericColumns = $derived(
		profiles.filter(p =>
			['integer', 'float', 'numeric', 'currency', 'percentage'].includes(p.data_type.toLowerCase())
		).map(p => p.column_name)
	);

	const allColumns = $derived(profiles.map(p => p.column_name));
</script>

<div class="space-y-6">
	<!-- Sub-tabs -->
	<div class="border-b border-neutral-200 dark:border-neutral-700">
		<nav class="flex gap-4" aria-label="Chart tabs">
			{#each subTabs as tab}
				<button
					onclick={() => activeSubTab = tab.id}
					class="py-2 px-1 text-sm font-medium border-b-2 transition-colors {activeSubTab === tab.id
						? 'border-brand-500 text-brand-600 dark:text-brand-400'
						: 'border-transparent text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300'}"
				>
					{tab.label}
				</button>
			{/each}
		</nav>
	</div>

	{#if activeSubTab === 'build'}
		<!-- Chart Builder Placeholder - will be replaced with ChartBuilder component -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
			<div class="flex items-center gap-3 mb-6">
				<span class="p-2 rounded-lg bg-brand-100 dark:bg-brand-900/30">
					<svg class="w-5 h-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
					</svg>
				</span>
				<div>
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Build a Chart</h2>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">Create custom visualizations from your data</p>
				</div>
			</div>

			{#if profiles.length === 0}
				<div class="text-center py-8">
					<svg class="w-12 h-12 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
					</svg>
					<p class="text-neutral-600 dark:text-neutral-400">
						Generate a profile first to enable chart building.
					</p>
				</div>
			{:else}
				<!-- Chart type selector -->
				<div class="grid grid-cols-4 gap-3 mb-6">
					{#each ['bar', 'line', 'scatter', 'pie'] as chartType}
						<button
							class="p-4 rounded-lg border-2 border-neutral-200 dark:border-neutral-600 hover:border-brand-300 dark:hover:border-brand-600 transition-colors flex flex-col items-center gap-2"
						>
							{#if chartType === 'bar'}
								<svg class="w-8 h-8 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
								</svg>
							{:else if chartType === 'line'}
								<svg class="w-8 h-8 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
								</svg>
							{:else if chartType === 'scatter'}
								<svg class="w-8 h-8 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="2" />
									<circle cx="16" cy="12" r="2" stroke="currentColor" stroke-width="2" />
									<circle cx="10" cy="16" r="2" stroke="currentColor" stroke-width="2" />
									<circle cx="18" cy="6" r="2" stroke="currentColor" stroke-width="2" />
								</svg>
							{:else}
								<svg class="w-8 h-8 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
								</svg>
							{/if}
							<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300 capitalize">{chartType}</span>
						</button>
					{/each}
				</div>

				<!-- Axis selectors placeholder -->
				<div class="grid grid-cols-2 gap-4 mb-6">
					<div>
						<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">X Axis</label>
						<select class="w-full px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white">
							<option value="">Select column...</option>
							{#each allColumns as col}
								<option value={col}>{col}</option>
							{/each}
						</select>
					</div>
					<div>
						<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">Y Axis</label>
						<select class="w-full px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white">
							<option value="">Select column...</option>
							{#each numericColumns as col}
								<option value={col}>{col}</option>
							{/each}
						</select>
					</div>
				</div>

				<!-- Preview placeholder -->
				<div class="border-2 border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg p-12 text-center">
					<svg class="w-16 h-16 mx-auto text-neutral-300 dark:text-neutral-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
					</svg>
					<p class="text-neutral-500 dark:text-neutral-400">Chart preview will appear here</p>
					<p class="text-sm text-neutral-400 dark:text-neutral-500 mt-1">Select axes and click Preview to generate</p>
				</div>

				<!-- Action buttons -->
				<div class="flex justify-end gap-3 mt-6">
					<button class="px-4 py-2 text-sm font-medium rounded-lg border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors">
						Preview
					</button>
					<button class="px-4 py-2 text-sm font-medium rounded-lg bg-brand-600 hover:bg-brand-700 text-white transition-colors flex items-center gap-2">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
						</svg>
						Save as Favourite
					</button>
				</div>
			{/if}
		</div>
	{:else}
		<!-- Favourites Tab -->
		<FavouritesTab
			{datasetId}
			{onReportGenerated}
		/>
	{/if}
</div>
