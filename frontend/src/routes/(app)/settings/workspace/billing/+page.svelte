<script lang="ts">
	/**
	 * Workspace Billing Settings - Manage workspace subscription and billing
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { env } from '$env/dynamic/public';
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import type { WorkspaceBillingInfoResponse, CheckoutResponse } from '$lib/api/client';
	import { PRICING_TIERS } from '$lib/data/pricing';
	import { currentWorkspace } from '$lib/stores/workspace';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';

	// Get Stripe price IDs from environment
	const STRIPE_PRICE_STARTER = env.PUBLIC_STRIPE_PRICE_STARTER || '';
	const STRIPE_PRICE_PRO = env.PUBLIC_STRIPE_PRICE_PRO || '';

	// State
	let billing = $state<WorkspaceBillingInfoResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let successMessage = $state<string | null>(null);
	let isUpgrading = $state(false);
	let portalLoading = $state(false);

	// Check for success/cancelled from Stripe redirect
	$effect(() => {
		const url = $page.url;
		if (url.searchParams.get('success') === 'true') {
			successMessage = 'Subscription updated successfully! Changes may take a moment to reflect.';
			// Remove query params
			goto('/settings/workspace/billing', { replaceState: true });
		}
		if (url.searchParams.get('cancelled') === 'true') {
			error = 'Checkout cancelled';
			goto('/settings/workspace/billing', { replaceState: true });
		}
	});

	// Format tier name
	function formatTierName(tier: string): string {
		return tier.charAt(0).toUpperCase() + tier.slice(1);
	}

	// Get tier info from pricing data
	function getTierInfo(tierId: string) {
		return PRICING_TIERS.find((t) => t.id === tierId);
	}

	// Get available upgrade tiers (tiers higher than current)
	function getUpgradeTiers() {
		const tierOrder = ['free', 'starter', 'pro'];
		const currentIndex = tierOrder.indexOf(billing?.tier || 'free');
		return PRICING_TIERS.filter((t) => tierOrder.indexOf(t.id) > currentIndex);
	}

	// Get price ID for a tier
	function getPriceId(tierId: string): string | null {
		switch (tierId) {
			case 'starter':
				return STRIPE_PRICE_STARTER || null;
			case 'pro':
				return STRIPE_PRICE_PRO || null;
			default:
				return null;
		}
	}

	onMount(async () => {
		if (!$currentWorkspace) {
			goto('/settings/workspace');
			return;
		}

		await loadBilling();
	});

	async function loadBilling() {
		if (!$currentWorkspace) return;

		isLoading = true;
		error = null;

		try {
			billing = await apiClient.getWorkspaceBilling($currentWorkspace.id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load billing information';
			console.error('Failed to load workspace billing:', e);
		} finally {
			isLoading = false;
		}
	}

	async function openBillingPortal() {
		if (!$currentWorkspace) return;

		portalLoading = true;
		try {
			const result = await apiClient.createWorkspacePortalSession($currentWorkspace.id);
			window.location.href = result.url;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to open billing portal';
		} finally {
			portalLoading = false;
		}
	}

	async function startCheckout(priceId: string) {
		if (isUpgrading || !$currentWorkspace) return;

		isUpgrading = true;
		error = null;

		try {
			const result = await apiClient.createWorkspaceCheckout($currentWorkspace.id, priceId);
			window.location.href = result.url;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to start checkout';
			isUpgrading = false;
		}
	}

	const tierInfo = $derived(billing ? getTierInfo(billing.tier) : null);
	const upgradeTiers = $derived(getUpgradeTiers());
</script>

<svelte:head>
	<title>Workspace Billing - Board of One</title>
</svelte:head>

{#if !$currentWorkspace}
	<div class="text-center py-12">
		<p class="text-slate-500 dark:text-slate-400">No workspace selected</p>
		<Button variant="secondary" onclick={() => goto('/settings/workspace')} class="mt-4">
			Go to Workspace Settings
		</Button>
	</div>
{:else if isLoading}
	<div class="flex items-center justify-center py-12">
		<div
			class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"
		></div>
	</div>
{:else}
	<div class="space-y-6">
		{#if successMessage}
			<Alert variant="success" dismissable ondismiss={() => (successMessage = null)}>
				{successMessage}
			</Alert>
		{/if}

		{#if error}
			<Alert variant="error" dismissable ondismiss={() => (error = null)}>
				{error}
			</Alert>
		{/if}

		<!-- Page Header -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
		>
			<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-2">Workspace Billing</h2>
			<p class="text-slate-600 dark:text-slate-400">
				Manage billing for <span class="font-medium">{billing?.workspace_name}</span>
			</p>
		</div>

		<!-- Current Plan -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
		>
			<div class="flex items-start justify-between mb-6">
				<div>
					<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-1">Current Plan</h3>
					<p class="text-slate-600 dark:text-slate-400">
						Your workspace's subscription plan and limits
					</p>
				</div>
			</div>

			<div
				class="flex items-center justify-between p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-800"
			>
				<div>
					<p class="text-2xl font-bold text-brand-700 dark:text-brand-400">
						{formatTierName(billing?.tier || 'free')}
					</p>
					<p class="text-brand-600 dark:text-brand-500">
						{#if tierInfo}
							{tierInfo.priceLabel}/{tierInfo.period}
						{:else}
							$0/month
						{/if}
					</p>
				</div>
				{#if billing?.has_billing_account && billing?.can_manage_billing}
					<Button variant="secondary" onclick={openBillingPortal} loading={portalLoading}>
						Manage Subscription
					</Button>
				{/if}
			</div>

			{#if tierInfo?.limits}
				<div class="mt-4">
					<p class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Plan limits:</p>
					<ul class="space-y-1">
						<li class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
							<svg
								class="w-4 h-4 text-green-500"
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
							{tierInfo.limits.meetings_monthly === -1
								? 'Unlimited meetings'
								: `${tierInfo.limits.meetings_monthly} meetings/month`}
						</li>
						{#if tierInfo.features.api_access}
							<li class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
								<svg
									class="w-4 h-4 text-green-500"
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
								API access
							</li>
						{/if}
					</ul>
				</div>
			{/if}

			{#if !billing?.can_manage_billing}
				<div class="mt-4 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
					<p class="text-sm text-slate-600 dark:text-slate-400">
						Contact your workspace admin to manage billing.
					</p>
				</div>
			{/if}
		</div>

		<!-- Upgrade Options (only show for non-pro and admins) -->
		{#if billing?.can_manage_billing && billing?.tier !== 'pro' && upgradeTiers.length > 0}
			<div
				class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
			>
				<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
					Upgrade Your Workspace
				</h3>
				<p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
					Unlock more features for your team with a workspace subscription.
				</p>

				<div class="grid gap-4 {upgradeTiers.length === 1 ? '' : 'md:grid-cols-2'}">
					{#each upgradeTiers as tier}
						{@const priceId = getPriceId(tier.id)}
						<div
							class="p-4 rounded-lg border {tier.highlight
								? 'border-brand-500 bg-brand-50/50 dark:bg-brand-900/10'
								: 'border-slate-200 dark:border-slate-700'}"
						>
							<div class="flex items-start justify-between mb-3">
								<div>
									<h4 class="font-semibold text-slate-900 dark:text-white">
										{tier.name}
										{#if tier.highlight}
											<span
												class="ml-2 text-xs bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-400 px-2 py-0.5 rounded-full"
											>
												Popular
											</span>
										{/if}
									</h4>
									<p class="text-sm text-slate-600 dark:text-slate-400">{tier.description}</p>
								</div>
								<div class="text-right">
									<span class="text-xl font-bold text-slate-900 dark:text-white"
										>{tier.priceLabel}</span
									>
									<span class="text-sm text-slate-500 dark:text-slate-400">/{tier.period}</span>
								</div>
							</div>

							<ul class="space-y-1 mb-4">
								<li class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
									<svg
										class="w-4 h-4 text-green-500 flex-shrink-0"
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
									{tier.limits.meetings_monthly === -1
										? 'Unlimited meetings'
										: `${tier.limits.meetings_monthly} meetings/month`}
								</li>
								{#if tier.features.api_access}
									<li class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
										<svg
											class="w-4 h-4 text-green-500 flex-shrink-0"
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
										API access
									</li>
								{/if}
								{#if tier.features.priority_support}
									<li class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
										<svg
											class="w-4 h-4 text-green-500 flex-shrink-0"
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
										Priority support
									</li>
								{/if}
							</ul>

							{#if priceId}
								<Button
									variant={tier.highlight ? 'brand' : 'secondary'}
									onclick={() => startCheckout(priceId)}
									disabled={isUpgrading}
									class="w-full"
								>
									{isUpgrading ? 'Processing...' : `Upgrade to ${tier.name}`}
								</Button>
							{:else}
								<Button
									variant="secondary"
									onclick={() => (window.location.href = 'mailto:support@boardof.one?subject=Upgrade%20Inquiry')}
									class="w-full"
								>
									Contact Sales
								</Button>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Billing Portal Access -->
		{#if billing?.has_billing_account && billing?.can_manage_billing}
			<div
				class="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-6"
			>
				<div class="flex items-center gap-4">
					<div
						class="w-10 h-10 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center"
					>
						<svg
							class="w-5 h-5 text-slate-600 dark:text-slate-400"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
							/>
						</svg>
					</div>
					<div class="flex-1">
						<h3 class="font-medium text-slate-700 dark:text-slate-300">
							Payment Methods & Invoices
						</h3>
						<p class="text-sm text-slate-500 dark:text-slate-400">
							Manage payment methods, view invoices, and update billing details
						</p>
					</div>
					<Button variant="secondary" onclick={openBillingPortal} loading={portalLoading}>
						Open Portal
					</Button>
				</div>
			</div>
		{/if}

		<!-- Help Note -->
		<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
			<div class="flex gap-3">
				<svg
					class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<div class="text-sm text-blue-900 dark:text-blue-200">
					<p class="font-semibold mb-1">Workspace billing info</p>
					<p class="text-blue-800 dark:text-blue-300">
						All workspace members benefit from the workspace subscription tier. For billing
						questions, contact us at
						<a href="mailto:support@boardof.one" class="underline hover:no-underline"
							>support@boardof.one</a
						>.
					</p>
				</div>
			</div>
		</div>
	</div>
{/if}
