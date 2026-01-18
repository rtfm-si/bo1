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
	<div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
		<div class="animate-pulse flex items-center gap-3">
			<div class="w-10 h-10 bg-slate-200 dark:bg-slate-700 rounded-lg"></div>
			<div class="flex-1 space-y-2">
				<div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4"></div>
				<div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
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
			<svg class="w-5 h-5 text-purple-500 dark:text-purple-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
			</svg>
		</div>
	</a>
{:else}
	<!-- Profile summary -->
	<a
		href="/settings/cognition"
		class="block bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 hover:border-brand-300 dark:hover:border-brand-700 transition-colors"
	>
		<div class="flex items-start gap-3">
			<div class="w-10 h-10 bg-brand-100 dark:bg-brand-900/50 rounded-lg flex items-center justify-center flex-shrink-0">
				<span class="text-xl">🧠</span>
			</div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center justify-between gap-2">
					<p class="font-medium text-slate-900 dark:text-white text-sm truncate">
						{profile?.cognitive_style_summary || 'Cognitive Profile'}
					</p>
					<svg class="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</div>

				{#if getDimensionHighlight()}
					<p class="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
						{getDimensionHighlight()}
					</p>
				{/if}

				{#if topBlindspot}
					<div class="mt-2 flex items-center gap-1.5">
						<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200">
							{topBlindspot.label}
						</span>
					</div>
				{/if}
			</div>
		</div>
	</a>
{/if}
