<script lang="ts">
	/**
	 * UsagePanel Component - Display all usage metrics for user's tier
	 * Shows usage meters for meetings, datasets, mentor chats
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { UsageResponse } from '$lib/api/types';
	import BoCard from './BoCard.svelte';
	import UsageMeter from './UsageMeter.svelte';
	import Badge from './Badge.svelte';
	import Spinner from './Spinner.svelte';

	interface Props {
		title?: string;
		compact?: boolean;
	}

	let { title = 'Usage & Limits', compact = false }: Props = $props();

	let usage = $state<UsageResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function loadUsage() {
		try {
			loading = true;
			error = null;
			usage = await apiClient.getUsage();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load usage';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadUsage();
	});

	// Tier display names and colors
	const tierConfig: Record<string, { label: string; color: 'neutral' | 'success' | 'brand' }> = {
		free: { label: 'Free', color: 'neutral' },
		starter: { label: 'Starter', color: 'success' },
		pro: { label: 'Pro', color: 'brand' },
		enterprise: { label: 'Enterprise', color: 'brand' }
	};

	const tierDisplay = $derived(tierConfig[usage?.effective_tier || 'free'] || tierConfig.free);
	const hasOverride = $derived(usage && usage.tier !== usage.effective_tier);
</script>

{#if compact}
	<!-- Compact inline display -->
	<div class="space-y-2">
		{#if loading}
			<div class="flex items-center gap-2 text-sm text-neutral-500">
				<Spinner size="sm" />
				Loading usage...
			</div>
		{:else if error}
			<div class="text-sm text-error-600 dark:text-error-400">{error}</div>
		{:else if usage}
			<div class="flex items-center gap-2 mb-2">
				<Badge variant={tierDisplay.color}>{tierDisplay.label}</Badge>
				{#if hasOverride}
					<span class="text-xs text-neutral-500">(override active)</span>
				{/if}
			</div>
			{#each usage.metrics as metric (metric.metric)}
				<UsageMeter {metric} compact />
			{/each}
		{/if}
	</div>
{:else}
	<!-- Full card display -->
	<BoCard>
		{#snippet header()}
			<h3 class="text-lg font-medium text-neutral-900 dark:text-neutral-100">{title}</h3>
		{/snippet}
		{#if loading}
			<div class="flex items-center justify-center py-8">
				<Spinner size="md" />
			</div>
		{:else if error}
			<div class="text-center py-8">
				<p class="text-error-600 dark:text-error-400 mb-2">{error}</p>
				<button
					onclick={loadUsage}
					class="text-sm text-brand-600 dark:text-brand-400 hover:underline"
				>
					Retry
				</button>
			</div>
		{:else if usage}
			<!-- Tier badge -->
			<div class="flex items-center gap-2 mb-4">
				<span class="text-sm text-neutral-600 dark:text-neutral-400">Current Plan:</span>
				<Badge variant={tierDisplay.color}>{tierDisplay.label}</Badge>
				{#if hasOverride}
					<span class="text-xs text-neutral-500 dark:text-neutral-500">(override from {usage.tier})</span>
				{/if}
			</div>

			<!-- Usage meters -->
			<div class="space-y-4">
				{#each usage.metrics as metric (metric.metric)}
					<UsageMeter {metric} />
				{/each}
			</div>

			<!-- Upgrade prompt for free tier -->
			{#if usage.effective_tier === 'free'}
				<div
					class="mt-6 p-4 bg-brand-50 dark:bg-brand-950/30 rounded-lg border border-brand-200 dark:border-brand-800"
				>
					<p class="text-sm text-brand-800 dark:text-brand-200 mb-2">
						Need more capacity? Upgrade to unlock higher limits.
					</p>
					<a
						href="/settings/billing"
						class="text-sm font-medium text-brand-600 dark:text-brand-400 hover:underline"
					>
						View Plans
					</a>
				</div>
			{/if}
		{/if}
	</BoCard>
{/if}
