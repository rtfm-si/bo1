<script lang="ts">
	/**
	 * CompetitorManager - User-managed competitor list
	 *
	 * CRUD interface for competitors the user explicitly tracks.
	 * Distinct from AI-generated competitor insights.
	 */
	import {
		Building2,
		Plus,
		Trash2,
		Link2,
		FileText,
		Loader2,
		X,
		ExternalLink,
		Clock,
		AlertTriangle,
		RefreshCw,
		Sparkles,
		ChevronDown,
		ChevronUp
	} from 'lucide-svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Tooltip from '$lib/components/ui/Tooltip.svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import BoFormField from '$lib/components/ui/BoFormField.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { apiClient } from '$lib/api/client';
	import type { ManagedCompetitor } from '$lib/api/types';

	import { formatDate } from '$lib/utils/time-formatting';
	interface Props {
		/** Initial competitors to display */
		initialCompetitors?: ManagedCompetitor[];
		/** Callback when list changes */
		onUpdate?: (competitors: ManagedCompetitor[]) => void;
	}

	let { initialCompetitors = [], onUpdate }: Props = $props();

	// State
	let competitors = $state<ManagedCompetitor[]>(initialCompetitors);
	let isLoading = $state(false);
	let isAdding = $state(false);
	let showAddForm = $state(false);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);

	// Add form state
	let newName = $state('');
	let newUrl = $state('');
	let newNotes = $state('');

	// Editing state
	let editingName = $state<string | null>(null);
	let editUrl = $state('');
	let editNotes = $state('');

	// Enrichment state
	let enrichingName = $state<string | null>(null);
	let isEnrichingAll = $state(false);
	let expandedCompetitor = $state<string | null>(null);

	function clearMessages() {
		error = null;
		success = null;
	}

	async function loadCompetitors() {
		isLoading = true;
		clearMessages();
		try {
			const response = await apiClient.listManagedCompetitors();
			if (response.success) {
				competitors = response.competitors;
				onUpdate?.(competitors);
			} else {
				error = response.error || 'Failed to load competitors';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load competitors';
		} finally {
			isLoading = false;
		}
	}

	async function addCompetitor() {
		if (!newName.trim()) return;

		isAdding = true;
		clearMessages();
		try {
			const response = await apiClient.addManagedCompetitor({
				name: newName.trim(),
				url: newUrl.trim() || undefined,
				notes: newNotes.trim() || undefined
			});

			if (response.success && response.competitor) {
				competitors = [response.competitor, ...competitors];
				onUpdate?.(competitors);
				success = `Added "${newName}" to competitors`;
				resetAddForm();
			} else {
				error = response.error || 'Failed to add competitor';
			}
		} catch (e: unknown) {
			const errorMsg = e instanceof Error ? e.message : 'Failed to add competitor';
			if (errorMsg.includes('409') || errorMsg.includes('already exists')) {
				error = `Competitor "${newName}" already exists`;
			} else {
				error = errorMsg;
			}
		} finally {
			isAdding = false;
		}
	}

	function startEdit(competitor: ManagedCompetitor) {
		editingName = competitor.name;
		editUrl = competitor.url || '';
		editNotes = competitor.notes || '';
	}

	function cancelEdit() {
		editingName = null;
		editUrl = '';
		editNotes = '';
	}

	async function saveEdit() {
		if (!editingName) return;

		clearMessages();
		try {
			const response = await apiClient.updateManagedCompetitor(editingName, {
				url: editUrl.trim() || null,
				notes: editNotes.trim() || null
			});

			if (response.success && response.competitor) {
				competitors = competitors.map((c) =>
					c.name.toLowerCase() === editingName?.toLowerCase() ? response.competitor! : c
				);
				onUpdate?.(competitors);
				success = `Updated "${editingName}"`;
				cancelEdit();
			} else {
				error = response.error || 'Failed to update competitor';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update competitor';
		}
	}

	async function removeCompetitor(name: string) {
		clearMessages();
		try {
			const response = await apiClient.removeManagedCompetitor(name);
			if (response.status === 'deleted') {
				competitors = competitors.filter((c) => c.name.toLowerCase() !== name.toLowerCase());
				onUpdate?.(competitors);
				success = `Removed "${name}"`;
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to remove competitor';
		}
	}

	async function enrichCompetitor(name: string) {
		enrichingName = name;
		clearMessages();
		try {
			const response = await apiClient.enrichManagedCompetitor(name);
			if (response.success && response.competitor) {
				competitors = competitors.map((c) =>
					c.name.toLowerCase() === name.toLowerCase() ? response.competitor! : c
				);
				onUpdate?.(competitors);
				const changes = response.changes?.length || 0;
				success = changes > 0
					? `Enriched "${name}" - ${changes} field(s) updated`
					: `"${name}" is already up to date`;
				// Auto-expand to show enriched data
				expandedCompetitor = name;
			} else {
				error = response.error || 'Failed to enrich competitor';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to enrich competitor';
		} finally {
			enrichingName = null;
		}
	}

	async function enrichAllCompetitors() {
		if (competitors.length === 0) return;

		isEnrichingAll = true;
		clearMessages();
		try {
			const response = await apiClient.enrichAllManagedCompetitors();
			if (response.success) {
				competitors = response.competitors;
				onUpdate?.(competitors);
				success = `Enriched ${response.enriched_count} competitor(s)`;
			} else {
				// Partial success - some may have failed
				competitors = response.competitors;
				onUpdate?.(competitors);
				const errorMsg = response.errors?.join(', ') || 'Some enrichments failed';
				error = `Enriched ${response.enriched_count}/${competitors.length}: ${errorMsg}`;
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to enrich competitors';
		} finally {
			isEnrichingAll = false;
		}
	}

	function toggleExpand(name: string) {
		expandedCompetitor = expandedCompetitor === name ? null : name;
	}

	function hasEnrichmentData(competitor: ManagedCompetitor): boolean {
		return !!(
			competitor.tagline ||
			competitor.product_description ||
			competitor.funding_info ||
			competitor.employee_count ||
			competitor.recent_news?.length ||
			competitor.key_signals?.length ||
			competitor.product_updates?.length ||
			competitor.funding_rounds?.length
		);
	}

	function hasDeepIntel(competitor: ManagedCompetitor): boolean {
		return !!(
			competitor.key_signals?.length ||
			competitor.product_updates?.length ||
			competitor.funding_rounds?.length
		);
	}

	function resetAddForm() {
		showAddForm = false;
		newName = '';
		newUrl = '';
		newNotes = '';
	}


	function getRelevanceBadge(score: number | null | undefined): { label: string; variant: 'success' | 'warning' | 'error'; tooltip: string } {
		if (score === null || score === undefined) {
			return { label: '', variant: 'success', tooltip: '' };
		}
		if (score > 0.66) {
			return { label: 'High', variant: 'success', tooltip: 'Strong match: similar product, target customer, and market' };
		}
		if (score > 0.33) {
			return { label: 'Medium', variant: 'warning', tooltip: 'Partial match: some overlap in product or market' };
		}
		return { label: 'Low', variant: 'error', tooltip: 'Weak match: may not be a direct competitor' };
	}

	// Load on mount if no initial data provided
	$effect(() => {
		if (initialCompetitors.length === 0) {
			loadCompetitors();
		}
	});
</script>

<div class="space-y-4">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-2">
			<Building2 class="h-5 w-5 text-brand-600 dark:text-brand-400" />
			<h3 class="font-semibold text-neutral-900 dark:text-neutral-100">Competitors</h3>
			<span class="text-sm text-neutral-500">({competitors.length})</span>
		</div>
		<div class="flex items-center gap-2">
			{#if competitors.length > 0}
				<Tooltip text="Enrich all competitors with latest data (monthly refresh)">
					<BoButton
						variant="outline"
						size="sm"
						onclick={enrichAllCompetitors}
						disabled={isEnrichingAll || enrichingName !== null}
					>
						{#if isEnrichingAll}
							<Loader2 class="h-4 w-4 mr-1.5 animate-spin" />
							Enriching...
						{:else}
							<RefreshCw class="h-4 w-4 mr-1.5" />
							Refresh All
						{/if}
					</BoButton>
				</Tooltip>
			{/if}
			{#if !showAddForm}
				<BoButton variant="outline" size="sm" onclick={() => (showAddForm = true)}>
					<Plus class="h-4 w-4 mr-1.5" />
					Add Competitor
				</BoButton>
			{/if}
		</div>
	</div>

	<!-- Success/Error Alerts -->
	{#if success}
		<Alert variant="success">
			{success}
		</Alert>
	{/if}

	{#if error}
		<Alert variant="error">
			{error}
			<button class="ml-2 underline" onclick={loadCompetitors}>Retry</button>
		</Alert>
	{/if}

	<!-- Add Form -->
	{#if showAddForm}
		<BoCard variant="bordered" padding="md">
			<div class="space-y-4">
				<div class="flex items-center justify-between">
					<h4 class="font-medium text-neutral-900 dark:text-neutral-100">Add Competitor</h4>
					<BoButton variant="ghost" size="sm" onclick={resetAddForm}>
						<X class="h-4 w-4" />
					</BoButton>
				</div>

				<BoFormField label="Company Name" required>
					<Input
						type="text"
						bind:value={newName}
						placeholder="e.g., Acme Corp"
						maxlength={100}
					/>
				</BoFormField>

				<BoFormField label="Website URL">
					<Input
						type="url"
						bind:value={newUrl}
						placeholder="https://example.com"
						maxlength={500}
					/>
				</BoFormField>

				<BoFormField label="Notes">
					<textarea
						bind:value={newNotes}
						placeholder="Why is this a competitor? Key differentiators?"
						rows={2}
						maxlength={1000}
						class="w-full px-3 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-200 resize-none"
					></textarea>
				</BoFormField>

				<div class="flex justify-end gap-2">
					<BoButton variant="ghost" onclick={resetAddForm}>Cancel</BoButton>
					<BoButton
						variant="brand"
						onclick={addCompetitor}
						disabled={!newName.trim() || isAdding}
					>
						{#if isAdding}
							<Loader2 class="h-4 w-4 mr-1.5 animate-spin" />
						{:else}
							<Plus class="h-4 w-4 mr-1.5" />
						{/if}
						Add Competitor
					</BoButton>
				</div>
			</div>
		</BoCard>
	{/if}

	<!-- Loading State -->
	{#if isLoading}
		<div class="flex items-center justify-center py-8 text-neutral-500">
			<Loader2 class="h-5 w-5 animate-spin mr-2" />
			<span>Loading competitors...</span>
		</div>
	{:else if competitors.length === 0 && !showAddForm}
		<!-- Empty State -->
		<BoCard variant="bordered" padding="md">
			<div class="text-center py-4">
				<Building2 class="h-8 w-8 text-neutral-400 mx-auto mb-2" />
				<p class="text-neutral-600 dark:text-neutral-400">
					No competitors tracked yet. Add your first competitor to start monitoring.
				</p>
				<BoButton variant="outline" size="sm" class="mt-4" onclick={() => (showAddForm = true)}>
					<Plus class="h-4 w-4 mr-1.5" />
					Add Competitor
				</BoButton>
			</div>
		</BoCard>
	{:else}
		<!-- Competitor List -->
		<div class="space-y-3">
			{#each competitors as competitor (competitor.name)}
				<BoCard variant="bordered" padding="sm">
					{#if editingName === competitor.name}
						<!-- Edit Mode -->
						<div class="space-y-3">
							<div class="font-medium text-neutral-900 dark:text-neutral-100">
								{competitor.name}
							</div>

							<BoFormField label="Website URL">
								<Input
									type="url"
									bind:value={editUrl}
									placeholder="https://example.com"
									maxlength={500}
								/>
							</BoFormField>

							<BoFormField label="Notes">
								<textarea
									bind:value={editNotes}
									placeholder="Why is this a competitor?"
									rows={2}
									maxlength={1000}
									class="w-full px-3 py-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors duration-200 resize-none"
								></textarea>
							</BoFormField>

							<div class="flex justify-end gap-2">
								<BoButton variant="ghost" size="sm" onclick={cancelEdit}>Cancel</BoButton>
								<BoButton variant="brand" size="sm" onclick={saveEdit}>Save</BoButton>
							</div>
						</div>
					{:else}
						<!-- View Mode -->
						<div>
							<div class="flex items-start justify-between">
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<h4 class="font-medium text-neutral-900 dark:text-neutral-100 truncate">
											{competitor.name}
										</h4>
										{#if competitor.url}
											<a
												href={competitor.url}
												target="_blank"
												rel="noopener noreferrer"
												class="text-brand-600 hover:text-brand-700 dark:text-brand-400"
												title="Visit website"
											>
												<ExternalLink class="h-4 w-4" />
											</a>
										{/if}
										<!-- Relevance badge -->
										{#if competitor.relevance_score !== null && competitor.relevance_score !== undefined}
											{@const badge = getRelevanceBadge(competitor.relevance_score)}
											<Tooltip text={badge.tooltip}>
												<Badge variant={badge.variant} size="sm">{badge.label}</Badge>
											</Tooltip>
										{/if}
										<!-- Enriched indicator -->
										{#if competitor.last_enriched_at}
											<Tooltip text={`Last enriched ${formatDate(competitor.last_enriched_at)}`}>
												<Sparkles class="h-4 w-4 text-brand-500" />
											</Tooltip>
										{/if}
										<!-- Warning indicator -->
										{#if competitor.relevance_warning}
											<Tooltip text={competitor.relevance_warning}>
												<AlertTriangle class="h-4 w-4 text-warning-500" />
											</Tooltip>
										{/if}
									</div>

									{#if competitor.tagline}
										<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1 italic">
											{competitor.tagline}
										</p>
									{:else if competitor.notes}
										<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1 line-clamp-2">
											{competitor.notes}
										</p>
									{/if}

									<div class="flex items-center gap-4 mt-2 text-xs text-neutral-500">
										<div class="flex items-center gap-1">
											<Clock class="h-3 w-3" />
											<span>Added {formatDate(competitor.added_at)}</span>
										</div>
										{#if competitor.last_enriched_at}
											<div class="flex items-center gap-1">
												<RefreshCw class="h-3 w-3" />
												<span>Updated {formatDate(competitor.last_enriched_at)}</span>
											</div>
										{/if}
									</div>
								</div>

								<div class="flex items-center gap-1 ml-3">
									<!-- Expand/Collapse button for enrichment data -->
									{#if hasEnrichmentData(competitor)}
										<Tooltip text={expandedCompetitor === competitor.name ? 'Collapse details' : 'Show enriched data'}>
											<BoButton
												variant="ghost"
												size="sm"
												onclick={() => toggleExpand(competitor.name)}
												ariaLabel="Toggle details"
											>
												{#if expandedCompetitor === competitor.name}
													<ChevronUp class="h-4 w-4" />
												{:else}
													<ChevronDown class="h-4 w-4" />
												{/if}
											</BoButton>
										</Tooltip>
									{/if}
									<!-- Enrich button -->
									<Tooltip text="Fetch latest data about this competitor">
										<BoButton
											variant="ghost"
											size="sm"
											onclick={() => enrichCompetitor(competitor.name)}
											disabled={enrichingName !== null || isEnrichingAll}
											ariaLabel="Enrich competitor"
										>
											{#if enrichingName === competitor.name}
												<Loader2 class="h-4 w-4 animate-spin" />
											{:else}
												<RefreshCw class="h-4 w-4" />
											{/if}
										</BoButton>
									</Tooltip>
									<BoButton
										variant="ghost"
										size="sm"
										onclick={() => startEdit(competitor)}
										ariaLabel="Edit competitor"
									>
										<FileText class="h-4 w-4" />
									</BoButton>
									<BoButton
										variant="ghost"
										size="sm"
										onclick={() => removeCompetitor(competitor.name)}
										ariaLabel="Remove competitor"
									>
										<Trash2 class="h-4 w-4 text-error-500" />
									</BoButton>
								</div>
							</div>

							<!-- Expandable Enrichment Details -->
							{#if expandedCompetitor === competitor.name && hasEnrichmentData(competitor)}
								<div class="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700 space-y-3">
									{#if competitor.product_description}
										<div>
											<span class="text-xs font-medium text-neutral-500 uppercase tracking-wide">Description</span>
											<p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1">
												{competitor.product_description}
											</p>
										</div>
									{/if}

									<div class="grid grid-cols-2 gap-4">
										{#if competitor.employee_count}
											<div>
												<span class="text-xs font-medium text-neutral-500 uppercase tracking-wide">Employees</span>
												<p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1">
													{competitor.employee_count}
												</p>
											</div>
										{/if}
										{#if competitor.funding_info}
											<div>
												<span class="text-xs font-medium text-neutral-500 uppercase tracking-wide">Funding</span>
												<p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1 line-clamp-2">
													{competitor.funding_info}
												</p>
											</div>
										{/if}
									</div>

									{#if competitor.recent_news && competitor.recent_news.length > 0}
										<div>
											<span class="text-xs font-medium text-neutral-500 uppercase tracking-wide">Recent News</span>
											<ul class="mt-1 space-y-1">
												{#each competitor.recent_news.slice(0, 3) as news}
													<li class="text-sm">
														<a
															href={news.url}
															target="_blank"
															rel="noopener noreferrer"
															class="text-brand-600 hover:text-brand-700 dark:text-brand-400 hover:underline"
														>
															{news.title}
														</a>
													</li>
												{/each}
											</ul>
										</div>
									{/if}

									<!-- Deep Intelligence Section (Pro tier) -->
									{#if hasDeepIntel(competitor)}
										<div class="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-700">
											<div class="flex items-center gap-2 mb-3">
												<Sparkles class="h-4 w-4 text-brand-500" />
												<span class="text-xs font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Deep Intelligence</span>
												{#if competitor.intel_gathered_at}
													<span class="text-xs text-neutral-500">
														(gathered {formatDate(competitor.intel_gathered_at)})
													</span>
												{/if}
											</div>

											<!-- Key Signals -->
											{#if competitor.key_signals && competitor.key_signals.length > 0}
												<div class="mb-3">
													<span class="text-xs font-medium text-neutral-500 uppercase tracking-wide">Key Signals</span>
													<div class="flex flex-wrap gap-2 mt-1">
														{#each competitor.key_signals as signal}
															<Badge variant="neutral" size="sm">{signal}</Badge>
														{/each}
													</div>
												</div>
											{/if}

											<!-- Funding Rounds -->
											{#if competitor.funding_rounds && competitor.funding_rounds.length > 0}
												<div class="mb-3">
													<span class="text-xs font-medium text-neutral-500 uppercase tracking-wide">Funding</span>
													<div class="space-y-2 mt-1">
														{#each competitor.funding_rounds.slice(0, 3) as round}
															<div class="flex items-center gap-2 text-sm">
																<Badge variant="success" size="sm">{round.round_type}</Badge>
																{#if round.amount}
																	<span class="font-medium text-neutral-700 dark:text-neutral-300">{round.amount}</span>
																{/if}
																{#if round.date}
																	<span class="text-neutral-500">({round.date})</span>
																{/if}
															</div>
															{#if round.investors && round.investors.length > 0}
																<p class="text-xs text-neutral-500 ml-4">
																	Investors: {round.investors.slice(0, 3).join(', ')}{round.investors.length > 3 ? '...' : ''}
																</p>
															{/if}
														{/each}
													</div>
												</div>
											{/if}

											<!-- Product Updates -->
											{#if competitor.product_updates && competitor.product_updates.length > 0}
												<div>
													<span class="text-xs font-medium text-neutral-500 uppercase tracking-wide">Product Updates</span>
													<ul class="mt-1 space-y-2">
														{#each competitor.product_updates.slice(0, 3) as update}
															<li class="text-sm">
																<div class="flex items-start gap-2">
																	{#if update.date}
																		<span class="text-xs text-neutral-500 whitespace-nowrap">{update.date}</span>
																	{/if}
																	<div>
																		{#if update.source_url}
																			<a
																				href={update.source_url}
																				target="_blank"
																				rel="noopener noreferrer"
																				class="text-brand-600 hover:text-brand-700 dark:text-brand-400 hover:underline font-medium"
																			>
																				{update.title}
																			</a>
																		{:else}
																			<span class="font-medium text-neutral-700 dark:text-neutral-300">{update.title}</span>
																		{/if}
																		{#if update.description}
																			<p class="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5">{update.description}</p>
																		{/if}
																	</div>
																</div>
															</li>
														{/each}
													</ul>
												</div>
											{/if}
										</div>
									{/if}

									{#if competitor.changes_detected && competitor.changes_detected.length > 0}
										<div class="flex items-center gap-2 text-xs text-warning-600 dark:text-warning-400">
											<AlertTriangle class="h-3 w-3" />
											<span>Changes detected: {competitor.changes_detected.join(', ')}</span>
										</div>
									{/if}
								</div>
							{/if}
						</div>
					{/if}
				</BoCard>
			{/each}
		</div>
	{/if}
</div>
