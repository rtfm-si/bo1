<script lang="ts">
	/**
	 * Billing Settings - Plan and usage management
	 * Uses actual data from billing API
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { PlanDetails, UsageStats } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';

	// State
	let plan = $state<PlanDetails | null>(null);
	let usage = $state<UsageStats | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let portalMessage = $state<string | null>(null);

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

	onMount(async () => {
		try {
			const [planResult, usageResult] = await Promise.all([
				apiClient.getBillingPlan(),
				apiClient.getBillingUsage()
			]);
			plan = planResult;
			usage = usageResult;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load billing information';
			console.error('Failed to load billing:', e);
		} finally {
			isLoading = false;
		}
	});

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
				<Button variant="secondary" onclick={openBillingPortal}>
					Manage Plan
				</Button>
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

		<!-- Payment Method -->
		<div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-6">
			<div class="flex items-center gap-4">
				<div class="text-2xl">💳</div>
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
				<div class="text-2xl">📄</div>
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
