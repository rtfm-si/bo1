<script lang="ts">
	/**
	 * Admin Promotions Page - List and manage promotional codes
	 */
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import { Plus, RefreshCw, Tag, Users, Trash2 } from 'lucide-svelte';
	import { adminApi, type Promotion, type UserWithPromotions } from '$lib/api/admin';
	import PromotionCard from '$lib/components/admin/PromotionCard.svelte';
	import AddPromotionModal from '$lib/components/admin/AddPromotionModal.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';

	// State
	let promotions = $state<Promotion[]>([]);
	let usersWithPromos = $state<UserWithPromotions[]>([]);
	let isLoading = $state(true);
	let isLoadingUsers = $state(false);
	let error = $state<string | null>(null);
	let filter = $state<'all' | 'active' | 'expired'>('all');
	let activeTab = $state<'codes' | 'users'>('codes');
	let showAddModal = $state(false);
	let deleteConfirm = $state<Promotion | null>(null);
	let removeConfirm = $state<{ userPromotionId: string; email: string; code: string } | null>(null);
	let isDeleting = $state(false);
	let isRemoving = $state(false);

	// Filtered promotions
	const filteredPromotions = $derived(() => {
		const now = new Date();
		return promotions.filter((p) => {
			if (filter === 'all') return true;
			if (filter === 'active') {
				if (p.deleted_at) return false;
				if (p.expires_at && new Date(p.expires_at) < now) return false;
				return true;
			}
			if (filter === 'expired') {
				if (p.deleted_at) return true;
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
				p.id === deleteConfirm!.id ? { ...p, deleted_at: new Date().toISOString() } : p
			);
			deleteConfirm = null;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to deactivate promotion';
		} finally {
			isDeleting = false;
		}
	}

	async function loadUsersWithPromos() {
		isLoadingUsers = true;
		error = null;
		try {
			usersWithPromos = await adminApi.getUsersWithPromotions();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load users with promotions';
		} finally {
			isLoadingUsers = false;
		}
	}

	function requestRemovePromo(userPromotionId: string, email: string, code: string) {
		removeConfirm = { userPromotionId, email, code };
	}

	function cancelRemove() {
		removeConfirm = null;
	}

	async function confirmRemove() {
		if (!removeConfirm) return;
		isRemoving = true;
		try {
			await adminApi.removeUserPromotion(removeConfirm.userPromotionId);
			// Refresh the users list
			await loadUsersWithPromos();
			removeConfirm = null;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to remove promotion';
		} finally {
			isRemoving = false;
		}
	}

	function switchTab(tab: 'codes' | 'users') {
		activeTab = tab;
		if (tab === 'users' && usersWithPromos.length === 0) {
			loadUsersWithPromos();
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
	<AdminPageHeader title="Promotions">
		{#snippet actions()}
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
		{/snippet}
	</AdminPageHeader>

	<!-- Main Content -->
	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-8">
		<!-- Tab Switcher -->
		<div class="mb-6 border-b border-neutral-200 dark:border-neutral-700">
			<nav class="-mb-px flex gap-4">
				<button
					class="py-2 px-1 border-b-2 font-medium text-sm transition-colors {activeTab === 'codes' ? 'border-brand-500 text-brand-600 dark:text-brand-400' : 'border-transparent text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-300'}"
					onclick={() => switchTab('codes')}
				>
					<span class="flex items-center gap-2">
						<Tag class="w-4 h-4" />
						Promo Codes
					</span>
				</button>
				<button
					class="py-2 px-1 border-b-2 font-medium text-sm transition-colors {activeTab === 'users' ? 'border-brand-500 text-brand-600 dark:text-brand-400' : 'border-transparent text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-300'}"
					onclick={() => switchTab('users')}
				>
					<span class="flex items-center gap-2">
						<Users class="w-4 h-4" />
						Users with Promos
					</span>
				</button>
			</nav>
		</div>

		<!-- Error State -->
		{#if error}
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4 mb-6">
				<p class="text-error-800 dark:text-error-200">{error}</p>
				<Button variant="secondary" size="sm" onclick={activeTab === 'codes' ? loadPromotions : loadUsersWithPromos} class="mt-2">
					{#snippet children()}Retry{/snippet}
				</Button>
			</div>
		{/if}

		{#if activeTab === 'codes'}
			<!-- Filter Tabs -->
			<div class="mb-6 flex gap-2" data-testid="filter-tabs">
				<button
					class="px-4 py-2 rounded-md text-sm font-medium transition-colors {filter === 'all' ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					onclick={() => filter = 'all'}
					data-testid="filter-all"
				>
					All ({promotions.length})
				</button>
				<button
					class="px-4 py-2 rounded-md text-sm font-medium transition-colors {filter === 'active' ? 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					onclick={() => filter = 'active'}
					data-testid="filter-active"
				>
					Active
				</button>
				<button
					class="px-4 py-2 rounded-md text-sm font-medium transition-colors {filter === 'expired' ? 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					onclick={() => filter = 'expired'}
					data-testid="filter-expired"
				>
					Expired/Inactive
				</button>
			</div>

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
				<EmptyState
					title={filter === 'all' ? 'No promotions yet' : filter === 'active' ? 'No active promotions' : 'No expired/inactive promotions'}
					description={filter === 'all' ? 'Create your first promotion code to get started.' : 'Change the filter to see other promotions.'}
					icon={Tag}
				>
					{#snippet actions()}
						{#if filter === 'all'}
							<Button variant="brand" size="md" onclick={() => showAddModal = true}>
								{#snippet children()}
									<Plus class="w-4 h-4" />
									Create Promotion
								{/snippet}
							</Button>
						{/if}
					{/snippet}
				</EmptyState>
			{:else}
				<!-- Promotions Grid -->
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
					{#each filteredPromotions() as promotion (promotion.id)}
						<PromotionCard {promotion} onDelete={requestDelete} />
					{/each}
				</div>
			{/if}
		{:else}
			<!-- Users Tab -->
			{#if isLoadingUsers}
				<div class="space-y-4">
					{#each [1, 2, 3] as _}
						<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 animate-pulse">
							<div class="h-5 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3 mb-3"></div>
							<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2"></div>
						</div>
					{/each}
				</div>
			{:else if usersWithPromos.length === 0}
				<!-- Empty State -->
				<EmptyState
					title="No users with active promotions"
					description="Users will appear here once promotions are applied to their accounts."
					icon={Users}
				/>
			{:else}
				<!-- Users with Promos Table -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					<table class="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
						<thead class="bg-neutral-50 dark:bg-neutral-900">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">User</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Promotions</th>
								<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Actions</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each usersWithPromos as user (user.user_id)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
									<td class="px-6 py-4 whitespace-nowrap">
										<div class="text-sm font-medium text-neutral-900 dark:text-white">{user.email || user.user_id}</div>
									</td>
									<td class="px-6 py-4">
										<div class="flex flex-wrap gap-2">
											{#each user.promotions as promo (promo.id)}
												<span class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
													<Tag class="w-3 h-3" />
													{promo.promotion_code}
													{#if promo.deliberations_remaining !== null}
														<span class="text-purple-500">({promo.deliberations_remaining} left)</span>
													{/if}
												</span>
											{/each}
										</div>
									</td>
									<td class="px-6 py-4 whitespace-nowrap text-right">
										<div class="flex justify-end gap-2">
											{#each user.promotions as promo (promo.id)}
												<button
													onclick={() => requestRemovePromo(promo.id, user.email || user.user_id, promo.promotion_code)}
													class="text-error-600 dark:text-error-400 hover:underline text-xs flex items-center gap-1"
													title="Remove {promo.promotion_code}"
												>
													<Trash2 class="w-3 h-3" />
													{promo.promotion_code}
												</button>
											{/each}
										</div>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
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
<Modal open={!!deleteConfirm} title="Deactivate Promotion" size="sm" onclose={cancelDelete}>
	<p class="text-sm text-neutral-600 dark:text-neutral-400">
		Are you sure you want to deactivate <strong class="font-mono">{deleteConfirm?.code}</strong>? This will prevent the code from being used, but existing usages will remain.
	</p>
	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" size="md" onclick={cancelDelete} disabled={isDeleting}>
				{#snippet children()}Cancel{/snippet}
			</Button>
			<Button variant="danger" size="md" onclick={confirmDelete} disabled={isDeleting}>
				{#snippet children()}{isDeleting ? 'Deactivating...' : 'Deactivate'}{/snippet}
			</Button>
		</div>
	{/snippet}
</Modal>

<!-- Remove User Promotion Confirmation Modal -->
<Modal open={!!removeConfirm} title="Remove Promotion from User" size="sm" onclose={cancelRemove}>
	<p class="text-sm text-neutral-600 dark:text-neutral-400">
		Are you sure you want to remove <strong class="font-mono">{removeConfirm?.code}</strong> from <strong>{removeConfirm?.email}</strong>? This action cannot be undone.
	</p>
	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" size="md" onclick={cancelRemove} disabled={isRemoving}>
				{#snippet children()}Cancel{/snippet}
			</Button>
			<Button variant="danger" size="md" onclick={confirmRemove} disabled={isRemoving}>
				{#snippet children()}{isRemoving ? 'Removing...' : 'Remove'}{/snippet}
			</Button>
		</div>
	{/snippet}
</Modal>
