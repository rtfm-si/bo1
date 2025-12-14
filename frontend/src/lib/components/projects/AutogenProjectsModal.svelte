<script lang="ts">
	/**
	 * AutogenProjectsModal Component - Shows AI-suggested projects
	 *
	 * Features:
	 * - Two tabs: "From Actions" and "From Business Context"
	 * - Actions tab: Clusters unassigned actions into project suggestions
	 * - Context tab: Suggests projects from business priorities
	 * - Loading states, checkbox selection, create button
	 */
	import Modal from '$lib/components/ui/Modal.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';
	import { apiClient } from '$lib/api/client';
	import type {
		AutogenSuggestion,
		ContextProjectSuggestion,
		ProjectDetailResponse
	} from '$lib/api/types';

	interface Props {
		open?: boolean;
		onclose?: () => void;
		onsuccess?: (projects: ProjectDetailResponse[]) => void;
	}

	let { open = $bindable(false), onclose, onsuccess }: Props = $props();

	// Tab state
	type Tab = 'actions' | 'context';
	let activeTab = $state<Tab>('actions');

	// Actions tab state
	let actionsLoading = $state(true);
	let actionsError = $state<string | null>(null);
	let actionsSuggestions = $state<AutogenSuggestion[]>([]);
	let actionsSelectedIds = $state<Set<string>>(new Set());
	let unassignedCount = $state(0);
	let minRequired = $state(3);

	// Context tab state
	let contextLoading = $state(true);
	let contextError = $state<string | null>(null);
	let contextSuggestions = $state<ContextProjectSuggestion[]>([]);
	let contextSelectedIds = $state<Set<string>>(new Set());
	let contextCompleteness = $state(0);
	let hasMinimumContext = $state(false);
	let missingFields = $state<string[]>([]);

	// Creating state (shared)
	let isCreating = $state(false);

	// Load data when modal opens or tab changes
	$effect(() => {
		if (open) {
			if (activeTab === 'actions') {
				loadActionsSuggestions();
			} else {
				loadContextSuggestions();
			}
		} else {
			// Reset state on close
			resetState();
		}
	});

	function resetState() {
		actionsSuggestions = [];
		actionsSelectedIds = new Set();
		actionsError = null;
		contextSuggestions = [];
		contextSelectedIds = new Set();
		contextError = null;
	}

	async function loadActionsSuggestions() {
		actionsLoading = true;
		actionsError = null;

		try {
			const response = await apiClient.getAutogenSuggestions();
			actionsSuggestions = response.suggestions;
			unassignedCount = response.unassigned_count;
			minRequired = response.min_required;
		} catch (e) {
			actionsError = e instanceof Error ? e.message : 'Failed to analyze actions';
		} finally {
			actionsLoading = false;
		}
	}

	async function loadContextSuggestions() {
		contextLoading = true;
		contextError = null;

		try {
			const response = await apiClient.getContextProjectSuggestions();
			contextSuggestions = response.suggestions;
			contextCompleteness = response.context_completeness;
			hasMinimumContext = response.has_minimum_context;
			missingFields = response.missing_fields;
		} catch (e) {
			contextError = e instanceof Error ? e.message : 'Failed to generate suggestions';
		} finally {
			contextLoading = false;
		}
	}

	function toggleActionsSelection(id: string) {
		const newSet = new Set(actionsSelectedIds);
		if (newSet.has(id)) {
			newSet.delete(id);
		} else {
			newSet.add(id);
		}
		actionsSelectedIds = newSet;
	}

	function toggleContextSelection(id: string) {
		const newSet = new Set(contextSelectedIds);
		if (newSet.has(id)) {
			newSet.delete(id);
		} else {
			newSet.add(id);
		}
		contextSelectedIds = newSet;
	}

	function selectAllActions() {
		actionsSelectedIds = new Set(actionsSuggestions.map((s) => s.id));
	}

	function deselectAllActions() {
		actionsSelectedIds = new Set();
	}

	function selectAllContext() {
		contextSelectedIds = new Set(contextSuggestions.map((s) => s.id));
	}

	function deselectAllContext() {
		contextSelectedIds = new Set();
	}

	async function handleCreate() {
		const selectedIds = activeTab === 'actions' ? actionsSelectedIds : contextSelectedIds;
		if (selectedIds.size === 0) return;

		isCreating = true;

		try {
			if (activeTab === 'actions') {
				const selectedSuggestions = actionsSuggestions.filter((s) => actionsSelectedIds.has(s.id));
				const response = await apiClient.createFromAutogenSuggestions(selectedSuggestions);
				open = false;
				onsuccess?.(response.created_projects);
			} else {
				const selectedSuggestions = contextSuggestions.filter((s) => contextSelectedIds.has(s.id));
				const response = await apiClient.createFromContextSuggestions(selectedSuggestions);
				open = false;
				onsuccess?.(response.created_projects);
			}
		} catch (e) {
			if (activeTab === 'actions') {
				actionsError = e instanceof Error ? e.message : 'Failed to create projects';
			} else {
				contextError = e instanceof Error ? e.message : 'Failed to create projects';
			}
		} finally {
			isCreating = false;
		}
	}

	function handleClose() {
		if (!isCreating) {
			onclose?.();
		}
	}

	// Computed
	let actionsSelectedCount = $derived(actionsSelectedIds.size);
	let contextSelectedCount = $derived(contextSelectedIds.size);
	let totalActionCount = $derived(
		actionsSuggestions
			.filter((s) => actionsSelectedIds.has(s.id))
			.reduce((sum, s) => sum + s.action_ids.length, 0)
	);

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.8) return 'text-success-600 dark:text-success-400';
		if (confidence >= 0.7) return 'text-brand-600 dark:text-brand-400';
		return 'text-warning-600 dark:text-warning-400';
	}

	function formatConfidence(confidence: number): string {
		return `${Math.round(confidence * 100)}%`;
	}

	function getCategoryColor(category: string): string {
		switch (category) {
			case 'strategy':
				return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
			case 'growth':
				return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
			case 'operations':
				return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
			case 'product':
				return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400';
			case 'marketing':
				return 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400';
			case 'finance':
				return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
			default:
				return 'bg-neutral-100 text-neutral-700 dark:bg-neutral-900/30 dark:text-neutral-400';
		}
	}

	function getPriorityColor(priority: string): string {
		switch (priority) {
			case 'high':
				return 'text-error-600 dark:text-error-400';
			case 'medium':
				return 'text-warning-600 dark:text-warning-400';
			case 'low':
				return 'text-neutral-500';
			default:
				return 'text-neutral-500';
		}
	}

	function formatFieldName(field: string): string {
		return field.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
	}
</script>

<Modal {open} title="Generate Project Ideas" size="lg" onclose={handleClose}>
	<!-- Tabs -->
	<div class="flex border-b border-neutral-200 dark:border-neutral-700 mb-4 -mt-2">
		<button
			type="button"
			onclick={() => (activeTab = 'actions')}
			class="px-4 py-2 text-sm font-medium border-b-2 transition-colors {activeTab === 'actions'
				? 'border-brand-500 text-brand-600 dark:text-brand-400'
				: 'border-transparent text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300'}"
		>
			From Actions
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'context')}
			class="px-4 py-2 text-sm font-medium border-b-2 transition-colors {activeTab === 'context'
				? 'border-brand-500 text-brand-600 dark:text-brand-400'
				: 'border-transparent text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300'}"
		>
			From Business Context
		</button>
	</div>

	<!-- Actions Tab Content -->
	{#if activeTab === 'actions'}
		{#if actionsError}
			<Alert variant="error" class="mb-4">{actionsError}</Alert>
		{/if}

		{#if actionsLoading}
			<div class="space-y-4">
				<p class="text-sm text-neutral-600 dark:text-neutral-400">
					Analyzing your unassigned actions to suggest project groupings...
				</p>
				<div class="space-y-3">
					<ShimmerSkeleton type="list-item" />
					<ShimmerSkeleton type="list-item" />
					<ShimmerSkeleton type="list-item" />
				</div>
			</div>
		{:else if actionsSuggestions.length === 0}
			<div class="text-center py-8">
				<div class="text-4xl mb-3">📊</div>
				{#if unassignedCount < minRequired}
					<p class="text-neutral-600 dark:text-neutral-400">
						You need at least <strong>{minRequired}</strong> unassigned actions to autogenerate projects.
					</p>
					<p class="text-sm text-neutral-500 mt-2">
						Currently you have <strong>{unassignedCount}</strong> unassigned action{unassignedCount ===
						1
							? ''
							: 's'}.
					</p>
				{:else}
					<p class="text-neutral-600 dark:text-neutral-400">
						No clear project groupings found for your unassigned actions.
					</p>
					<p class="text-sm text-neutral-500 mt-2">
						Try the "From Business Context" tab or create projects manually.
					</p>
				{/if}
			</div>
		{:else}
			<div class="space-y-4">
				<div class="flex items-center justify-between">
					<p class="text-sm text-neutral-600 dark:text-neutral-400">
						Found <strong>{actionsSuggestions.length}</strong> suggested
						project{actionsSuggestions.length === 1 ? '' : 's'} from <strong>{unassignedCount}</strong>
						unassigned actions.
					</p>
					<div class="flex gap-2">
						<button
							type="button"
							onclick={selectAllActions}
							class="text-xs text-brand-600 dark:text-brand-400 hover:underline"
						>
							Select All
						</button>
						<span class="text-neutral-300 dark:text-neutral-600">|</span>
						<button
							type="button"
							onclick={deselectAllActions}
							class="text-xs text-brand-600 dark:text-brand-400 hover:underline"
						>
							Clear
						</button>
					</div>
				</div>

				<div class="space-y-3 max-h-[400px] overflow-y-auto pr-1">
					{#each actionsSuggestions as suggestion (suggestion.id)}
						<div
							class="border rounded-lg p-4 transition-colors {actionsSelectedIds.has(suggestion.id)
								? 'border-brand-500 bg-brand-50/50 dark:bg-brand-900/10'
								: 'border-neutral-200 dark:border-neutral-700'}"
						>
							<div class="flex items-start gap-3">
								<input
									type="checkbox"
									checked={actionsSelectedIds.has(suggestion.id)}
									onchange={() => toggleActionsSelection(suggestion.id)}
									class="w-4 h-4 mt-1 text-brand-600 bg-white dark:bg-neutral-800 border-neutral-300 dark:border-neutral-600 rounded focus:ring-brand-500 focus:ring-2"
								/>
								<div class="flex-1 min-w-0">
									<div class="flex items-center justify-between gap-2">
										<h4 class="font-medium text-neutral-900 dark:text-neutral-100 truncate">
											{suggestion.name}
										</h4>
										<span
											class="text-xs {getConfidenceColor(suggestion.confidence)} whitespace-nowrap"
										>
											{formatConfidence(suggestion.confidence)} confidence
										</span>
									</div>
									{#if suggestion.description}
										<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1 line-clamp-2">
											{suggestion.description}
										</p>
									{/if}
									<div class="flex items-center gap-4 mt-2 text-xs text-neutral-500">
										<span class="flex items-center gap-1">
											<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
												/>
											</svg>
											{suggestion.action_ids.length} action{suggestion.action_ids.length === 1
												? ''
												: 's'}
										</span>
									</div>
									{#if suggestion.rationale}
										<p
											class="text-xs text-neutral-500 dark:text-neutral-500 mt-2 italic line-clamp-2"
										>
											{suggestion.rationale}
										</p>
									{/if}
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	{/if}

	<!-- Context Tab Content -->
	{#if activeTab === 'context'}
		{#if contextError}
			<Alert variant="error" class="mb-4">{contextError}</Alert>
		{/if}

		{#if contextLoading}
			<div class="space-y-4">
				<p class="text-sm text-neutral-600 dark:text-neutral-400">
					Analyzing your business context to suggest strategic projects...
				</p>
				<div class="space-y-3">
					<ShimmerSkeleton type="list-item" />
					<ShimmerSkeleton type="list-item" />
					<ShimmerSkeleton type="list-item" />
				</div>
			</div>
		{:else if !hasMinimumContext}
			<div class="text-center py-8">
				<div class="text-4xl mb-3">💡</div>
				<p class="text-neutral-600 dark:text-neutral-400">
					Complete your business context to get strategic project suggestions.
				</p>
				{#if missingFields.length > 0}
					<p class="text-sm text-neutral-500 mt-2">
						Missing: {missingFields.slice(0, 3).map(formatFieldName).join(', ')}
						{missingFields.length > 3 ? ` and ${missingFields.length - 3} more` : ''}
					</p>
				{/if}
				<a
					href="/context"
					class="inline-block mt-4 text-sm text-brand-600 dark:text-brand-400 hover:underline"
				>
					Complete your business profile
				</a>
			</div>
		{:else if contextSuggestions.length === 0}
			<div class="text-center py-8">
				<div class="text-4xl mb-3">🎯</div>
				<p class="text-neutral-600 dark:text-neutral-400">
					No additional project suggestions at this time.
				</p>
				<p class="text-sm text-neutral-500 mt-2">
					Your existing projects may already cover your strategic priorities.
				</p>
			</div>
		{:else}
			<div class="space-y-4">
				<div class="flex items-center justify-between">
					<p class="text-sm text-neutral-600 dark:text-neutral-400">
						Found <strong>{contextSuggestions.length}</strong> strategic project idea{contextSuggestions.length ===
						1
							? ''
							: 's'} based on your business priorities.
					</p>
					<div class="flex gap-2">
						<button
							type="button"
							onclick={selectAllContext}
							class="text-xs text-brand-600 dark:text-brand-400 hover:underline"
						>
							Select All
						</button>
						<span class="text-neutral-300 dark:text-neutral-600">|</span>
						<button
							type="button"
							onclick={deselectAllContext}
							class="text-xs text-brand-600 dark:text-brand-400 hover:underline"
						>
							Clear
						</button>
					</div>
				</div>

				<div class="space-y-3 max-h-[400px] overflow-y-auto pr-1">
					{#each contextSuggestions as suggestion (suggestion.id)}
						<div
							class="border rounded-lg p-4 transition-colors {contextSelectedIds.has(suggestion.id)
								? 'border-brand-500 bg-brand-50/50 dark:bg-brand-900/10'
								: 'border-neutral-200 dark:border-neutral-700'}"
						>
							<div class="flex items-start gap-3">
								<input
									type="checkbox"
									checked={contextSelectedIds.has(suggestion.id)}
									onchange={() => toggleContextSelection(suggestion.id)}
									class="w-4 h-4 mt-1 text-brand-600 bg-white dark:bg-neutral-800 border-neutral-300 dark:border-neutral-600 rounded focus:ring-brand-500 focus:ring-2"
								/>
								<div class="flex-1 min-w-0">
									<div class="flex items-center justify-between gap-2">
										<h4 class="font-medium text-neutral-900 dark:text-neutral-100 truncate">
											{suggestion.name}
										</h4>
										<div class="flex items-center gap-2">
											<span
												class="text-xs px-2 py-0.5 rounded-full {getCategoryColor(
													suggestion.category
												)}"
											>
												{suggestion.category}
											</span>
											<span class="text-xs {getPriorityColor(suggestion.priority)}">
												{suggestion.priority}
											</span>
										</div>
									</div>
									{#if suggestion.description}
										<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1 line-clamp-2">
											{suggestion.description}
										</p>
									{/if}
									{#if suggestion.rationale}
										<p
											class="text-xs text-neutral-500 dark:text-neutral-500 mt-2 italic line-clamp-2"
										>
											{suggestion.rationale}
										</p>
									{/if}
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	{/if}

	<!-- Footer -->
	<div
		class="flex items-center justify-between pt-4 mt-4 border-t border-neutral-200 dark:border-neutral-700"
	>
		<div class="text-sm text-neutral-600 dark:text-neutral-400">
			{#if activeTab === 'actions'}
				{#if actionsSelectedCount > 0}
					{actionsSelectedCount} project{actionsSelectedCount === 1 ? '' : 's'} selected ({totalActionCount}
					action{totalActionCount === 1 ? '' : 's'})
				{:else}
					Select projects to create
				{/if}
			{:else if contextSelectedCount > 0}
				{contextSelectedCount} project{contextSelectedCount === 1 ? '' : 's'} selected
			{:else}
				Select projects to create
			{/if}
		</div>
		<div class="flex gap-3">
			<Button type="button" variant="ghost" onclick={handleClose} disabled={isCreating}>
				Cancel
			</Button>
			<Button
				type="button"
				variant="brand"
				onclick={handleCreate}
				loading={isCreating}
				disabled={(activeTab === 'actions'
					? actionsSelectedCount === 0 || actionsLoading
					: contextSelectedCount === 0 || contextLoading) || isCreating}
			>
				Create {activeTab === 'actions' && actionsSelectedCount > 0
					? actionsSelectedCount
					: activeTab === 'context' && contextSelectedCount > 0
						? contextSelectedCount
						: ''} Project{(activeTab === 'actions' ? actionsSelectedCount : contextSelectedCount) === 1
					? ''
					: 's'}
			</Button>
		</div>
	</div>
</Modal>
