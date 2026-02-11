<script lang="ts">
	/**
	 * Admin Billing Page - Manage products, prices, and Stripe sync
	 */
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui';
	import { RefreshCw, Cloud, CloudOff, Check, AlertCircle, Package, CreditCard, Plus } from 'lucide-svelte';
	import {
		adminApi,
		type BillingProduct,
		type BillingConfigResponse,
		type SyncStatus,
		type SyncResult,
		type StripeConfigStatus
	} from '$lib/api/admin';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';

	import { formatDate } from '$lib/utils/time-formatting';
	// State
	let config = $state<BillingConfigResponse | null>(null);
	let syncStatus = $state<SyncStatus | null>(null);
	let stripeConfig = $state<StripeConfigStatus | null>(null);
	let isLoading = $state(true);
	let isSyncing = $state(false);
	let error = $state<string | null>(null);
	let syncResult = $state<SyncResult | null>(null);
	let filter = $state<'all' | 'subscriptions' | 'bundles'>('all');
	let editingProduct = $state<BillingProduct | null>(null);
	let editingPrice = $state<{ productId: string; priceId: string; amount: number } | null>(null);

	// Filtered products
	const filteredProducts = $derived(() => {
		if (!config) return [];
		return config.products.filter((p) => {
			if (filter === 'all') return true;
			if (filter === 'subscriptions') return p.type === 'subscription';
			if (filter === 'bundles') return p.type === 'one_time';
			return true;
		});
	});

	// Subscriptions and bundles counts
	const subscriptionCount = $derived(config?.products.filter((p) => p.type === 'subscription').length ?? 0);
	const bundleCount = $derived(config?.products.filter((p) => p.type === 'one_time').length ?? 0);

	async function loadData() {
		isLoading = true;
		error = null;
		try {
			const [configRes, statusRes, stripeRes] = await Promise.all([
				adminApi.getBillingProducts(),
				adminApi.getBillingSyncStatus(),
				adminApi.getStripeConfigStatus()
			]);
			config = configRes;
			syncStatus = statusRes;
			stripeConfig = stripeRes;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load billing config';
		} finally {
			isLoading = false;
		}
	}

	async function syncToStripe() {
		isSyncing = true;
		syncResult = null;
		error = null;
		try {
			syncResult = await adminApi.syncBillingToStripe();
			// Reload data after sync
			await loadData();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Sync failed';
		} finally {
			isSyncing = false;
		}
	}

	async function updatePrice(productId: string, priceId: string, amountCents: number) {
		try {
			await adminApi.updateBillingPrice(priceId, { amount_cents: amountCents });
			await loadData();
			editingPrice = null;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to update price';
		}
	}

	async function updateProduct(productId: string, updates: Record<string, unknown>) {
		try {
			await adminApi.updateBillingProduct(productId, updates);
			await loadData();
			editingProduct = null;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to update product';
		}
	}

	function formatPrice(cents: number, currency: string = 'GBP'): string {
		const amount = cents / 100;
		return new Intl.NumberFormat('en-GB', {
			style: 'currency',
			currency: currency
		}).format(amount);
	}


	onMount(() => {
		loadData();
	});
</script>

<svelte:head>
	<title>Billing Config - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="Billing Config">
		{#snippet actions()}
			<Button variant="secondary" size="sm" onclick={loadData} disabled={isLoading}>
				{#snippet children()}
					<RefreshCw class="w-4 h-4 {isLoading ? 'animate-spin' : ''}" />
					Refresh
				{/snippet}
			</Button>
			<div class="relative group">
				<Button
					variant="brand"
					size="sm"
					onclick={syncToStripe}
					disabled={isSyncing || !stripeConfig?.configured}
				>
					{#snippet children()}
						<Cloud class="w-4 h-4 {isSyncing ? 'animate-pulse' : ''}" />
						{isSyncing ? 'Syncing...' : 'Sync to Stripe'}
					{/snippet}
				</Button>
				{#if stripeConfig && !stripeConfig.configured}
					<div class="absolute right-0 top-full mt-1 w-64 p-2 bg-neutral-800 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10">
						{stripeConfig.error || 'Stripe not configured'}
					</div>
				{/if}
			</div>
		{/snippet}
	</AdminPageHeader>

	<!-- Main Content -->
	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-8">
		<!-- Stripe Config Warning Banner -->
		{#if stripeConfig && !stripeConfig.configured}
			<div class="bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg p-4 mb-6">
				<div class="flex items-start gap-3">
					<CloudOff class="w-5 h-5 text-warning-500 mt-0.5 flex-shrink-0" />
					<div>
						<p class="font-medium text-warning-800 dark:text-warning-200">Stripe not configured</p>
						<p class="text-sm text-warning-700 dark:text-warning-300 mt-1">
							{stripeConfig.error || 'STRIPE_SECRET_KEY environment variable is not set.'}
						</p>
						<p class="text-sm text-warning-600 dark:text-warning-400 mt-2">
							To enable Stripe sync, set the <code class="bg-warning-100 dark:bg-warning-900 px-1 rounded">STRIPE_SECRET_KEY</code> environment variable with a valid Stripe secret key.
						</p>
					</div>
				</div>
			</div>
		{:else if stripeConfig?.mode === 'test'}
			<div class="bg-info-50 dark:bg-info-900/20 border border-info-200 dark:border-info-800 rounded-lg p-3 mb-6">
				<div class="flex items-center gap-2">
					<div class="w-2 h-2 bg-info-500 rounded-full"></div>
					<span class="text-sm text-info-700 dark:text-info-300">Stripe is in <strong>test mode</strong></span>
				</div>
			</div>
		{:else if stripeConfig?.mode === 'live'}
			<div class="bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg p-3 mb-6">
				<div class="flex items-center gap-2">
					<div class="w-2 h-2 bg-success-500 rounded-full"></div>
					<span class="text-sm text-success-700 dark:text-success-300">Stripe is in <strong>live mode</strong></span>
				</div>
			</div>
		{/if}

		<!-- Sync Status Card -->
		{#if syncStatus}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 mb-6">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-6">
						<div class="flex items-center gap-2">
							{#if syncStatus.all_synced}
								<Check class="w-5 h-5 text-success-500" />
								<span class="text-sm font-medium text-success-600 dark:text-success-400">All synced</span>
							{:else}
								<AlertCircle class="w-5 h-5 text-warning-500" />
								<span class="text-sm font-medium text-warning-600 dark:text-warning-400">Sync needed</span>
							{/if}
						</div>
						<div class="text-sm text-neutral-600 dark:text-neutral-400">
							<span class="text-success-600 dark:text-success-400">{syncStatus.synced} synced</span>
							{#if syncStatus.out_of_sync > 0}
								<span class="mx-1">|</span>
								<span class="text-warning-600 dark:text-warning-400">{syncStatus.out_of_sync} out of sync</span>
							{/if}
							{#if syncStatus.not_synced > 0}
								<span class="mx-1">|</span>
								<span class="text-neutral-500">{syncStatus.not_synced} not synced</span>
							{/if}
						</div>
					</div>
					{#if config?.last_sync}
						<span class="text-sm text-neutral-500 dark:text-neutral-400">
							Last sync: {formatDate(config.last_sync)}
						</span>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Sync Result Alert -->
		{#if syncResult}
			<div class="mb-6 p-4 rounded-lg {syncResult.success ? 'bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800' : 'bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800'}">
				<div class="flex items-start gap-3">
					{#if syncResult.success}
						<Check class="w-5 h-5 text-success-500 mt-0.5" />
						<div>
							<p class="font-medium text-success-800 dark:text-success-200">Sync completed</p>
							<p class="text-sm text-success-700 dark:text-success-300">
								{syncResult.synced_products} products, {syncResult.synced_prices} prices synced
							</p>
						</div>
					{:else}
						<AlertCircle class="w-5 h-5 text-error-500 mt-0.5" />
						<div>
							<p class="font-medium text-error-800 dark:text-error-200">Sync failed</p>
							{#each syncResult.errors as err}
								<p class="text-sm text-error-700 dark:text-error-300">{err}</p>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Error State -->
		{#if error}
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4 mb-6">
				<p class="text-error-800 dark:text-error-200">{error}</p>
				<Button variant="secondary" size="sm" onclick={loadData} class="mt-2">
					{#snippet children()}Retry{/snippet}
				</Button>
			</div>
		{/if}

		<!-- Filter Tabs -->
		<div class="mb-6 flex gap-2">
			<button
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors {filter === 'all' ? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
				onclick={() => filter = 'all'}
			>
				All ({config?.products.length ?? 0})
			</button>
			<button
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 {filter === 'subscriptions' ? 'bg-accent-100 text-accent-700 dark:bg-accent-900/30 dark:text-accent-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
				onclick={() => filter = 'subscriptions'}
			>
				<CreditCard class="w-4 h-4" />
				Subscriptions ({subscriptionCount})
			</button>
			<button
				class="px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 {filter === 'bundles' ? 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300' : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
				onclick={() => filter = 'bundles'}
			>
				<Package class="w-4 h-4" />
				Bundles ({bundleCount})
			</button>
		</div>

		<!-- Loading State -->
		{#if isLoading}
			<div class="space-y-4">
				{#each [1, 2, 3, 4] as _}
					<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 animate-pulse">
						<div class="flex justify-between">
							<div class="space-y-2">
								<div class="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-32"></div>
								<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-48"></div>
							</div>
							<div class="h-8 bg-neutral-200 dark:bg-neutral-700 rounded w-20"></div>
						</div>
					</div>
				{/each}
			</div>
		{:else if filteredProducts().length === 0}
			<!-- Empty State -->
			<EmptyState title="No products found" description="Products will appear here once configured." icon={Package} />
		{:else}
			<!-- Products List -->
			<div class="space-y-4">
				{#each filteredProducts() as product (product.id)}
					<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
						<div class="p-6">
							<div class="flex items-start justify-between">
								<div class="flex items-start gap-4">
									<!-- Type Badge -->
									<div class="p-2 rounded-lg {product.type === 'subscription' ? 'bg-accent-100 dark:bg-accent-900/30' : 'bg-success-100 dark:bg-success-900/30'}">
										{#if product.type === 'subscription'}
											<CreditCard class="w-5 h-5 text-accent-600 dark:text-accent-400" />
										{:else}
											<Package class="w-5 h-5 text-success-600 dark:text-success-400" />
										{/if}
									</div>

									<div>
										<div class="flex items-center gap-2">
											<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">
												{product.name}
											</h3>
											{#if product.highlighted}
												<span class="px-2 py-0.5 text-xs font-medium bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300 rounded-full">
													Popular
												</span>
											{/if}
											{#if !product.active}
												<span class="px-2 py-0.5 text-xs font-medium bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400 rounded-full">
													Inactive
												</span>
											{/if}
										</div>
										<p class="text-sm text-neutral-500 dark:text-neutral-400 font-mono">
											{product.slug}
										</p>
										{#if product.description}
											<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
												{product.description}
											</p>
										{/if}
									</div>
								</div>

								<!-- Sync Status -->
								<div class="flex items-center gap-2">
									{#if product.sync_status === 'synced'}
										<Check class="w-4 h-4 text-success-500" />
									{:else if product.sync_status === 'out_of_sync'}
										<AlertCircle class="w-4 h-4 text-warning-500" />
									{:else}
										<CloudOff class="w-4 h-4 text-neutral-400" />
									{/if}
									<span class="text-sm text-neutral-500 dark:text-neutral-400 capitalize">
										{product.sync_status.replace('_', ' ')}
									</span>
								</div>
							</div>

							<!-- Limits Grid -->
							<div class="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
								<div class="p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg">
									<div class="text-xs text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Meetings</div>
									<div class="text-lg font-semibold text-neutral-900 dark:text-white">
										{product.meetings_monthly === -1 ? 'Unlimited' : product.meetings_monthly}/mo
									</div>
								</div>
								<div class="p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg">
									<div class="text-xs text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Datasets</div>
									<div class="text-lg font-semibold text-neutral-900 dark:text-white">
										{product.datasets_total === -1 ? 'Unlimited' : product.datasets_total}
									</div>
								</div>
								<div class="p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg">
									<div class="text-xs text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Mentor</div>
									<div class="text-lg font-semibold text-neutral-900 dark:text-white">
										{product.mentor_daily === -1 ? 'Unlimited' : product.mentor_daily}/day
									</div>
								</div>
								<div class="p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg">
									<div class="text-xs text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">API</div>
									<div class="text-lg font-semibold text-neutral-900 dark:text-white">
										{product.api_daily === -1 ? 'Unlimited' : product.api_daily}/day
									</div>
								</div>
							</div>

							<!-- Prices -->
							<div class="mt-4 border-t border-neutral-200 dark:border-neutral-700 pt-4">
								<h4 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Prices</h4>
								<div class="flex flex-wrap gap-2">
									{#each product.prices as price (price.id)}
										<div class="inline-flex items-center gap-2 px-3 py-2 bg-neutral-100 dark:bg-neutral-700 rounded-lg">
											{#if editingPrice?.priceId === price.id}
												<input
													type="number"
													class="w-24 px-2 py-1 text-sm border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800"
													value={editingPrice.amount}
													oninput={(e) => {
														if (editingPrice) {
															editingPrice.amount = parseInt(e.currentTarget.value) || 0;
														}
													}}
												/>
												<button
													class="text-success-600 hover:text-success-700"
													onclick={() => {
														if (editingPrice) {
															updatePrice(product.id, editingPrice.priceId, editingPrice.amount);
														}
													}}
												>
													<Check class="w-4 h-4" />
												</button>
											{:else}
												<span class="font-semibold text-neutral-900 dark:text-white">
													{formatPrice(price.amount_cents, price.currency)}
												</span>
												{#if price.interval}
													<span class="text-sm text-neutral-500 dark:text-neutral-400">/{price.interval}</span>
												{:else}
													<span class="text-sm text-neutral-500 dark:text-neutral-400">one-time</span>
												{/if}
												<button
													class="text-neutral-400 hover:text-neutral-600"
													aria-label="Edit price"
													onclick={() => {
														editingPrice = {
															productId: product.id,
															priceId: price.id,
															amount: price.amount_cents
														};
													}}
												>
													<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
													</svg>
												</button>
											{/if}
											{#if price.stripe_price_id}
												<span class="text-xs text-neutral-400 font-mono" title={price.stripe_price_id}>
													{price.stripe_price_id.slice(0, 12)}...
												</span>
											{/if}
										</div>
									{/each}
								</div>
							</div>

							<!-- Features (collapsible) -->
							{#if Object.keys(product.features).length > 0}
								<details class="mt-4 border-t border-neutral-200 dark:border-neutral-700 pt-4">
									<summary class="text-sm font-medium text-neutral-700 dark:text-neutral-300 cursor-pointer">
										Features ({Object.entries(product.features).filter(([_, v]) => v).length} enabled)
									</summary>
									<div class="mt-2 flex flex-wrap gap-2">
										{#each Object.entries(product.features) as [feature, enabled]}
											<span class="px-2 py-1 text-xs rounded {enabled ? 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300' : 'bg-neutral-100 text-neutral-500 dark:bg-neutral-700 dark:text-neutral-400'}">
												{feature}
											</span>
										{/each}
									</div>
								</details>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</main>
</div>
