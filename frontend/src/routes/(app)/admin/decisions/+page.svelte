<script lang="ts">
	/**
	 * Admin Decisions Page - List and manage published decisions
	 */
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui';
	import {
		Plus,
		RefreshCw,
		BookOpen,
		Sparkles,
		Eye,
		EyeOff,
		Trash2,
		Edit,
		ExternalLink,
		Star,
		LayoutGrid
	} from 'lucide-svelte';
	import {
		adminApi,
		type Decision,
		type DecisionCategory,
		DECISION_CATEGORIES
	} from '$lib/api/admin';
	import DecisionEditorModal from '$lib/components/admin/DecisionEditorModal.svelte';
	import DecisionGenerateModal from '$lib/components/admin/DecisionGenerateModal.svelte';
	import FeaturedDecisionsModal from '$lib/components/admin/FeaturedDecisionsModal.svelte';

	// State
	let decisions = $state<Decision[]>([]);
	let total = $state(0);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let filter = $state<'all' | 'draft' | 'published'>('all');
	let categoryFilter = $state<DecisionCategory | 'all'>('all');

	// Modals
	let showEditorModal = $state(false);
	let showGenerateModal = $state(false);
	let showFeaturedModal = $state(false);
	let editingDecision = $state<Decision | null>(null);
	let deleteConfirm = $state<Decision | null>(null);
	let isDeleting = $state(false);
	let togglingFeatured = $state<string | null>(null);

	const filteredDecisions = $derived(() => {
		let result = decisions;
		if (filter !== 'all') {
			result = result.filter((d) => d.status === filter);
		}
		if (categoryFilter !== 'all') {
			result = result.filter((d) => d.category === categoryFilter);
		}
		return result;
	});

	async function loadDecisions() {
		isLoading = true;
		error = null;
		try {
			const statusParam = filter === 'all' ? undefined : filter;
			const categoryParam = categoryFilter === 'all' ? undefined : categoryFilter;
			const response = await adminApi.listDecisions({
				status: statusParam,
				category: categoryParam
			});
			decisions = response.decisions;
			total = response.total;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load decisions';
		} finally {
			isLoading = false;
		}
	}

	async function openEditor(decision?: Decision) {
		if (decision) {
			try {
				editingDecision = await adminApi.getDecision(decision.id);
			} catch (err) {
				error = err instanceof Error ? err.message : 'Failed to load decision';
				return;
			}
		} else {
			editingDecision = null;
		}
		showEditorModal = true;
	}

	function handleDecisionSaved(decision: Decision) {
		if (editingDecision) {
			decisions = decisions.map((d) => (d.id === decision.id ? decision : d));
		} else {
			decisions = [decision, ...decisions];
			total++;
		}
		showEditorModal = false;
		editingDecision = null;
	}

	function handleGenerated(decision: Decision) {
		decisions = [decision, ...decisions];
		total++;
		showGenerateModal = false;
	}

	function requestDelete(decision: Decision) {
		deleteConfirm = decision;
	}

	function cancelDelete() {
		deleteConfirm = null;
	}

	async function confirmDelete() {
		if (!deleteConfirm) return;
		isDeleting = true;
		try {
			await adminApi.deleteDecision(deleteConfirm.id);
			decisions = decisions.filter((d) => d.id !== deleteConfirm!.id);
			total--;
			deleteConfirm = null;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to delete decision';
		} finally {
			isDeleting = false;
		}
	}

	async function togglePublish(decision: Decision) {
		try {
			let updated: Decision;
			if (decision.status === 'published') {
				updated = await adminApi.unpublishDecision(decision.id);
			} else {
				updated = await adminApi.publishDecision(decision.id);
			}
			decisions = decisions.map((d) => (d.id === updated.id ? updated : d));
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to update decision status';
		}
	}

	async function toggleFeatured(decision: Decision) {
		togglingFeatured = decision.id;
		try {
			let updated: Decision;
			if (decision.homepage_featured) {
				updated = await adminApi.unfeatureDecision(decision.id);
			} else {
				updated = await adminApi.featureDecision(decision.id);
			}
			decisions = decisions.map((d) => (d.id === updated.id ? updated : d));
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to update featured status';
		} finally {
			togglingFeatured = null;
		}
	}

	function formatDate(date: string | undefined) {
		if (!date) return '-';
		return new Date(date).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	function getStatusColor(status: string) {
		switch (status) {
			case 'draft':
				return 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300';
			case 'published':
				return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
			default:
				return 'bg-neutral-100 text-neutral-600';
		}
	}

	function getCategoryColor(category: string) {
		const colors: Record<string, string> = {
			hiring: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
			pricing: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
			fundraising: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
			marketing: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
			strategy: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
			product: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
			operations: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
			growth: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
		};
		return colors[category] || 'bg-neutral-100 text-neutral-600';
	}

	onMount(() => {
		loadDecisions();
	});
</script>

<svelte:head>
	<title>Decision Library - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/admin"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
						aria-label="Back to admin dashboard"
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
					<div class="flex items-center gap-2">
						<BookOpen class="w-6 h-6 text-brand-600 dark:text-brand-400" />
						<h1 class="text-xl font-semibold text-neutral-900 dark:text-white">Decision Library</h1>
					</div>
					<span
						class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400"
					>
						{total} decisions
					</span>
				</div>
				<div class="flex items-center gap-2">
					<Button variant="outline" size="sm" onclick={() => loadDecisions()} disabled={isLoading}>
						<RefreshCw class="w-4 h-4 mr-1.5 {isLoading ? 'animate-spin' : ''}" />
						Refresh
					</Button>
					<Button variant="outline" size="sm" onclick={() => (showFeaturedModal = true)}>
						<LayoutGrid class="w-4 h-4 mr-1.5" />
						Manage Featured
					</Button>
					<Button variant="outline" size="sm" onclick={() => (showGenerateModal = true)}>
						<Sparkles class="w-4 h-4 mr-1.5" />
						Generate
					</Button>
					<Button size="sm" onclick={() => openEditor()}>
						<Plus class="w-4 h-4 mr-1.5" />
						New Decision
					</Button>
				</div>
			</div>
		</div>
	</header>

	<!-- Filters -->
	<div class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="flex items-center justify-between py-3">
				<!-- Status tabs -->
				<nav class="flex gap-6" aria-label="Status filter">
					{#each ['all', 'draft', 'published'] as tab}
						<button
							class="px-1 py-2 text-sm font-medium border-b-2 transition-colors {filter === tab
								? 'border-brand-500 text-brand-600 dark:text-brand-400'
								: 'border-transparent text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-300'}"
							onclick={() => {
								filter = tab as typeof filter;
								loadDecisions();
							}}
						>
							{tab.charAt(0).toUpperCase() + tab.slice(1)}
						</button>
					{/each}
				</nav>

				<!-- Category filter -->
				<select
					class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
					bind:value={categoryFilter}
					onchange={() => loadDecisions()}
				>
					<option value="all">All Categories</option>
					{#each DECISION_CATEGORIES as cat}
						<option value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>

	<!-- Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
		{#if error}
			<div class="rounded-lg bg-red-50 dark:bg-red-900/20 p-4 mb-6">
				<p class="text-sm text-red-700 dark:text-red-400">{error}</p>
			</div>
		{/if}

		{#if isLoading}
			<div class="animate-pulse space-y-4">
				{#each Array(3) as _}
					<div class="h-28 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
				{/each}
			</div>
		{:else if filteredDecisions().length === 0}
			<div class="text-center py-12">
				<BookOpen class="w-12 h-12 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" />
				<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-2">
					No decisions yet
				</h3>
				<p class="text-neutral-500 dark:text-neutral-400 mb-4">
					Create decision pages to help founders with common strategic questions.
				</p>
				<div class="flex justify-center gap-3">
					<Button variant="outline" onclick={() => (showGenerateModal = true)}>
						<Sparkles class="w-4 h-4 mr-1.5" />
						Generate with AI
					</Button>
					<Button onclick={() => openEditor()}>
						<Plus class="w-4 h-4 mr-1.5" />
						New Decision
					</Button>
				</div>
			</div>
		{:else}
			<div class="space-y-4">
				{#each filteredDecisions() as decision (decision.id)}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 hover:shadow-sm transition-shadow"
					>
						<div class="flex items-start justify-between gap-4">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 mb-1 flex-wrap">
									<span
										class="px-2 py-0.5 rounded text-xs font-medium {getStatusColor(
											decision.status
										)}"
									>
										{decision.status}
									</span>
									<span
										class="px-2 py-0.5 rounded text-xs font-medium {getCategoryColor(
											decision.category
										)}"
									>
										{decision.category}
									</span>
								</div>
								<h3
									class="text-lg font-medium text-neutral-900 dark:text-white"
									title={decision.title}
								>
									{decision.title}
								</h3>
								{#if decision.meta_description}
									<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-2">
										{decision.meta_description}
									</p>
								{/if}
								<div
									class="flex items-center gap-4 mt-2 text-xs text-neutral-500 dark:text-neutral-400"
								>
									<span>/{decision.category}/{decision.slug}</span>
									{#if decision.status === 'published' && decision.published_at}
										<span>Published: {formatDate(decision.published_at)}</span>
									{:else}
										<span>Updated: {formatDate(decision.updated_at)}</span>
									{/if}
									<span>{decision.view_count} views</span>
									<span>{decision.click_through_count} clicks</span>
								</div>
							</div>
							<div class="flex items-center gap-2">
								{#if decision.status === 'published'}
									<a
										href="/decisions/{decision.category}/{decision.slug}"
										target="_blank"
										rel="noopener noreferrer"
										class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
										title="View live page"
									>
										<ExternalLink class="w-4 h-4 text-neutral-500" />
									</a>
								{/if}
								<button
									class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors disabled:opacity-50"
									onclick={() => toggleFeatured(decision)}
									disabled={togglingFeatured === decision.id || decision.status !== 'published'}
									title={decision.homepage_featured ? 'Remove from homepage' : 'Feature on homepage'}
								>
									<Star
										class="w-4 h-4 {decision.homepage_featured
											? 'text-amber-500 fill-amber-500'
											: 'text-neutral-400'}"
									/>
								</button>
								<Button
									variant="outline"
									size="sm"
									onclick={() => togglePublish(decision)}
									title={decision.status === 'published' ? 'Unpublish' : 'Publish'}
								>
									{#if decision.status === 'published'}
										<EyeOff class="w-4 h-4" />
									{:else}
										<Eye class="w-4 h-4" />
									{/if}
								</Button>
								<Button variant="ghost" size="sm" onclick={() => openEditor(decision)}>
									<Edit class="w-4 h-4" />
								</Button>
								<Button variant="ghost" size="sm" onclick={() => requestDelete(decision)}>
									<Trash2 class="w-4 h-4 text-red-500" />
								</Button>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</main>
</div>

<!-- Delete confirmation -->
{#if deleteConfirm}
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 max-w-md mx-4">
			<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">Delete Decision?</h3>
			<p class="text-neutral-600 dark:text-neutral-400 mb-4">
				Are you sure you want to delete "{deleteConfirm.title}"? This cannot be undone.
			</p>
			<div class="flex justify-end gap-3">
				<Button variant="outline" onclick={cancelDelete} disabled={isDeleting}>Cancel</Button>
				<Button variant="danger" onclick={confirmDelete} disabled={isDeleting}>
					{isDeleting ? 'Deleting...' : 'Delete'}
				</Button>
			</div>
		</div>
	</div>
{/if}

<!-- Editor Modal -->
{#if showEditorModal}
	<DecisionEditorModal
		decision={editingDecision}
		onclose={() => {
			showEditorModal = false;
			editingDecision = null;
		}}
		onsave={handleDecisionSaved}
	/>
{/if}

<!-- Generate Modal -->
{#if showGenerateModal}
	<DecisionGenerateModal onclose={() => (showGenerateModal = false)} ongenerated={handleGenerated} />
{/if}

<!-- Featured Management Modal -->
{#if showFeaturedModal}
	<FeaturedDecisionsModal
		onclose={() => (showFeaturedModal = false)}
		onsave={() => {
			showFeaturedModal = false;
			loadDecisions();
		}}
	/>
{/if}
