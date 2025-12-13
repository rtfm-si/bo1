<script lang="ts">
	/**
	 * Admin Promotions Page - List and manage promotional codes
	 */
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui';
	import { Plus, RefreshCw, Tag } from 'lucide-svelte';
	import { adminApi, type Promotion } from '$lib/api/admin';
	import PromotionCard from '$lib/components/admin/PromotionCard.svelte';
	import AddPromotionModal from '$lib/components/admin/AddPromotionModal.svelte';

	// State
	let promotions = $state<Promotion[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let filter = $state<'all' | 'active' | 'expired'>('all');
	let showAddModal = $state(false);
	let deleteConfirm = $state<Promotion | null>(null);
	let isDeleting = $state(false);

	// Filtered promotions
	const filteredPromotions = $derived(() => {
		const now = new Date();
		return promotions.filter((p) => {
			if (filter === 'all') return true;
			if (filter === 'active') {
				if (!p.is_active) return false;
				if (p.expires_at && new Date(p.expires_at) < now) return false;
				return true;
			}
			if (filter === 'expired') {
				if (!p.is_active) return true;
				if (p.expires_at && new Date(p.expires_at) < now) return true;
				return false;
			}
			return true;
		});
	});

	async function loadPromotions() {
		isLoading = true;
		error = null;
		try {
			promotions = await adminApi.listPromotions();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load promotions';
		} finally {
			isLoading = false;
		}
	}

	function handleCreated(promotion: Promotion) {
		promotions = [promotion, ...promotions];
	}

	function requestDelete(promotion: Promotion) {
		deleteConfirm = promotion;
	}

	function cancelDelete() {
		deleteConfirm = null;
	}

	async function confirmDelete() {
		if (!deleteConfirm) return;
		isDeleting = true;
		try {
			await adminApi.deletePromotion(deleteConfirm.id);
			promotions = promotions.map((p) =>
				p.id === deleteConfirm!.id ? { ...p, is_active: false } : p
			);
			deleteConfirm = null;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to deactivate promotion';
		} finally {
			isDeleting = false;
		}
	}

	onMount(() => {
		loadPromotions();
	});
</script>

<svelte:head>
	<title>Promotions - Admin - Board of One</title>
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
						<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</a>
					<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
						Promotions
					</h1>
				</div>
				<div class="flex items-center gap-2">
					<Button variant="secondary" size="sm" onclick={loadPromotions} disabled={isLoading}>
						{#snippet children()}
							<RefreshCw class="w-4 h-4 {isLoading ? 'animate-spin' : ''}" />
							Refresh
						{/snippet}
					</Button>
					<Button variant="brand" size="sm" onclick={() => showAddModal = true}>
						{#snippet children()}
							<Plus class="w-4 h-4" />
							Add Promotion
						{/snippet}
					</Button>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Filter Tabs -->
		<div class="mb-6 flex gap-2">
			<button
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors {filter === 'all' ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
				onclick={() => filter = 'all'}
			>
				All ({promotions.length})
			</button>
			<button
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors {filter === 'active' ? 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
				onclick={() => filter = 'active'}
			>
				Active
			</button>
			<button
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors {filter === 'expired' ? 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
				onclick={() => filter = 'expired'}
			>
				Expired/Inactive
			</button>
		</div>

		<!-- Error State -->
		{#if error}
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4 mb-6">
				<p class="text-error-800 dark:text-error-200">{error}</p>
				<Button variant="secondary" size="sm" onclick={loadPromotions} class="mt-2">
					{#snippet children()}Retry{/snippet}
				</Button>
			</div>
		{/if}

		<!-- Loading State -->
		{#if isLoading}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{#each [1, 2, 3] as _}
					<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 animate-pulse">
						<div class="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2 mb-3"></div>
						<div class="grid grid-cols-2 gap-3 mb-4">
							<div class="h-8 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
							<div class="h-8 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
							<div class="h-8 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
							<div class="h-8 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
						</div>
					</div>
				{/each}
			</div>
		{:else if filteredPromotions().length === 0}
			<!-- Empty State -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-12 text-center">
				<div class="mx-auto w-12 h-12 bg-neutral-100 dark:bg-neutral-700 rounded-full flex items-center justify-center mb-4">
					<Tag class="w-6 h-6 text-neutral-400" />
				</div>
				<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-2">
					{#if filter === 'all'}
						No promotions yet
					{:else if filter === 'active'}
						No active promotions
					{:else}
						No expired/inactive promotions
					{/if}
				</h3>
				<p class="text-neutral-600 dark:text-neutral-400 mb-4">
					{#if filter === 'all'}
						Create your first promotion code to get started.
					{:else}
						Change the filter to see other promotions.
					{/if}
				</p>
				{#if filter === 'all'}
					<Button variant="brand" size="md" onclick={() => showAddModal = true}>
						{#snippet children()}
							<Plus class="w-4 h-4" />
							Create Promotion
						{/snippet}
					</Button>
				{/if}
			</div>
		{:else}
			<!-- Promotions Grid -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{#each filteredPromotions() as promotion (promotion.id)}
					<PromotionCard {promotion} onDelete={requestDelete} />
				{/each}
			</div>
		{/if}
	</main>
</div>

<!-- Add Promotion Modal -->
<AddPromotionModal
	open={showAddModal}
	onClose={() => showAddModal = false}
	onCreated={handleCreated}
/>

<!-- Delete Confirmation Modal -->
{#if deleteConfirm}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onclick={cancelDelete} role="presentation">
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6" onclick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" tabindex="-1">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Deactivate Promotion</h2>
			<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
				Are you sure you want to deactivate <strong class="font-mono">{deleteConfirm.code}</strong>? This will prevent the code from being used, but existing usages will remain.
			</p>
			<div class="flex justify-end gap-3">
				<Button variant="secondary" size="md" onclick={cancelDelete} disabled={isDeleting}>
					{#snippet children()}Cancel{/snippet}
				</Button>
				<Button variant="danger" size="md" onclick={confirmDelete} disabled={isDeleting}>
					{#snippet children()}{isDeleting ? 'Deactivating...' : 'Deactivate'}{/snippet}
				</Button>
			</div>
		</div>
	</div>
{/if}
