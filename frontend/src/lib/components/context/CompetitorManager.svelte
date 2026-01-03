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
		AlertTriangle
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

	function resetAddForm() {
		showAddForm = false;
		newName = '';
		newUrl = '';
		newNotes = '';
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
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
		{#if !showAddForm}
			<BoButton variant="outline" size="sm" onclick={() => (showAddForm = true)}>
				<Plus class="h-4 w-4 mr-1.5" />
				Add Competitor
			</BoButton>
		{/if}
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
									<!-- Warning indicator -->
									{#if competitor.relevance_warning}
										<Tooltip text={competitor.relevance_warning}>
											<AlertTriangle class="h-4 w-4 text-amber-500" />
										</Tooltip>
									{/if}
								</div>

								{#if competitor.notes}
									<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1 line-clamp-2">
										{competitor.notes}
									</p>
								{/if}

								<div class="flex items-center gap-4 mt-2 text-xs text-neutral-500">
									<div class="flex items-center gap-1">
										<Clock class="h-3 w-3" />
										<span>Added {formatDate(competitor.added_at)}</span>
									</div>
								</div>
							</div>

							<div class="flex items-center gap-1 ml-3">
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
									<Trash2 class="h-4 w-4 text-red-500" />
								</BoButton>
							</div>
						</div>
					{/if}
				</BoCard>
			{/each}
		</div>
	{/if}
</div>
