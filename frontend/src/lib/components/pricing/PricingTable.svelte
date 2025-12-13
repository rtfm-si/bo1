<script lang="ts">
	/**
	 * PricingTable Component - Comparison table for pricing tiers
	 * Displays Free/Starter/Pro with feature matrix
	 */
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import { Check, X, Minus } from 'lucide-svelte';
	import {
		PRICING_TIERS,
		FEATURE_ROWS,
		formatLimit,
		type PricingTier,
		type FeatureRow
	} from '$lib/data/pricing';

	// Get the value to display for a feature row
	function getFeatureValue(tier: PricingTier, row: FeatureRow): { type: 'check' | 'x' | 'text'; value?: string } {
		if (row.type === 'limit' && row.limitKey) {
			const limitValue = tier.limits[row.limitKey];
			// Special case: API calls should show '-' if API access is disabled
			if (row.limitKey === 'api_daily' && !tier.features.api_access) {
				return { type: 'x' };
			}
			return { type: 'text', value: formatLimit(limitValue) };
		}
		if (row.type === 'feature' && row.featureKey) {
			return tier.features[row.featureKey] ? { type: 'check' } : { type: 'x' };
		}
		return { type: 'x' };
	}
</script>

<div class="overflow-x-auto">
	<!-- Mobile card view -->
	<div class="md:hidden space-y-6">
		{#each PRICING_TIERS as tier (tier.id)}
			<div
				class="rounded-lg border {tier.highlight
					? 'border-brand-500 ring-2 ring-brand-500/20'
					: 'border-neutral-200 dark:border-neutral-700'} bg-white dark:bg-neutral-800 p-6"
			>
				{#if tier.highlight}
					<span
						class="inline-block px-3 py-1 mb-4 text-xs font-semibold text-brand-700 dark:text-brand-300 bg-brand-100 dark:bg-brand-900/30 rounded-full"
					>
						Most Popular
					</span>
				{/if}

				<h3 class="text-xl font-bold text-neutral-900 dark:text-neutral-100">{tier.name}</h3>
				<p class="mt-1 text-sm text-neutral-600 dark:text-neutral-400">{tier.description}</p>

				<div class="mt-4">
					<span class="text-3xl font-bold text-neutral-900 dark:text-neutral-100"
						>{tier.priceLabel}</span
					>
					<span class="text-neutral-600 dark:text-neutral-400">/{tier.period}</span>
				</div>

				<div class="mt-6">
					<BoButton
						variant={tier.highlight ? 'brand' : 'outline'}
						class="w-full"
						onclick={() => window.location.href = tier.ctaHref}
					>
						{tier.ctaLabel}
					</BoButton>
				</div>

				<ul class="mt-6 space-y-3">
					{#each FEATURE_ROWS as row (row.key)}
						{@const featureValue = getFeatureValue(tier, row)}
						<li class="flex items-start gap-3 text-sm">
							{#if featureValue.type === 'check'}
								<Check class="w-5 h-5 text-success-500 shrink-0 mt-0.5" />
								<span class="text-neutral-700 dark:text-neutral-300">{row.label}</span>
							{:else if featureValue.type === 'x'}
								<X class="w-5 h-5 text-neutral-400 shrink-0 mt-0.5" />
								<span class="text-neutral-500">{row.label}</span>
							{:else}
								<span
									class="w-5 h-5 shrink-0 flex items-center justify-center text-brand-600 dark:text-brand-400 font-semibold text-xs"
								>
									{featureValue.value}
								</span>
								<span class="text-neutral-700 dark:text-neutral-300">{row.label}</span>
							{/if}
						</li>
					{/each}
				</ul>
			</div>
		{/each}
	</div>

	<!-- Desktop table view -->
	<table class="hidden md:table w-full">
		<thead>
			<tr>
				<th class="text-left py-4 px-4 text-neutral-600 dark:text-neutral-400 font-medium w-1/4">
					Features
				</th>
				{#each PRICING_TIERS as tier (tier.id)}
					<th
						class="text-center py-4 px-4 w-1/4 {tier.highlight ? 'bg-brand-50 dark:bg-brand-900/20' : ''}"
					>
						<div class="relative">
							{#if tier.highlight}
								<span
									class="absolute -top-8 left-1/2 -translate-x-1/2 inline-block px-3 py-1 text-xs font-semibold text-brand-700 dark:text-brand-300 bg-brand-100 dark:bg-brand-900/30 rounded-full whitespace-nowrap"
								>
									Most Popular
								</span>
							{/if}
							<div class="text-xl font-bold text-neutral-900 dark:text-neutral-100">{tier.name}</div>
							<div class="mt-2">
								<span class="text-2xl font-bold text-neutral-900 dark:text-neutral-100"
									>{tier.priceLabel}</span
								>
								<span class="text-sm text-neutral-600 dark:text-neutral-400">/{tier.period}</span>
							</div>
							<p class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">{tier.description}</p>
							<div class="mt-4">
								<BoButton
									variant={tier.highlight ? 'brand' : 'outline'}
									size="sm"
									onclick={() => window.location.href = tier.ctaHref}
								>
									{tier.ctaLabel}
								</BoButton>
							</div>
						</div>
					</th>
				{/each}
			</tr>
		</thead>
		<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
			{#each FEATURE_ROWS as row (row.key)}
				<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
					<td class="py-4 px-4">
						<div class="font-medium text-neutral-900 dark:text-neutral-100">{row.label}</div>
						{#if row.description}
							<div class="text-sm text-neutral-500">{row.description}</div>
						{/if}
					</td>
					{#each PRICING_TIERS as tier (tier.id)}
						{@const featureValue = getFeatureValue(tier, row)}
						<td
							class="py-4 px-4 text-center {tier.highlight ? 'bg-brand-50 dark:bg-brand-900/20' : ''}"
						>
							{#if featureValue.type === 'check'}
								<Check class="w-5 h-5 text-success-500 mx-auto" />
							{:else if featureValue.type === 'x'}
								<Minus class="w-5 h-5 text-neutral-400 mx-auto" />
							{:else}
								<span class="font-semibold text-neutral-900 dark:text-neutral-100">
									{featureValue.value}
								</span>
							{/if}
						</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
</div>
