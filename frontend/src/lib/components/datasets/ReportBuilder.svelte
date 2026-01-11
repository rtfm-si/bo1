<script lang="ts">
	/**
	 * ReportBuilder - Slide-out panel for building and exporting data reports
	 *
	 * Features:
	 * - Collect insights from analysis and chat
	 * - Reorder and manage items
	 * - Generate executive summary via LLM
	 * - Export to Markdown or PDF
	 */
	import { fly } from 'svelte/transition';
	import { apiClient } from '$lib/api/client';
	import type {
		DatasetFavourite,
		DatasetReportResponse,
		ObjectiveInsight,
		ConversationMessage
	} from '$lib/api/types';
	import { Button } from '$lib/components/ui';

	interface SelectedInsight {
		id: string;
		type: 'insight' | 'chat_message' | 'favourite';
		headline?: string;
		content: string;
		chart_spec?: object;
		figure_json?: object;
		included: boolean;
	}

	interface Props {
		datasetId: string;
		datasetName?: string;
		isOpen: boolean;
		selectedInsights?: SelectedInsight[];
		onClose: () => void;
		onExport?: (format: 'markdown' | 'pdf') => void;
		onReportGenerated?: (report: DatasetReportResponse) => void;
	}

	let {
		datasetId,
		datasetName = 'Dataset',
		isOpen,
		selectedInsights = [],
		onClose,
		onExport,
		onReportGenerated
	}: Props = $props();

	// Local state
	let reportTitle = $state(`${datasetName} Analysis Report`);
	let isGenerating = $state(false);
	let isExporting = $state(false);
	let generatedReport = $state<DatasetReportResponse | null>(null);
	let error = $state<string | null>(null);
	let showExportMenu = $state(false);

	// Derived: count of included items
	const includedCount = $derived(selectedInsights.filter((i) => i.included).length);

	function removeInsight(index: number) {
		selectedInsights = selectedInsights.filter((_, i) => i !== index);
	}

	function toggleIncluded(index: number) {
		selectedInsights = selectedInsights.map((item, i) =>
			i === index ? { ...item, included: !item.included } : item
		);
	}

	function moveUp(index: number) {
		if (index <= 0) return;
		const newList = [...selectedInsights];
		[newList[index - 1], newList[index]] = [newList[index], newList[index - 1]];
		selectedInsights = newList;
	}

	function moveDown(index: number) {
		if (index >= selectedInsights.length - 1) return;
		const newList = [...selectedInsights];
		[newList[index], newList[index + 1]] = [newList[index + 1], newList[index]];
		selectedInsights = newList;
	}

	async function generateReport() {
		if (includedCount === 0) {
			error = 'Please select at least one item to include in the report';
			return;
		}

		isGenerating = true;
		error = null;

		try {
			// First, create favourites for items that don't have IDs
			const favouriteIds: string[] = [];

			for (const insight of selectedInsights.filter((i) => i.included)) {
				if (insight.type === 'favourite' && insight.id) {
					favouriteIds.push(insight.id);
				} else {
					// Create a favourite for this insight
					const favourite = await apiClient.createFavourite(datasetId, {
						favourite_type: insight.type === 'chat_message' ? 'message' : 'insight',
						title: insight.headline || 'Untitled',
						content: insight.content,
						chart_spec: insight.chart_spec as Record<string, unknown> | undefined,
						figure_json: insight.figure_json as Record<string, unknown> | undefined
					});
					favouriteIds.push(favourite.id);
				}
			}

			// Generate report
			const report = await apiClient.generateReport(datasetId, {
				title: reportTitle,
				favourite_ids: favouriteIds
			});

			generatedReport = report;
			onReportGenerated?.(report);
		} catch (err) {
			console.error('[ReportBuilder] Error generating report:', err);
			error = err instanceof Error ? err.message : 'Failed to generate report';
		} finally {
			isGenerating = false;
		}
	}

	async function handleExport(format: 'markdown' | 'pdf') {
		if (!generatedReport) {
			// Generate report first if needed
			await generateReport();
			if (!generatedReport) return;
		}

		isExporting = true;
		error = null;
		showExportMenu = false;

		try {
			const response = await apiClient.exportReport(datasetId, generatedReport.id, format);

			// Create download link
			const blob = new Blob([response], {
				type: format === 'markdown' ? 'text/markdown' : 'application/pdf'
			});
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${reportTitle.replace(/[^a-z0-9]/gi, '_')}.${format === 'markdown' ? 'md' : 'pdf'}`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);

			onExport?.(format);
		} catch (err) {
			console.error('[ReportBuilder] Export error:', err);
			error = err instanceof Error ? err.message : 'Failed to export report';
		} finally {
			isExporting = false;
		}
	}

	async function regenerateSummary() {
		if (!generatedReport) return;

		isGenerating = true;
		error = null;

		try {
			const result = await apiClient.regenerateReportSummary(datasetId, generatedReport.id);
			if (result.summary) {
				generatedReport = {
					...generatedReport,
					executive_summary: result.summary
				};
			}
		} catch (err) {
			console.error('[ReportBuilder] Summary regeneration error:', err);
			error = err instanceof Error ? err.message : 'Failed to regenerate summary';
		} finally {
			isGenerating = false;
		}
	}

	function handleClose() {
		showExportMenu = false;
		onClose();
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (isOpen && event.key === 'Escape') {
			handleClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeyDown} />

{#if isOpen}
	<!-- Backdrop -->
	<button
		type="button"
		class="fixed inset-0 bg-black/20 dark:bg-black/40 z-40"
		onclick={handleClose}
		aria-label="Close report panel"
	></button>

	<!-- Panel -->
	<aside
		class="fixed right-0 top-0 h-full w-96 max-w-[90vw] z-50 bg-white dark:bg-neutral-800 shadow-xl border-l border-neutral-200 dark:border-neutral-700 flex flex-col"
		transition:fly={{ x: 300, duration: 200 }}
	>
		<!-- Header -->
		<header class="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
			<div class="flex items-center gap-2">
				<svg class="w-5 h-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
				</svg>
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Your Report</h2>
				{#if includedCount > 0}
					<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300">
						{includedCount} items
					</span>
				{/if}
			</div>
			<button
				onclick={handleClose}
				class="p-1.5 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-500"
				aria-label="Close panel"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</header>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto p-4 space-y-4">
			<!-- Report Title -->
			<div>
				<label for="report-title" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
					Report Title
				</label>
				<input
					id="report-title"
					type="text"
					bind:value={reportTitle}
					class="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
					placeholder="Enter report title"
				/>
			</div>

			<!-- Error message -->
			{#if error}
				<div class="p-3 rounded-lg bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800">
					<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
				</div>
			{/if}

			<!-- Executive Summary (if generated) -->
			{#if generatedReport?.executive_summary}
				<div class="p-4 rounded-lg bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800">
					<div class="flex items-center justify-between mb-2">
						<h3 class="text-sm font-semibold text-brand-900 dark:text-brand-200">Executive Summary</h3>
						<button
							onclick={regenerateSummary}
							disabled={isGenerating}
							class="text-xs text-brand-600 dark:text-brand-400 hover:underline disabled:opacity-50"
						>
							Regenerate
						</button>
					</div>
					<p class="text-sm text-brand-800 dark:text-brand-300 leading-relaxed">
						{generatedReport.executive_summary}
					</p>
				</div>
			{/if}

			<!-- Insights List -->
			<div>
				<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
					Report Items
				</h3>
				{#if selectedInsights.length === 0}
					<div class="text-center py-8">
						<svg class="w-12 h-12 mx-auto text-neutral-300 dark:text-neutral-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
						<p class="text-sm text-neutral-500 dark:text-neutral-400">
							No items added yet
						</p>
						<p class="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
							Click "Add to Report" on insights or chat messages
						</p>
					</div>
				{:else}
					<ul class="space-y-2">
						{#each selectedInsights as insight, i (insight.id)}
							<li class="group relative bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-3 border border-neutral-200 dark:border-neutral-600">
								<div class="flex items-start gap-3">
									<!-- Checkbox -->
									<input
										type="checkbox"
										checked={insight.included}
										onchange={() => toggleIncluded(i)}
										class="mt-0.5 rounded border-neutral-300 dark:border-neutral-500 text-brand-600 focus:ring-brand-500"
									/>

									<!-- Content -->
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2 mb-1">
											<span class="inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded bg-neutral-200 dark:bg-neutral-600 text-neutral-600 dark:text-neutral-300">
												{insight.type === 'chat_message' ? 'Chat' : insight.type === 'favourite' ? 'Saved' : 'Insight'}
											</span>
											{#if insight.chart_spec || insight.figure_json}
												<span class="inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300">
													Chart
												</span>
											{/if}
										</div>
										<p class="text-sm font-medium text-neutral-900 dark:text-white truncate">
											{insight.headline || `Item ${i + 1}`}
										</p>
										{#if insight.content}
											<p class="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2 mt-0.5">
												{insight.content}
											</p>
										{/if}
									</div>

									<!-- Actions -->
									<div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
										<button
											onclick={() => moveUp(i)}
											disabled={i === 0}
											class="p-1 rounded hover:bg-neutral-200 dark:hover:bg-neutral-600 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 disabled:opacity-30"
											aria-label="Move up"
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
											</svg>
										</button>
										<button
											onclick={() => moveDown(i)}
											disabled={i === selectedInsights.length - 1}
											class="p-1 rounded hover:bg-neutral-200 dark:hover:bg-neutral-600 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 disabled:opacity-30"
											aria-label="Move down"
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
											</svg>
										</button>
										<button
											onclick={() => removeInsight(i)}
											class="p-1 rounded hover:bg-error-100 dark:hover:bg-error-900/30 text-neutral-400 hover:text-error-600 dark:hover:text-error-400"
											aria-label="Remove"
										>
											<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
											</svg>
										</button>
									</div>
								</div>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		</div>

		<!-- Footer Actions -->
		<footer class="px-4 py-3 border-t border-neutral-200 dark:border-neutral-700 space-y-3">
			<!-- Generate Button -->
			<Button
				variant="brand"
				size="md"
				onclick={generateReport}
				disabled={isGenerating || includedCount === 0}
				class="w-full"
			>
				{#snippet children()}
					{#if isGenerating}
						<svg class="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						Generating...
					{:else}
						<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
						</svg>
						{generatedReport ? 'Regenerate Report' : 'Generate Executive Summary'}
					{/if}
				{/snippet}
			</Button>

			<!-- Export Buttons -->
			<div class="flex gap-2">
				<div class="relative flex-1">
					<button
						onclick={() => showExportMenu = !showExportMenu}
						disabled={isExporting || (!generatedReport && includedCount === 0)}
						class="w-full inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
					>
						{#if isExporting}
							<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							Exporting...
						{:else}
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
							</svg>
							Export
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
							</svg>
						{/if}
					</button>

					<!-- Export Menu -->
					{#if showExportMenu}
						<div class="absolute bottom-full left-0 right-0 mb-1 bg-white dark:bg-neutral-700 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-600 overflow-hidden">
							<button
								onclick={() => handleExport('markdown')}
								class="w-full px-4 py-2.5 text-left text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-600 flex items-center gap-2"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
								</svg>
								Export as Markdown
							</button>
							<button
								onclick={() => handleExport('pdf')}
								class="w-full px-4 py-2.5 text-left text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-600 flex items-center gap-2"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
								</svg>
								Export as PDF
							</button>
						</div>
					{/if}
				</div>

				{#if generatedReport}
					<a
						href="/datasets/{datasetId}/report/{generatedReport.id}"
						class="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-600 transition-colors"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
						</svg>
						View
					</a>
				{/if}
			</div>
		</footer>
	</aside>
{/if}
