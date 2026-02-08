<script lang="ts">
	/**
	 * CognitionWidget - Compact dashboard widget showing cognitive profile summary
	 * Shows style summary, top dimensions, and primary blindspot
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { CognitionProfileResponse } from '$lib/api/client';

	// State
	let profile = $state<CognitionProfileResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	// Computed
	const hasProfile = $derived(profile?.exists && profile?.gravity?.assessed_at);
	const topBlindspot = $derived(profile?.primary_blindspots?.[0] ?? null);

	onMount(async () => {
		try {
			profile = await apiClient.getCognitionProfile();
		} catch (e) {
			error = 'Failed to load';
			console.error(e);
		} finally {
			isLoading = false;
		}
	});

	function getDimensionHighlight(): string {
		if (!profile) return '';
		const highlights: string[] = [];

		const th = profile.gravity?.time_horizon;
		if (th !== null && th !== undefined) {
			if (th < 0.35) highlights.push('Action-oriented');
			else if (th > 0.65) highlights.push('Strategic planner');
		}

		const risk = profile.friction?.risk_sensitivity;
		if (risk !== null && risk !== undefined) {
			if (risk < 0.35) highlights.push('Risk-comfortable');
			else if (risk > 0.65) highlights.push('Risk-aware');
		}

		return highlights.slice(0, 2).join(' · ');
	}
</script>

{#if isLoading}
	<div class="bg-white dark:bg-neutral-800 rounded-xl p-4 border border-neutral-200 dark:border-neutral-700">
		<div class="animate-pulse flex items-center gap-3">
			<div class="w-10 h-10 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
			<div class="flex-1 space-y-2">
				<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4"></div>
				<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2"></div>
			</div>
		</div>
	</div>
{:else if !hasProfile}
	<!-- CTA to complete assessment -->
	<a
		href="/settings/cognition"
		class="block bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 rounded-xl p-4 border border-purple-200 dark:border-purple-800 hover:border-purple-300 dark:hover:border-purple-700 transition-colors"
	>
		<div class="flex items-center gap-3">
			<div class="w-10 h-10 bg-purple-100 dark:bg-purple-900/50 rounded-lg flex items-center justify-center">
				<span class="text-xl">🧠</span>
			</div>
			<div class="flex-1 min-w-0">
				<p class="font-medium text-purple-900 dark:text-purple-100 text-sm">
					Complete Your Cognitive Profile
				</p>
				<p class="text-xs text-purple-700 dark:text-purple-300 mt-0.5">
					90 seconds to personalize recommendations
				</p>
			</div>
			<span class="flex-shrink-0 inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-purple-600 dark:text-purple-400 bg-white/50 dark:bg-purple-900/30 border border-purple-200 dark:border-purple-700 rounded-lg hover:bg-white dark:hover:bg-purple-900/50 hover:border-purple-300 dark:hover:border-purple-600 transition-colors">
				Start
			</span>
		</div>
	</a>
{:else}
	<!-- Profile summary -->
	<a
		href="/settings/cognition"
		class="block bg-white dark:bg-neutral-800 rounded-xl p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-700 transition-colors"
	>
		<div class="flex items-start gap-3">
			<div class="w-10 h-10 bg-brand-100 dark:bg-brand-900/50 rounded-lg flex items-center justify-center flex-shrink-0">
				<span class="text-xl">🧠</span>
			</div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center justify-between gap-2">
					<p class="font-medium text-neutral-900 dark:text-white text-sm truncate">
						{profile?.cognitive_style_summary || 'Cognitive Profile'}
					</p>
					<span class="flex-shrink-0 inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-brand-600 dark:text-brand-400 bg-white/50 dark:bg-brand-900/30 border border-brand-200 dark:border-brand-700 rounded-lg hover:bg-white dark:hover:bg-brand-900/50 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						Update
					</span>
				</div>

				{#if getDimensionHighlight()}
					<p class="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5">
						{getDimensionHighlight()}
					</p>
				{/if}

				{#if topBlindspot}
					<div class="mt-2 flex items-center gap-1.5">
						<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-warning-100 dark:bg-warning-900/30 text-warning-800 dark:text-warning-200">
							{topBlindspot.label}
						</span>
					</div>
				{/if}
			</div>
		</div>
	</a>
{/if}
