<script lang="ts">
	/**
	 * Benchmarks Page - Industry and Peer benchmarks with tabbed interface
	 *
	 * Features:
	 * - Industry tab: Compare against industry standards
	 * - Peer tab: Compare against opted-in peers
	 * - URL sync: ?tab=industry|peer
	 */
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import Tabs, { type Tab } from '$lib/components/ui/Tabs.svelte';
	import IndustryBenchmarksTab from '$lib/components/benchmarks/IndustryBenchmarksTab.svelte';
	import PeerBenchmarksTab from '$lib/components/benchmarks/PeerBenchmarksTab.svelte';

	const tabs: Tab[] = [
		{ id: 'industry', label: 'Industry', icon: '📊' },
		{ id: 'peer', label: 'Peer', icon: '👥' }
	];

	// Read tab from URL, default to 'industry'
	let activeTab = $derived($page.url.searchParams.get('tab') || 'industry');

	// Sync tab changes to URL
	function handleTabChange(tabId: string) {
		const url = new URL($page.url);
		if (tabId === 'industry') {
			url.searchParams.delete('tab');
		} else {
			url.searchParams.set('tab', tabId);
		}
		goto(url.toString(), { replaceState: true, noScroll: true });
	}
</script>

<svelte:head>
	<title>Benchmarks - Board of One</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<Tabs {tabs} {activeTab} onchange={handleTabChange}>
		{#snippet children({ activeTab })}
			{#if activeTab === 'industry'}
				<IndustryBenchmarksTab />
			{:else if activeTab === 'peer'}
				<PeerBenchmarksTab />
			{/if}
		{/snippet}
	</Tabs>
</div>
