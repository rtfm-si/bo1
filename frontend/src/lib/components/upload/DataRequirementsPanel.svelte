<script lang="ts">
	/**
	 * DataRequirementsPanel - Shows data requirements for a selected objective
	 * Displays essential data, valuable additions, and data sources
	 */
	import { Button } from '$lib/components/ui';

	interface EssentialData {
		name: string;
		description: string;
		example_columns: string[];
		why_essential: string;
		questions_answered: string[];
	}

	interface ValuableAddition {
		name: string;
		description: string;
		insight_unlocked: string;
		priority: 'high' | 'medium' | 'low';
	}

	interface DataSource {
		source_type: string;
		example_tools: string[];
		typical_export_name: string;
		columns_typically_included: string[];
	}

	interface DataRequirements {
		objective_summary: string;
		essential_data: EssentialData[];
		valuable_additions: ValuableAddition[];
		data_sources: DataSource[];
		analysis_preview: string;
	}

	let {
		requirements = null,
		loading = false,
		error = null,
		objectiveName,
		onUploadClick,
		onBackClick,
	}: {
		requirements: DataRequirements | null;
		loading?: boolean;
		error?: string | null;
		objectiveName: string;
		onUploadClick: () => void;
		onBackClick: () => void;
	} = $props();
</script>

<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
	<!-- Header -->
	<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/50">
		<div class="flex items-center gap-2">
			<svg
				class="w-5 h-5 text-brand-500"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
				/>
			</svg>
			<h3 class="font-semibold text-neutral-900 dark:text-white">
				To analyze "{objectiveName}"
			</h3>
		</div>
	</div>

	<!-- Content -->
	<div class="p-6">
		{#if loading}
			<div class="flex flex-col items-center justify-center py-12">
				<svg
					class="w-8 h-8 text-brand-500 animate-spin"
					fill="none"
					viewBox="0 0 24 24"
				>
					<circle
						class="opacity-25"
						cx="12"
						cy="12"
						r="10"
						stroke="currentColor"
						stroke-width="4"
					></circle>
					<path
						class="opacity-75"
						fill="currentColor"
						d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
					></path>
				</svg>
				<p class="mt-3 text-neutral-600 dark:text-neutral-400">
					Analyzing data requirements...
				</p>
			</div>
		{:else if error}
			<div class="text-center py-8">
				<svg
					class="w-12 h-12 mx-auto text-error-500 mb-3"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<p class="text-error-600 dark:text-error-400">{error}</p>
				<Button variant="outline" size="sm" class="mt-4" onclick={onBackClick}>
					Try again
				</Button>
			</div>
		{:else if requirements}
			<div class="space-y-6">
				<!-- Objective Summary -->
				{#if requirements.objective_summary}
					<p class="text-neutral-600 dark:text-neutral-400">
						{requirements.objective_summary}
					</p>
				{/if}

				<!-- Essential Data -->
				{#if requirements.essential_data.length > 0}
					<div>
						<h4 class="text-sm font-semibold text-neutral-900 dark:text-white uppercase tracking-wide mb-3">
							Essential Data
						</h4>
						<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-3">
							These columns are required for meaningful analysis:
						</p>
						<ul class="space-y-3">
							{#each requirements.essential_data as item, i (i)}
								<li class="flex items-start gap-3">
									<svg
										class="w-5 h-5 text-success-500 flex-shrink-0 mt-0.5"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M5 13l4 4L19 7"
										/>
									</svg>
									<div>
										<p class="font-medium text-neutral-900 dark:text-white">
											{item.name}
										</p>
										<p class="text-sm text-neutral-500 dark:text-neutral-400">
											{item.description}
										</p>
										{#if item.example_columns.length > 0}
											<p class="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
												e.g., {item.example_columns.join(', ')}
											</p>
										{/if}
									</div>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Valuable Additions -->
				{#if requirements.valuable_additions.length > 0}
					<div class="pt-4 border-t border-neutral-200 dark:border-neutral-700">
						<h4 class="text-sm font-semibold text-neutral-900 dark:text-white uppercase tracking-wide mb-3">
							Valuable Additions
						</h4>
						<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-3">
							These would strengthen the analysis:
						</p>
						<ul class="space-y-3">
							{#each requirements.valuable_additions as item, i (i)}
								<li class="flex items-start gap-3">
									<svg
										class="w-5 h-5 text-brand-500 flex-shrink-0 mt-0.5"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M12 4v16m8-8H4"
										/>
									</svg>
									<div>
										<p class="font-medium text-neutral-900 dark:text-white">
											{item.name}
											{#if item.priority === 'high'}
												<span class="ml-2 text-xs px-1.5 py-0.5 rounded bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300">
													high impact
												</span>
											{/if}
										</p>
										<p class="text-sm text-neutral-500 dark:text-neutral-400">
											{item.insight_unlocked}
										</p>
									</div>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Data Sources -->
				{#if requirements.data_sources.length > 0}
					<div class="pt-4 border-t border-neutral-200 dark:border-neutral-700">
						<h4 class="text-sm font-semibold text-neutral-900 dark:text-white uppercase tracking-wide mb-3">
							Where to Find This Data
						</h4>
						<ul class="space-y-2">
							{#each requirements.data_sources as source, i (i)}
								<li class="flex items-start gap-2 text-sm">
									<span class="text-neutral-400 dark:text-neutral-500">*</span>
									<span class="text-neutral-600 dark:text-neutral-400">
										<span class="font-medium text-neutral-700 dark:text-neutral-300">
											{source.source_type}
										</span>
										{#if source.example_tools.length > 0}
											({source.example_tools.join(', ')})
										{/if}
									</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Analysis Preview -->
				{#if requirements.analysis_preview}
					<div class="pt-4 border-t border-neutral-200 dark:border-neutral-700">
						<p class="text-sm text-neutral-600 dark:text-neutral-400 italic">
							{requirements.analysis_preview}
						</p>
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Footer Actions -->
	<div class="px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/50">
		<div class="flex flex-col sm:flex-row gap-3">
			<Button variant="brand" class="flex-1 sm:flex-none" onclick={onUploadClick}>
				I have this data - Upload now
			</Button>
			<Button variant="outline" class="flex-1 sm:flex-none" onclick={onBackClick}>
				Check another objective
			</Button>
		</div>
	</div>
</div>
