<script lang="ts">
	/**
	 * MeetingBundles Component - One-time meeting purchase options
	 */
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import { MEETING_BUNDLES, type MeetingBundle } from '$lib/data/pricing';
	import { apiClient } from '$lib/api/client';
	import { Package, Zap } from 'lucide-svelte';

	let loading = $state<number | null>(null);
	let error = $state<string | null>(null);

	async function purchaseBundle(bundle: MeetingBundle) {
		loading = bundle.meetings;
		error = null;

		try {
			const result = await apiClient.purchaseMeetingBundle(bundle.meetings);
			// Redirect to Stripe checkout
			window.location.href = result.url;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to start checkout';
			loading = null;
		}
	}
</script>

<div class="space-y-6">
	<div class="text-center">
		<h2 class="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
			Meeting Bundles
		</h2>
		<p class="mt-2 text-neutral-600 dark:text-neutral-400">
			Pay as you go with one-time meeting purchases. No subscription required.
		</p>
	</div>

	{#if error}
		<div
			class="p-4 rounded-lg bg-error-50 dark:bg-error-900/20 text-error-700 dark:text-error-300 text-sm text-center"
		>
			{error}
		</div>
	{/if}

	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
		{#each MEETING_BUNDLES as bundle (bundle.meetings)}
			<BoCard
				class="{bundle.meetings === 5
					? 'ring-2 ring-brand-500'
					: ''} transition-shadow hover:shadow-lg"
			>
				<div class="text-center space-y-4">
					{#if bundle.meetings === 5}
						<span
							class="inline-block px-3 py-1 text-xs font-semibold text-brand-700 dark:text-brand-300 bg-brand-100 dark:bg-brand-900/30 rounded-full"
						>
							Most Popular
						</span>
					{:else}
						<div class="h-6"></div>
					{/if}

					<div class="flex items-center justify-center gap-2">
						<Package class="w-6 h-6 text-brand-500" />
						<span class="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
							{bundle.meetings}
						</span>
						<span class="text-neutral-600 dark:text-neutral-400">
							meeting{bundle.meetings > 1 ? 's' : ''}
						</span>
					</div>

					<div>
						<span class="text-3xl font-bold text-neutral-900 dark:text-neutral-100">
							£{bundle.price}
						</span>
						<span class="text-sm text-neutral-500">one-time</span>
					</div>

					<p class="text-sm text-neutral-600 dark:text-neutral-400">
						{bundle.description}
					</p>

					<BoButton
						variant={bundle.meetings === 5 ? 'brand' : 'outline'}
						class="w-full"
						disabled={loading !== null}
						onclick={() => purchaseBundle(bundle)}
					>
						{#if loading === bundle.meetings}
							<span class="flex items-center gap-2">
								<Zap class="w-4 h-4 animate-pulse" />
								Processing...
							</span>
						{:else}
							Buy Now
						{/if}
					</BoButton>
				</div>
			</BoCard>
		{/each}
	</div>

	<p class="text-center text-sm text-neutral-500">
		Credits never expire. Use them anytime for AI-powered deliberation meetings.
	</p>
</div>
