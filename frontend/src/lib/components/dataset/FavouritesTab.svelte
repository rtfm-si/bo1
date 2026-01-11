<script lang="ts">
	/**
	 * FavouritesTab - Shows favourited charts and insights with manage/report generation
	 */
	import type { DatasetFavourite, DatasetReportResponse } from '$lib/api/types';
	import { apiClient } from '$lib/api/client';
	import FavouriteButton from './FavouriteButton.svelte';
	import ChartRenderer from './ChartRenderer.svelte';
	import ChartModal from './ChartModal.svelte';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { Button } from '$lib/components/ui';

	interface Props {
		datasetId: string;
		onReportGenerated?: (report: DatasetReportResponse) => void;
	}

	let { datasetId, onReportGenerated }: Props = $props();

	// Favourites state
	let favourites = $state<DatasetFavourite[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Report generation state
	let generating = $state(false);
	let generateError = $state<string | null>(null);

	// Edit note state
	let editingNoteId = $state<string | null>(null);
	let editNoteText = $state('');

	// Delete state
	let deletingId = $state<string | null>(null);

	// Modal state
	let modalOpen = $state(false);
	let modalFigureJson = $state<Record<string, unknown> | null>(null);
	let modalTitle = $state('');

	async function fetchFavourites() {
		loading = true;
		error = null;
		try {
			const response = await apiClient.listFavourites(datasetId);
			favourites = response.favourites;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load favourites';
		} finally {
			loading = false;
		}
	}

	async function handleDelete(id: string) {
		deletingId = id;
		try {
			await apiClient.deleteFavourite(datasetId, id);
			favourites = favourites.filter((f) => f.id !== id);
		} catch (err) {
			console.error('Failed to delete favourite:', err);
		} finally {
			deletingId = null;
		}
	}

	function startEditNote(fav: DatasetFavourite) {
		editingNoteId = fav.id;
		editNoteText = fav.user_note || '';
	}

	async function saveNote(id: string) {
		try {
			const updated = await apiClient.updateFavourite(datasetId, id, { user_note: editNoteText });
			favourites = favourites.map((f) => (f.id === id ? updated : f));
			editingNoteId = null;
		} catch (err) {
			console.error('Failed to save note:', err);
		}
	}

	function cancelEditNote() {
		editingNoteId = null;
		editNoteText = '';
	}

	async function generateReport() {
		if (favourites.length === 0) return;

		generating = true;
		generateError = null;
		try {
			const report = await apiClient.generateReport(datasetId, {
				favourite_ids: favourites.map((f) => f.id)
			});
			onReportGenerated?.(report);
		} catch (err) {
			generateError = err instanceof Error ? err.message : 'Failed to generate report';
		} finally {
			generating = false;
		}
	}

	function handleExpandChart(fav: DatasetFavourite) {
		modalFigureJson = fav.figure_json as Record<string, unknown> | null;
		modalTitle = fav.title || 'Chart';
		modalOpen = true;
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		});
	}

	// Fetch on mount
	$effect(() => {
		fetchFavourites();
	});
</script>

<div class="space-y-4">
	{#if loading}
		<div class="space-y-4">
			{#each Array(3) as _}
				<ShimmerSkeleton type="card" />
			{/each}
		</div>
	{:else if error}
		<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4">
			<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
			<button
				onclick={fetchFavourites}
				class="mt-2 text-sm text-error-600 hover:text-error-700 dark:text-error-400"
			>
				Try again
			</button>
		</div>
	{:else if favourites.length === 0}
		<!-- Empty State -->
		<div class="text-center py-12">
			<svg class="w-16 h-16 mx-auto text-neutral-300 dark:text-neutral-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
			</svg>
			<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">No favourites yet</h3>
			<p class="text-neutral-600 dark:text-neutral-400 max-w-sm mx-auto">
				Star charts and insights from your analysis to collect them here. Then generate a report from your favourites.
			</p>
		</div>
	{:else}
		<!-- Favourites List -->
		<div class="space-y-4">
			{#each favourites as fav (fav.id)}
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 transition-all hover:border-brand-200 dark:hover:border-brand-800">
					<div class="flex items-start gap-4">
						<!-- Icon based on type -->
						<div class="flex-shrink-0">
							{#if fav.favourite_type === 'chart'}
								<div class="w-10 h-10 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
									<svg class="w-5 h-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
									</svg>
								</div>
							{:else}
								<div class="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
									<svg class="w-5 h-5 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
									</svg>
								</div>
							{/if}
						</div>

						<!-- Content -->
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2 mb-1">
								<span class="text-xs font-medium px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 capitalize">
									{fav.favourite_type}
								</span>
								<span class="text-xs text-neutral-500 dark:text-neutral-400">
									{formatDate(fav.created_at)}
								</span>
							</div>

							<h4 class="font-medium text-neutral-900 dark:text-white">
								{fav.title || 'Untitled'}
							</h4>

							{#if fav.content}
								<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1 line-clamp-2">
									{fav.content}
								</p>
							{/if}

							<!-- User Note -->
							{#if editingNoteId === fav.id}
								<div class="mt-2">
									<textarea
										bind:value={editNoteText}
										rows="2"
										class="w-full px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent"
										placeholder="Add a note..."
									></textarea>
									<div class="flex gap-2 mt-2">
										<button
											onclick={() => saveNote(fav.id)}
											class="px-3 py-1 text-xs rounded bg-brand-500 text-white hover:bg-brand-600 transition-colors"
										>
											Save
										</button>
										<button
											onclick={cancelEditNote}
											class="px-3 py-1 text-xs rounded bg-neutral-200 dark:bg-neutral-600 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-300 dark:hover:bg-neutral-500 transition-colors"
										>
											Cancel
										</button>
									</div>
								</div>
							{:else if fav.user_note}
								<div class="mt-2 text-sm text-neutral-500 dark:text-neutral-400 italic border-l-2 border-brand-300 dark:border-brand-700 pl-2">
									"{fav.user_note}"
								</div>
							{/if}

							<!-- Chart preview -->
							{#if fav.favourite_type === 'chart' && fav.figure_json}
								<div class="mt-3">
									<ChartRenderer
										figureJson={fav.figure_json}
										title=""
										viewMode="simple"
										height={180}
										onExpand={() => handleExpandChart(fav)}
									/>
								</div>
							{/if}
						</div>

						<!-- Actions -->
						<div class="flex items-center gap-1 flex-shrink-0">
							<button
								onclick={() => startEditNote(fav)}
								class="p-1.5 rounded text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
								title="Add note"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
								</svg>
							</button>
							<button
								onclick={() => handleDelete(fav.id)}
								disabled={deletingId === fav.id}
								class="p-1.5 rounded text-neutral-500 hover:text-error-600 dark:text-neutral-400 dark:hover:text-error-400 hover:bg-error-50 dark:hover:bg-error-900/20 transition-colors disabled:opacity-50"
								title="Remove from favourites"
							>
								{#if deletingId === fav.id}
									<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
								{:else}
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
									</svg>
								{/if}
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>

		<!-- Generate Report Button -->
		<div class="pt-4 border-t border-neutral-200 dark:border-neutral-700">
			{#if generateError}
				<div class="mb-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-3">
					<p class="text-sm text-error-700 dark:text-error-300">{generateError}</p>
				</div>
			{/if}
			<Button variant="brand" size="lg" onclick={generateReport} disabled={generating} class="w-full">
				{#snippet children()}
					{#if generating}
						<svg class="w-5 h-5 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Generating Report...
					{:else}
						<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
						Generate Report from {favourites.length} Favourite{favourites.length !== 1 ? 's' : ''}
					{/if}
				{/snippet}
			</Button>
		</div>
	{/if}
</div>

<!-- Chart Modal -->
<ChartModal
	bind:open={modalOpen}
	figureJson={modalFigureJson}
	title={modalTitle}
/>
