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

	// Calculate data completeness percentage for a competitor
	function getDataCompleteness(competitor: CompetitorProfile): { percentage: number; populated: number; total: number } {
		const allFields = [
			'tagline', 'product_description', 'pricing_model', 'target_market',
			'business_model', 'value_proposition', 'tech_stack', 'funding_info',
			'employee_count', 'recent_news', 'industry'
		];

		// Fields available per tier
		const tierFields: Record<string, string[]> = {
			basic: ['tagline', 'product_description', 'industry'],
			standard: ['tagline', 'product_description', 'industry', 'pricing_model', 'target_market', 'business_model'],
			deep: allFields
		};

		const availableFields = tierFields[dataDepth] || tierFields.basic;
		let populated = 0;

		for (const field of availableFields) {
			const value = competitor[field as keyof CompetitorProfile];
			if (value !== null && value !== undefined && value !== '' &&
			    !(Array.isArray(value) && value.length === 0)) {
				populated++;
			}
		}

		return {
			percentage: Math.round((populated / availableFields.length) * 100),
			populated,
			total: availableFields.length
		};
	}

	// Get completeness color
	function getCompletenessColor(percentage: number): string {
		if (percentage >= 75) return 'bg-green-500';
		if (percentage >= 50) return 'bg-amber-500';
		return 'bg-red-400';
	}

	// Collapsible sections state
	let expandedSections = $state<Record<string, Set<string>>>({});

	function toggleSection(competitorId: string, section: string) {
		if (!expandedSections[competitorId]) {
			expandedSections[competitorId] = new Set();
		}
		if (expandedSections[competitorId].has(section)) {
			expandedSections[competitorId].delete(section);
		} else {
			expandedSections[competitorId].add(section);
		}
		expandedSections = { ...expandedSections };
	}

	function isSectionExpanded(competitorId: string, section: string): boolean {
		return expandedSections[competitorId]?.has(section) ?? false;
	}

	// Comparison table state
	let showComparison = $state(true);
</script>

<svelte:head>
	<title>Competitor Watch - Board of One</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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

				<!-- Quick Comparison Table (Standard/Deep tier, >1 competitor) -->
				{#if dataDepth !== 'basic' && competitors.length > 1}
					<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
						<button
							type="button"
							class="w-full flex items-center justify-between p-4 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
							onclick={() => showComparison = !showComparison}
						>
							<div class="flex items-center gap-2">
								<span class="text-lg">📊</span>
								<span class="font-semibold text-slate-900 dark:text-white">Quick Comparison</span>
							</div>
							<svg
								class="w-5 h-5 text-slate-400 transition-transform {showComparison ? 'rotate-180' : ''}"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
							</svg>
						</button>
						{#if showComparison}
							<div class="border-t border-slate-200 dark:border-slate-700 overflow-x-auto">
								<table class="w-full text-sm">
									<thead class="bg-slate-50 dark:bg-slate-700/50">
										<tr>
											<th class="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">Competitor</th>
											<th class="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">Industry</th>
											<th class="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">Pricing</th>
											<th class="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">Target Market</th>
											{#if dataDepth === 'deep'}
												<th class="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">Team Size</th>
											{/if}
											<th class="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">Data</th>
										</tr>
									</thead>
									<tbody class="divide-y divide-slate-200 dark:divide-slate-700">
										{#each competitors as competitor (competitor.id)}
											{@const completeness = getDataCompleteness(competitor)}
											<tr class="hover:bg-slate-50 dark:hover:bg-slate-700/30">
												<td class="px-4 py-3 font-medium text-slate-900 dark:text-white">
													{competitor.name}
												</td>
												<td class="px-4 py-3 text-slate-600 dark:text-slate-400">
													{competitor.industry || '—'}
												</td>
												<td class="px-4 py-3 text-slate-600 dark:text-slate-400">
													{competitor.pricing_model || '—'}
												</td>
												<td class="px-4 py-3 text-slate-600 dark:text-slate-400">
													{competitor.target_market || '—'}
												</td>
												{#if dataDepth === 'deep'}
													<td class="px-4 py-3 text-slate-600 dark:text-slate-400">
														{competitor.employee_count || '—'}
													</td>
												{/if}
												<td class="px-4 py-3">
													<div class="flex items-center gap-2">
														<div class="w-16 h-2 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
															<div class="h-full {getCompletenessColor(completeness.percentage)}" style="width: {completeness.percentage}%"></div>
														</div>
														<span class="text-xs text-slate-500 dark:text-slate-400">{completeness.percentage}%</span>
													</div>
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						{/if}
					</div>
				{/if}

				{#each competitors as competitor (competitor.id)}
					{@const completeness = getDataCompleteness(competitor)}
					<div
						class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
					>
						<!-- Header with name, industry badge, and actions -->
						<div class="flex items-start justify-between mb-4">
							<div class="flex items-center gap-3">
								<div
									class="w-10 h-10 bg-slate-100 dark:bg-slate-700 rounded-lg flex items-center justify-center text-lg font-semibold text-slate-600 dark:text-slate-300"
								>
									{competitor.name.charAt(0).toUpperCase()}
								</div>
								<div>
									<div class="flex items-center gap-2">
										<h4 class="font-semibold text-slate-900 dark:text-white">{competitor.name}</h4>
										{#if competitor.industry}
											<span class="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400">
												{competitor.industry}
											</span>
										{/if}
									</div>
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
								<!-- Data completeness indicator -->
								<div class="flex items-center gap-1.5 mr-2" title="{completeness.populated}/{completeness.total} fields populated">
									<div class="w-12 h-1.5 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
										<div class="h-full {getCompletenessColor(completeness.percentage)}" style="width: {completeness.percentage}%"></div>
									</div>
									<span class="text-xs text-slate-500 dark:text-slate-400">{completeness.percentage}%</span>
								</div>
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

						<!-- Section: Overview (tagline, description) -->
						{#if competitor.tagline || competitor.product_description}
							<div class="space-y-2 mb-4">
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

						<!-- Section: Market & Business (Standard+ tier) -->
						{#if dataDepth !== 'basic' && (competitor.pricing_model || competitor.target_market || competitor.business_model)}
							<div class="border-t border-slate-200 dark:border-slate-700 pt-4 mt-4">
								<button
									type="button"
									class="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
									onclick={() => toggleSection(competitor.id!, 'market')}
								>
									<svg class="w-3 h-3 transition-transform {isSectionExpanded(competitor.id!, 'market') ? 'rotate-90' : ''}" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
									</svg>
									Market & Business
								</button>
								{#if isSectionExpanded(competitor.id!, 'market')}
									<div class="grid grid-cols-2 gap-4 pl-5">
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
										{#if competitor.business_model}
											<div class="col-span-2">
												<span class="text-xs text-slate-500 dark:text-slate-400">Business Model</span>
												<p class="text-sm text-slate-900 dark:text-white">{competitor.business_model}</p>
											</div>
										{/if}
									</div>
								{:else}
									<!-- Collapsed preview -->
									<div class="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400 pl-5">
										{#if competitor.pricing_model}<span>{competitor.pricing_model}</span>{/if}
										{#if competitor.target_market}<span>• {competitor.target_market}</span>{/if}
									</div>
								{/if}
							</div>
						{/if}

						<!-- Section: Company & Funding (Deep tier) -->
						{#if dataDepth === 'deep' && (competitor.funding_info || competitor.employee_count)}
							<div class="border-t border-slate-200 dark:border-slate-700 pt-4 mt-4">
								<button
									type="button"
									class="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
									onclick={() => toggleSection(competitor.id!, 'company')}
								>
									<svg class="w-3 h-3 transition-transform {isSectionExpanded(competitor.id!, 'company') ? 'rotate-90' : ''}" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
									</svg>
									Company & Funding
								</button>
								{#if isSectionExpanded(competitor.id!, 'company')}
									<div class="grid grid-cols-2 gap-4 pl-5">
										{#if competitor.employee_count}
											<div>
												<span class="text-xs text-slate-500 dark:text-slate-400">Team Size</span>
												<p class="text-sm text-slate-900 dark:text-white">{competitor.employee_count} employees</p>
											</div>
										{/if}
										{#if competitor.funding_info}
											<div>
												<span class="text-xs text-slate-500 dark:text-slate-400">Funding</span>
												<p class="text-sm text-slate-900 dark:text-white">{competitor.funding_info}</p>
											</div>
										{/if}
									</div>
								{:else}
									<div class="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400 pl-5">
										{#if competitor.employee_count}<span>{competitor.employee_count} employees</span>{/if}
										{#if competitor.funding_info}<span>• {competitor.funding_info}</span>{/if}
									</div>
								{/if}
							</div>
						{/if}

						<!-- Section: Product & Tech (Deep tier) -->
						{#if dataDepth === 'deep' && (competitor.value_proposition || competitor.tech_stack?.length)}
							<div class="border-t border-slate-200 dark:border-slate-700 pt-4 mt-4">
								<button
									type="button"
									class="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
									onclick={() => toggleSection(competitor.id!, 'tech')}
								>
									<svg class="w-3 h-3 transition-transform {isSectionExpanded(competitor.id!, 'tech') ? 'rotate-90' : ''}" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
									</svg>
									Product & Tech
								</button>
								{#if isSectionExpanded(competitor.id!, 'tech')}
									<div class="space-y-3 pl-5">
										{#if competitor.value_proposition}
											<div>
												<span class="text-xs text-slate-500 dark:text-slate-400">Value Proposition</span>
												<p class="text-sm text-slate-900 dark:text-white">{competitor.value_proposition}</p>
											</div>
										{/if}
										{#if competitor.tech_stack?.length}
											<div>
												<span class="text-xs text-slate-500 dark:text-slate-400">Tech Stack</span>
												<div class="flex flex-wrap gap-1.5 mt-1">
													{#each competitor.tech_stack as tech}
														<span class="text-xs px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400">
															{tech}
														</span>
													{/each}
												</div>
											</div>
										{/if}
									</div>
								{:else}
									<div class="flex flex-wrap gap-1.5 pl-5">
										{#if competitor.tech_stack?.length}
											{#each competitor.tech_stack.slice(0, 4) as tech}
												<span class="text-xs px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400">
													{tech}
												</span>
											{/each}
											{#if competitor.tech_stack.length > 4}
												<span class="text-xs text-slate-500">+{competitor.tech_stack.length - 4} more</span>
											{/if}
										{:else if competitor.value_proposition}
											<span class="text-xs text-slate-500 dark:text-slate-400 truncate max-w-xs">
												{competitor.value_proposition}
											</span>
										{/if}
									</div>
								{/if}
							</div>
						{/if}

						<!-- Section: Recent News (Deep tier) -->
						{#if dataDepth === 'deep' && competitor.recent_news?.length}
							<div class="border-t border-slate-200 dark:border-slate-700 pt-4 mt-4">
								<button
									type="button"
									class="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
									onclick={() => toggleSection(competitor.id!, 'news')}
								>
									<svg class="w-3 h-3 transition-transform {isSectionExpanded(competitor.id!, 'news') ? 'rotate-90' : ''}" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
									</svg>
									Recent News ({competitor.recent_news.length})
								</button>
								{#if isSectionExpanded(competitor.id!, 'news')}
									<ul class="space-y-2 pl-5">
										{#each competitor.recent_news as news}
											<li class="flex items-start gap-2">
												<span class="text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap mt-0.5">
													{news.date ? new Date(news.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : ''}
												</span>
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
								{:else}
									<div class="text-xs text-slate-500 dark:text-slate-400 pl-5">
										{competitor.recent_news[0]?.title || 'View recent news'}
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
</div>
