<script lang="ts">
	/**
	 * Billing Settings - Plan and usage management
	 * Uses actual data from billing API with Stripe checkout integration
	 */
	import { onMount } from 'svelte';
	import { env } from '$env/dynamic/public';
	import { apiClient } from '$lib/api/client';
	import type { PlanDetails, UsageStats } from '$lib/api/client';
	import { PRICING_TIERS, MEETING_BUNDLES } from '$lib/data/pricing';
	import type { MeetingCreditsResponse } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { Package } from 'lucide-svelte';

	// Get Stripe price IDs from environment
	const STRIPE_PRICE_STARTER = env.PUBLIC_STRIPE_PRICE_STARTER || '';
	const STRIPE_PRICE_PRO = env.PUBLIC_STRIPE_PRICE_PRO || '';

	// Check if Stripe pricing is configured
	const isStripeConfigured = Boolean(STRIPE_PRICE_STARTER && STRIPE_PRICE_PRO);

	// State
	let plan = $state<PlanDetails | null>(null);
	let usage = $state<UsageStats | null>(null);
	let credits = $state<MeetingCreditsResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let portalMessage = $state<string | null>(null);
	let isUpgrading = $state(false);
	let purchasingBundle = $state<number | null>(null);

	// Format price in dollars
	function formatPrice(cents: number): string {
		if (cents === 0) return '$0';
		return `$${(cents / 100).toFixed(0)}`;
	}

	// Calculate usage percentage
	function getUsagePercent(used: number, limit: number | null): number {
		if (!limit) return 0; // Unlimited
		return Math.min((used / limit) * 100, 100);
	}

	// Get available upgrade tiers (tiers higher than current)
	function getUpgradeTiers() {
		const tierOrder = ['free', 'starter', 'pro'];
		const currentIndex = tierOrder.indexOf(plan?.tier || 'free');
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
		try {
			const [planResult, usageResult, creditsResult] = await Promise.all([
				apiClient.getBillingPlan(),
				apiClient.getBillingUsage(),
				apiClient.getMeetingCredits()
			]);
			plan = planResult;
			usage = usageResult;
			credits = creditsResult;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load billing information';
			console.error('Failed to load billing:', e);
		} finally {
			isLoading = false;
		}
	});

	async function purchaseBundle(bundleSize: number) {
		if (purchasingBundle !== null) return;

		purchasingBundle = bundleSize;
		error = null;

		try {
			const result = await apiClient.purchaseMeetingBundle(bundleSize);
			window.location.href = result.url;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to start checkout';
			purchasingBundle = null;
		}
	}

	async function openBillingPortal() {
		try {
			const result = await apiClient.createBillingPortalSession();
			if (result.available && result.url) {
				window.location.href = result.url;
			} else {
				portalMessage = result.message;
				setTimeout(() => {
					portalMessage = null;
				}, 5000);
			}
		} catch (e) {
			portalMessage = e instanceof Error ? e.message : 'Failed to open billing portal';
		}
	}

	async function startCheckout(priceId: string) {
		if (isUpgrading) return;

		isUpgrading = true;
		error = null;

		try {
			const result = await apiClient.createCheckoutSession(priceId);
			// Redirect to Stripe Checkout
			window.location.href = result.url;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to start checkout';
			isUpgrading = false;
		}
	}
</script>

<svelte:head>
	<title>Billing - Board of One</title>
</svelte:head>

{#if isLoading}
	<div class="flex items-center justify-center py-12">
		<div class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"></div>
	</div>
{:else}
	<div class="space-y-6">
		{#if error}
			<Alert variant="error">{error}</Alert>
		{/if}

		{#if portalMessage}
			<Alert variant="info">{portalMessage}</Alert>
		{/if}

		<!-- Current Plan -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="flex items-start justify-between mb-6">
				<div>
					<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-1">
						Current Plan
					</h2>
					<p class="text-slate-600 dark:text-slate-400">
						Manage your subscription and billing
					</p>
				</div>
			</div>

			<div class="flex items-center justify-between p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-800">
				<div>
					<p class="text-2xl font-bold text-brand-700 dark:text-brand-400">
						{plan?.name || 'Free'}
					</p>
					<p class="text-brand-600 dark:text-brand-500">
						{plan ? (plan.price_monthly > 0 ? `${formatPrice(plan.price_monthly)}/month` : 'Free') : '$0/month'}
					</p>
				</div>
				{#if plan?.tier !== 'free'}
					<Button variant="secondary" onclick={openBillingPortal}>
						Manage Subscription
					</Button>
				{/if}
			</div>

			{#if plan?.features && plan.features.length > 0}
				<div class="mt-4">
					<p class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Included features:</p>
					<ul class="space-y-1">
						{#each plan.features as feature}
							<li class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
								<svg class="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
								</svg>
								{feature}
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		</div>

		<!-- Upgrade Options -->
		{#if plan?.tier !== 'pro'}
			{#if isStripeConfigured && getUpgradeTiers().length > 0}
				<!-- Show upgrade cards when Stripe is configured -->
				<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
					<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
						Upgrade Your Plan
					</h3>

					<div class="grid gap-4 {getUpgradeTiers().length === 1 ? '' : 'md:grid-cols-2'}">
						{#each getUpgradeTiers() as tier}
							{@const priceId = getPriceId(tier.id)}
							<div class="p-4 rounded-lg border {tier.highlight ? 'border-brand-500 bg-brand-50/50 dark:bg-brand-900/10' : 'border-slate-200 dark:border-slate-700'}">
								<div class="flex items-start justify-between mb-3">
									<div>
										<h4 class="font-semibold text-slate-900 dark:text-white">
											{tier.name}
											{#if tier.highlight}
												<span class="ml-2 text-xs bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-400 px-2 py-0.5 rounded-full">
													Popular
												</span>
											{/if}
										</h4>
										<p class="text-sm text-slate-600 dark:text-slate-400">{tier.description}</p>
									</div>
									<div class="text-right">
										<span class="text-xl font-bold text-slate-900 dark:text-white">{tier.priceLabel}</span>
										{#if tier.period}
											<span class="text-sm text-slate-500 dark:text-slate-400">/{tier.period}</span>
										{/if}
									</div>
								</div>

								<ul class="space-y-1 mb-4">
									<li class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
										<svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
										</svg>
										{tier.limits.meetings_monthly === -1 ? 'Unlimited meetings' : `${tier.limits.meetings_monthly} meetings/month`}
									</li>
									{#if tier.features.api_access}
										<li class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
											<svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
											</svg>
											API access
										</li>
									{/if}
									{#if tier.features.priority_support}
										<li class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
											<svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
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
									<Button variant="secondary" onclick={() => window.location.href = 'mailto:support@boardof.one?subject=Upgrade%20Inquiry'} class="w-full">
										Contact Sales
									</Button>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{:else}
				<!-- Show "Coming Soon" when Stripe not configured -->
				<div class="bg-gradient-to-br from-brand-50 to-purple-50 dark:from-brand-900/20 dark:to-purple-900/20 rounded-xl shadow-sm border border-brand-200 dark:border-brand-800 p-6">
					<div class="flex items-start gap-4">
						<div class="w-12 h-12 rounded-full bg-brand-100 dark:bg-brand-900/50 flex items-center justify-center flex-shrink-0">
							<svg class="w-6 h-6 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
						</div>
						<div class="flex-1">
							<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-2">
								Paid Plans Coming Soon
							</h3>
							<p class="text-slate-600 dark:text-slate-400 mb-4">
								We're finalizing our pricing for Starter and Pro plans. Enjoy full access to all features during our beta period.
							</p>
							<p class="text-sm text-slate-500 dark:text-slate-400 mb-4">
								Interested in upgrading when available? Let us know and we'll notify you.
							</p>
							<Button
								variant="secondary"
								onclick={() => window.location.href = 'mailto:support@boardof.one?subject=Upgrade%20Interest'}
							>
								Contact Sales
							</Button>
						</div>
					</div>
				</div>
			{/if}
		{/if}

		<!-- Meeting Credits -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<div class="flex items-start justify-between mb-4">
				<div>
					<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
						Meeting Credits
					</h3>
					<p class="text-sm text-slate-600 dark:text-slate-400">
						Prepaid meetings that never expire
					</p>
				</div>
				{#if credits?.meeting_credits}
					<div class="flex items-center gap-2 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 px-3 py-1.5 rounded-full">
						<Package class="w-4 h-4" />
						<span class="font-semibold">{credits.meeting_credits} credit{credits.meeting_credits === 1 ? '' : 's'}</span>
					</div>
				{/if}
			</div>

			{#if !credits?.meeting_credits}
				<p class="text-sm text-slate-500 dark:text-slate-400 mb-4">
					No meeting credits. Purchase a bundle to get started.
				</p>
			{/if}

			<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
				{#each MEETING_BUNDLES as bundle (bundle.meetings)}
					<button
						class="p-3 rounded-lg border text-center transition-colors {bundle.meetings === 5
							? 'border-brand-500 bg-brand-50/50 dark:bg-brand-900/10 hover:bg-brand-50 dark:hover:bg-brand-900/20'
							: 'border-slate-200 dark:border-slate-700 hover:border-brand-300 dark:hover:border-brand-600'}"
						onclick={() => purchaseBundle(bundle.meetings)}
						disabled={purchasingBundle !== null}
					>
						<div class="text-xl font-bold text-slate-900 dark:text-white">
							{bundle.meetings}
						</div>
						<div class="text-xs text-slate-500 dark:text-slate-400">
							meeting{bundle.meetings > 1 ? 's' : ''}
						</div>
						<div class="mt-2 text-sm font-semibold text-brand-600 dark:text-brand-400">
							{#if purchasingBundle === bundle.meetings}
								...
							{:else}
								£{bundle.price}
							{/if}
						</div>
					</button>
				{/each}
			</div>
		</div>

		<!-- Usage -->
		<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
			<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
				Usage This Month
			</h3>

			<div class="space-y-4">
				<div>
					<div class="flex items-center justify-between mb-2">
						<span class="text-sm text-slate-600 dark:text-slate-400">Meetings</span>
						<span class="text-sm font-medium text-slate-900 dark:text-white">
							{usage?.meetings_used ?? 0} / {usage?.meetings_limit ?? '∞'}
						</span>
					</div>
					<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
						<div
							class="h-full rounded-full transition-all duration-300 {getUsagePercent(usage?.meetings_used ?? 0, usage?.meetings_limit ?? null) > 80 ? 'bg-amber-500' : 'bg-brand-500'}"
							style="width: {usage?.meetings_limit ? getUsagePercent(usage?.meetings_used ?? 0, usage?.meetings_limit ?? null) : 0}%"
						></div>
					</div>
					{#if usage?.meetings_remaining !== null && usage?.meetings_remaining !== undefined}
						<p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
							{usage.meetings_remaining} meetings remaining
						</p>
					{:else if usage?.meetings_limit === null}
						<p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
							Unlimited meetings
						</p>
					{/if}
				</div>

				{#if usage && usage.total_cost_cents > 0}
					<div class="pt-4 border-t border-slate-200 dark:border-slate-700">
						<div class="flex items-center justify-between">
							<span class="text-sm text-slate-600 dark:text-slate-400">API costs this month</span>
							<span class="text-sm font-medium text-slate-900 dark:text-white">
								{formatPrice(usage.total_cost_cents)}
							</span>
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Payment Method (only show for paying customers) -->
		{#if plan?.tier !== 'free'}
			<div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-6">
				<div class="flex items-center gap-4">
					<div class="w-10 h-10 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center">
						<svg class="w-5 h-5 text-slate-600 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
						</svg>
					</div>
					<div class="flex-1">
						<h3 class="font-medium text-slate-700 dark:text-slate-300">Payment Method</h3>
						<p class="text-sm text-slate-500 dark:text-slate-400">
							Manage payment methods through the billing portal
						</p>
					</div>
					<Button variant="secondary" onclick={openBillingPortal}>
						Manage
					</Button>
				</div>
			</div>

			<!-- Invoices -->
			<div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-6">
				<div class="flex items-center gap-4">
					<div class="w-10 h-10 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center">
						<svg class="w-5 h-5 text-slate-600 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
					</div>
					<div class="flex-1">
						<h3 class="font-medium text-slate-700 dark:text-slate-300">Invoices</h3>
						<p class="text-sm text-slate-500 dark:text-slate-400">
							View and download invoices through the billing portal
						</p>
					</div>
					<Button variant="secondary" onclick={openBillingPortal}>
						View
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
					<p class="font-semibold mb-1">Need help with billing?</p>
					<p class="text-blue-800 dark:text-blue-300">
						Contact us at <a href="mailto:support@boardof.one" class="underline hover:no-underline">support@boardof.one</a> for any billing questions or to request plan changes.
					</p>
				</div>
			</div>
		</div>
	</div>
{/if}
