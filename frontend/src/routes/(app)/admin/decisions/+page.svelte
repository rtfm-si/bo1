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
		LayoutGrid,
		Search
	} from 'lucide-svelte';
	import {
		adminApi,
		type Decision,
		type BankedTopic,
		type DecisionCategory,
		DECISION_CATEGORIES
	} from '$lib/api/admin';
	import DecisionEditorModal from '$lib/components/admin/DecisionEditorModal.svelte';
	import DecisionGenerateModal from '$lib/components/admin/DecisionGenerateModal.svelte';
	import FeaturedDecisionsModal from '$lib/components/admin/FeaturedDecisionsModal.svelte';
	import TopicBankPanel from '$lib/components/admin/TopicBankPanel.svelte';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';

	import { formatDate } from '$lib/utils/time-formatting';
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

	// Topic Bank
	let bankedTopics = $state<BankedTopic[]>([]);
	let showTopicBank = $state(false);
	let isResearching = $state(false);
	let topicBankTotal = $state(0);

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


	function getStatusColor(status: string) {
		switch (status) {
			case 'draft':
				return 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300';
			case 'published':
				return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400';
			default:
				return 'bg-neutral-100 text-neutral-600';
		}
	}

	function getCategoryColor(category: string) {
		const colors: Record<string, string> = {
			hiring: 'bg-info-100 text-info-700 dark:bg-info-900/30 dark:text-info-400',
			pricing: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
			fundraising: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400',
			marketing: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
			strategy: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
			product: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
			operations: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
			growth: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400'
		};
		return colors[category] || 'bg-neutral-100 text-neutral-600';
	}

	async function loadTopicBank() {
		try {
			const response = await adminApi.listTopicBank();
			bankedTopics = response.topics;
			topicBankTotal = response.total;
			if (response.total > 0) showTopicBank = true;
		} catch (err) {
			// Silently ignore - topic bank is optional
		}
	}

	async function researchTopics() {
		isResearching = true;
		error = null;
		try {
			const response = await adminApi.researchDecisionTopics();
			bankedTopics = response.topics;
			topicBankTotal = response.total;
			showTopicBank = true;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to research topics';
		} finally {
			isResearching = false;
		}
	}

	async function dismissTopic(id: string) {
		try {
			await adminApi.dismissTopic(id);
			bankedTopics = bankedTopics.filter((t) => t.id !== id);
			topicBankTotal--;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to dismiss topic';
		}
	}

	async function useTopicAsDraft(id: string) {
		try {
			const decision = await adminApi.useTopicAsDraft(id);
			decisions = [decision, ...decisions];
			total++;
			bankedTopics = bankedTopics.filter((t) => t.id !== id);
			topicBankTotal--;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to create draft from topic';
		}
	}

	onMount(() => {
		loadDecisions();
		loadTopicBank();
	});
</script>

<svelte:head>
	<title>Decision Library - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="Decision Library" icon={BookOpen}>
		{#snippet badge()}
			<span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">
				{total} decisions
			</span>
		{/snippet}
		{#snippet actions()}
			<Button variant="outline" size="sm" onclick={() => loadDecisions()} disabled={isLoading}>
				<RefreshCw class="w-4 h-4 mr-1.5 {isLoading ? 'animate-spin' : ''}" />
				Refresh
			</Button>
			<Button variant="outline" size="sm" onclick={() => (showFeaturedModal = true)}>
				<LayoutGrid class="w-4 h-4 mr-1.5" />
				Manage Featured
			</Button>
			<Button variant="outline" size="sm" onclick={researchTopics} disabled={isResearching}>
				<Search class="w-4 h-4 mr-1.5 {isResearching ? 'animate-pulse' : ''}" />
				{isResearching ? 'Researching...' : 'Research Topics'}
			</Button>
			<Button variant="outline" size="sm" onclick={() => (showGenerateModal = true)}>
				<Sparkles class="w-4 h-4 mr-1.5" />
				Generate
			</Button>
			<Button size="sm" onclick={() => openEditor()}>
				<Plus class="w-4 h-4 mr-1.5" />
				New Decision
			</Button>
		{/snippet}
	</AdminPageHeader>

	<!-- Filters -->
	<div class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
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

	<!-- Topic Bank Panel -->
	{#if showTopicBank && bankedTopics.length > 0}
		<div class="bg-brand-50/50 dark:bg-brand-900/10 border-b border-brand-200 dark:border-brand-800">
			<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-4">
				<div class="flex items-center justify-between mb-3">
					<h3 class="text-sm font-medium text-neutral-900 dark:text-white">
						Topic Bank
						<span class="ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">
							{topicBankTotal}
						</span>
					</h3>
					<button
						class="text-xs text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-300"
						onclick={() => (showTopicBank = false)}
					>
						Hide
					</button>
				</div>
				<TopicBankPanel topics={bankedTopics} ondismiss={dismissTopic} onuse={useTopicAsDraft} />
			</div>
		</div>
	{/if}

	<!-- Content -->
	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-6">
		{#if error}
			<div class="rounded-lg bg-error-50 dark:bg-error-900/20 p-4 mb-6">
				<p class="text-sm text-error-700 dark:text-error-400">{error}</p>
			</div>
		{/if}

		{#if isLoading}
			<div class="animate-pulse space-y-4">
				{#each Array(3) as _}
					<div class="h-28 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
				{/each}
			</div>
		{:else if filteredDecisions().length === 0}
			<EmptyState title="No decisions yet" description="Create decision pages to help founders with common strategic questions." icon={BookOpen}>
				{#snippet actions()}
					<Button variant="outline" onclick={() => (showGenerateModal = true)}>
						<Sparkles class="w-4 h-4 mr-1.5" />
						Generate with AI
					</Button>
					<Button onclick={() => openEditor()}>
						<Plus class="w-4 h-4 mr-1.5" />
						New Decision
					</Button>
				{/snippet}
			</EmptyState>
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
											? 'text-warning-500 fill-amber-500'
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
									<Trash2 class="w-4 h-4 text-error-500" />
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
<Modal open={!!deleteConfirm} title="Delete Decision?" size="sm" onclose={cancelDelete}>
	<p class="text-neutral-600 dark:text-neutral-400">
		Are you sure you want to delete "{deleteConfirm?.title}"? This cannot be undone.
	</p>
	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="outline" onclick={cancelDelete} disabled={isDeleting}>Cancel</Button>
			<Button variant="danger" onclick={confirmDelete} disabled={isDeleting}>
				{isDeleting ? 'Deleting...' : 'Delete'}
			</Button>
		</div>
	{/snippet}
</Modal>

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
