<script lang="ts">
	/**
	 * Competitor Watch - Track and monitor competitor intelligence
	 *
	 * Features:
	 * - Tier-based limits (Free: 3, Starter: 5, Pro: 8)
	 * - Auto-enrichment with Tavily
	 * - Change detection for monthly refresh
	 */
	import { onMount } from 'svelte';
	import {
		apiClient,
		type CompetitorProfile,
		type CompetitorListResponse
	} from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';

	// State
	let isLoading = $state(true);
	let competitors = $state<CompetitorProfile[]>([]);
	let tier = $state('free');
	let maxAllowed = $state(3);
	let dataDepth = $state<'basic' | 'standard' | 'deep'>('basic');

	// UI state
	let isAdding = $state(false);
	let isEnrichingAll = $state(false);
	let enrichingIds = $state<Set<string>>(new Set());
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);

	// New competitor form
	let newName = $state('');
	let newWebsite = $state('');

	onMount(async () => {
		await loadCompetitors();
	});

	async function loadCompetitors() {
		try {
			const response = await apiClient.getCompetitors();
			competitors = response.competitors;
			tier = response.tier;
			maxAllowed = response.max_allowed;
			dataDepth = response.data_depth;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load competitors';
		} finally {
			isLoading = false;
		}
	}

	async function addCompetitor() {
		if (!newName.trim()) return;

		isAdding = true;
		error = null;

		try {
			const newCompetitor = await apiClient.createCompetitor({
				name: newName.trim(),
				website: newWebsite.trim() || undefined
			});
			competitors = [...competitors, newCompetitor];
			newName = '';
			newWebsite = '';
			success = `Added ${newCompetitor.name} to your watch list`;
			setTimeout(() => (success = null), 3000);
		} catch (e: unknown) {
			if (e instanceof Error && e.message.includes('403')) {
				error = `You've reached your competitor limit (${maxAllowed}). Upgrade to track more.`;
			} else {
				error = e instanceof Error ? e.message : 'Failed to add competitor';
			}
		} finally {
			isAdding = false;
		}
	}

	async function enrichCompetitor(id: string) {
		enrichingIds = new Set([...enrichingIds, id]);
		error = null;

		try {
			const response = await apiClient.enrichCompetitor(id);
			if (response.success && response.competitor) {
				competitors = competitors.map((c) => (c.id === id ? response.competitor! : c));
				if (response.changes && response.changes.length > 0) {
					success = `Updated: ${response.changes.join(', ')}`;
				} else {
					success = 'No new information found';
				}
			} else {
				error = response.error || 'Enrichment failed';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to enrich competitor';
		} finally {
			enrichingIds = new Set([...enrichingIds].filter((i) => i !== id));
			setTimeout(() => (success = null), 3000);
		}
	}

	async function enrichAll() {
		isEnrichingAll = true;
		error = null;

		try {
			const response = await apiClient.enrichAllCompetitors();
			if (response.success) {
				competitors = response.competitors;
				success = `Refreshed ${response.enriched_count} competitors`;
			} else {
				error = response.errors?.join(', ') || 'Some enrichments failed';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to refresh competitors';
		} finally {
			isEnrichingAll = false;
			setTimeout(() => (success = null), 3000);
		}
	}

	async function deleteCompetitor(id: string, name: string) {
		if (!confirm(`Remove ${name} from your watch list?`)) return;

		try {
			await apiClient.deleteCompetitor(id);
			competitors = competitors.filter((c) => c.id !== id);
			success = `Removed ${name}`;
			setTimeout(() => (success = null), 3000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to remove competitor';
		}
	}

	function formatDate(dateStr: string | null | undefined): string {
		if (!dateStr) return 'Never';
		return new Date(dateStr).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		});
	}

	function getTierBadgeColor(t: string): string {
		switch (t) {
			case 'pro':
				return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
			case 'starter':
				return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
			default:
				return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
		}
	}

	function getDepthLabel(depth: string): string {
		switch (depth) {
			case 'deep':
				return 'Full Intel';
			case 'standard':
				return 'Standard';
			default:
				return 'Basic';
		}
	}
</script>

<svelte:head>
	<title>Competitor Watch - Board of One</title>
</svelte:head>

{#if isLoading}
	<div class="flex items-center justify-center py-12">
		<div
			class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"
		></div>
	</div>
{:else}
	<div class="space-y-6">
		<!-- Header -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
		>
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-3">
					<span class="text-2xl">🔍</span>
					<div>
						<h2 class="text-lg font-semibold text-slate-900 dark:text-white">Competitor Watch</h2>
						<p class="text-sm text-slate-600 dark:text-slate-400">
							Track and monitor your competitors with AI-powered intelligence
						</p>
					</div>
				</div>
				<div class="flex items-center gap-3">
					<span class={`text-xs px-2 py-1 rounded-full font-medium ${getTierBadgeColor(tier)}`}>
						{tier.charAt(0).toUpperCase() + tier.slice(1)} Plan
					</span>
					<span class="text-sm text-slate-500 dark:text-slate-400">
						{competitors.length}/{maxAllowed} tracked
					</span>
				</div>
			</div>

			<!-- Data depth indicator -->
			<div
				class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-700/50 rounded-lg px-3 py-2"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<span>
					Your plan includes <strong>{getDepthLabel(dataDepth)}</strong> competitor data.
					{#if tier === 'free'}
						<a href="/settings/billing" class="text-brand-600 dark:text-brand-400 hover:underline">
							Upgrade for deeper insights
						</a>
					{/if}
				</span>
			</div>
		</div>

		<!-- Alerts -->
		{#if success}
			<Alert variant="success">{success}</Alert>
		{/if}
		{#if error}
			<Alert variant="error">{error}</Alert>
		{/if}

		<!-- Add competitor form -->
		{#if competitors.length < maxAllowed}
			<div
				class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
			>
				<h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-4">Add Competitor</h3>
				<div class="flex gap-4">
					<div class="flex-1">
						<Input
							placeholder="Company name"
							bind:value={newName}
							onkeydown={(e: KeyboardEvent) => e.key === 'Enter' && addCompetitor()}
						/>
					</div>
					<div class="flex-1">
						<Input placeholder="Website URL (optional)" bind:value={newWebsite} />
					</div>
					<Button onclick={addCompetitor} disabled={isAdding || !newName.trim()} loading={isAdding}>
						{isAdding ? 'Adding...' : 'Add'}
					</Button>
				</div>
			</div>
		{:else}
			<div
				class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4"
			>
				<div class="flex gap-3">
					<svg
						class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
						/>
					</svg>
					<div class="text-sm text-amber-900 dark:text-amber-200">
						<p class="font-semibold">Competitor limit reached</p>
						<p class="text-amber-800 dark:text-amber-300">
							You're tracking the maximum {maxAllowed} competitors on the {tier} plan.
							<a
								href="/settings/billing"
								class="text-amber-700 dark:text-amber-400 font-medium hover:underline"
							>
								Upgrade to track more
							</a>
						</p>
					</div>
				</div>
			</div>
		{/if}

		<!-- Competitors list -->
		{#if competitors.length > 0}
			<div class="space-y-4">
				<div class="flex items-center justify-between">
					<h3 class="text-sm font-semibold text-slate-900 dark:text-white">Tracked Competitors</h3>
					<Button
						variant="outline"
						size="sm"
						onclick={enrichAll}
						disabled={isEnrichingAll}
						loading={isEnrichingAll}
					>
						{isEnrichingAll ? 'Refreshing...' : 'Refresh All'}
					</Button>
				</div>

				{#each competitors as competitor (competitor.id)}
					<div
						class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
					>
						<div class="flex items-start justify-between mb-4">
							<div class="flex items-center gap-3">
								<div
									class="w-10 h-10 bg-slate-100 dark:bg-slate-700 rounded-lg flex items-center justify-center text-lg font-semibold text-slate-600 dark:text-slate-300"
								>
									{competitor.name.charAt(0).toUpperCase()}
								</div>
								<div>
									<h4 class="font-semibold text-slate-900 dark:text-white">{competitor.name}</h4>
									{#if competitor.website}
										<a
											href={competitor.website.startsWith('http')
												? competitor.website
												: `https://${competitor.website}`}
											target="_blank"
											rel="noopener noreferrer"
											class="text-sm text-brand-600 dark:text-brand-400 hover:underline"
										>
											{competitor.website}
										</a>
									{/if}
								</div>
							</div>
							<div class="flex items-center gap-2">
								<Button
									variant="ghost"
									size="sm"
									onclick={() => enrichCompetitor(competitor.id!)}
									disabled={enrichingIds.has(competitor.id!)}
									loading={enrichingIds.has(competitor.id!)}
								>
									{enrichingIds.has(competitor.id!) ? 'Enriching...' : 'Enrich'}
								</Button>
								<button
									type="button"
									onclick={() => deleteCompetitor(competitor.id!, competitor.name)}
									class="p-2 text-slate-400 hover:text-red-500 transition-colors"
									aria-label="Remove competitor"
								>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
										/>
									</svg>
								</button>
							</div>
						</div>

						<!-- Competitor data -->
						{#if competitor.tagline || competitor.product_description}
							<div class="space-y-3 mb-4">
								{#if competitor.tagline}
									<p class="text-sm text-slate-600 dark:text-slate-400 italic">
										"{competitor.tagline}"
									</p>
								{/if}
								{#if competitor.product_description}
									<p class="text-sm text-slate-700 dark:text-slate-300">
										{competitor.product_description}
									</p>
								{/if}
							</div>
						{/if}

						<!-- Standard tier data -->
						{#if dataDepth !== 'basic' && (competitor.pricing_model || competitor.target_market)}
							<div class="grid grid-cols-2 gap-4 mb-4">
								{#if competitor.pricing_model}
									<div>
										<span class="text-xs text-slate-500 dark:text-slate-400">Pricing</span>
										<p class="text-sm text-slate-900 dark:text-white">{competitor.pricing_model}</p>
									</div>
								{/if}
								{#if competitor.target_market}
									<div>
										<span class="text-xs text-slate-500 dark:text-slate-400">Target Market</span>
										<p class="text-sm text-slate-900 dark:text-white">{competitor.target_market}</p>
									</div>
								{/if}
							</div>
						{/if}

						<!-- Deep tier data -->
						{#if dataDepth === 'deep' && (competitor.funding_info || competitor.employee_count || competitor.recent_news?.length)}
							<div class="border-t border-slate-200 dark:border-slate-700 pt-4 mt-4">
								<div class="grid grid-cols-2 gap-4">
									{#if competitor.employee_count}
										<div>
											<span class="text-xs text-slate-500 dark:text-slate-400">Team Size</span>
											<p class="text-sm text-slate-900 dark:text-white">
												{competitor.employee_count} employees
											</p>
										</div>
									{/if}
									{#if competitor.funding_info}
										<div>
											<span class="text-xs text-slate-500 dark:text-slate-400">Funding</span>
											<p class="text-sm text-slate-900 dark:text-white">{competitor.funding_info}</p>
										</div>
									{/if}
								</div>
								{#if competitor.recent_news?.length}
									<div class="mt-3">
										<span class="text-xs text-slate-500 dark:text-slate-400">Recent News</span>
										<ul class="mt-1 space-y-1">
											{#each competitor.recent_news.slice(0, 3) as news}
												<li>
													<a
														href={news.url}
														target="_blank"
														rel="noopener noreferrer"
														class="text-sm text-brand-600 dark:text-brand-400 hover:underline"
													>
														{news.title}
													</a>
												</li>
											{/each}
										</ul>
									</div>
								{/if}
							</div>
						{/if}

						<!-- Footer metadata -->
						<div
							class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mt-4 pt-4 border-t border-slate-100 dark:border-slate-700"
						>
							<span>Last enriched: {formatDate(competitor.last_enriched_at)}</span>
							{#if competitor.changes_detected?.length}
								<span class="text-green-600 dark:text-green-400">
									{competitor.changes_detected.length} updates detected
								</span>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<!-- Empty state -->
			<div
				class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-12 text-center"
			>
				<div class="text-4xl mb-4">🔍</div>
				<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-2">
					No competitors tracked yet
				</h3>
				<p class="text-slate-600 dark:text-slate-400 mb-4">
					Add your competitors above to start monitoring their activity and strategy.
				</p>
			</div>
		{/if}

		<!-- Info Box -->
		<div
			class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4"
		>
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
					<p class="font-semibold mb-1">How Competitor Watch works</p>
					<ul class="text-blue-800 dark:text-blue-300 space-y-1 list-disc list-inside">
						<li>Add competitors by name and optionally their website</li>
						<li>Click "Enrich" to pull the latest data from review sites and news</li>
						<li>Use "Refresh All" monthly to detect changes in their strategy</li>
						<li>This data helps our AI experts give you competitive insights during meetings</li>
					</ul>
				</div>
			</div>
		</div>
	</div>
{/if}
