<script lang="ts">
	import { env } from '$env/dynamic/public';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { apiClient } from '$lib/api/client';
	import type { GSCStatusResponse, GSCSitesResponse } from '$lib/api/types';
	import { Search, Link2, Unlink, CheckCircle, AlertCircle, Loader2 } from 'lucide-svelte';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';

	let gscStatus = $state<GSCStatusResponse | null>(null);
	let gscSites = $state<GSCSitesResponse | null>(null);
	let loading = $state(true);
	let sitesLoading = $state(false);
	let selectingLoading = $state(false);
	let disconnectLoading = $state(false);
	let error = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	// Handle OAuth callback params
	$effect(() => {
		const gscConnected = $page.url.searchParams.get('gsc_connected');
		const gscError = $page.url.searchParams.get('gsc_error');

		if (gscConnected === 'true') {
			successMessage = 'Google Search Console connected successfully. Please select a site below.';
			// Clear URL params
			const url = new URL(window.location.href);
			url.searchParams.delete('gsc_connected');
			window.history.replaceState({}, '', url.pathname);
		}

		if (gscError) {
			const errorMessages: Record<string, string> = {
				invalid_request: 'Invalid OAuth request. Please try again.',
				invalid_state: 'OAuth session expired. Please try again.',
				token_exchange_failed: 'Failed to exchange OAuth token. Please try again.',
				unexpected_error: 'An unexpected error occurred. Please try again.',
				access_denied: 'Access was denied. Please grant the required permissions.'
			};
			error = errorMessages[gscError] || `OAuth error: ${gscError}`;
			// Clear URL params
			const url = new URL(window.location.href);
			url.searchParams.delete('gsc_error');
			window.history.replaceState({}, '', url.pathname);
		}
	});

	onMount(async () => {
		await loadStatus();
	});

	async function loadStatus() {
		loading = true;
		error = null;
		try {
			gscStatus = await apiClient.getGSCStatus();
			// If connected but no site selected, load sites
			if (gscStatus.connected && !gscStatus.site_url) {
				await loadSites();
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load GSC status';
		} finally {
			loading = false;
		}
	}

	async function loadSites() {
		sitesLoading = true;
		try {
			gscSites = await apiClient.listGSCSites();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load GSC sites';
		} finally {
			sitesLoading = false;
		}
	}

	async function selectSite(siteUrl: string) {
		selectingLoading = true;
		error = null;
		try {
			gscStatus = await apiClient.selectGSCSite(siteUrl);
			successMessage = `Site "${siteUrl}" selected successfully.`;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to select site';
		} finally {
			selectingLoading = false;
		}
	}

	async function disconnect() {
		if (!confirm('Are you sure you want to disconnect Google Search Console?')) return;

		disconnectLoading = true;
		error = null;
		successMessage = null;
		try {
			await apiClient.disconnectGSC();
			gscStatus = { connected: false, feature_enabled: gscStatus?.feature_enabled ?? true };
			gscSites = null;
			successMessage = 'Google Search Console disconnected.';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to disconnect';
		} finally {
			disconnectLoading = false;
		}
	}

	function connectGSC() {
		// Redirect to backend OAuth endpoint
		window.location.href = `${env.PUBLIC_API_URL}/api/v1/integrations/search-console/connect`;
	}
</script>

<svelte:head>
	<title>Integrations - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="Integrations" />

	<!-- Main Content -->
	<main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Success/Error Messages -->
		{#if successMessage}
			<div
				class="mb-6 p-4 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg flex items-start gap-3"
			>
				<CheckCircle class="w-5 h-5 text-success-600 dark:text-success-400 flex-shrink-0 mt-0.5" />
				<p class="text-success-700 dark:text-success-300">{successMessage}</p>
			</div>
		{/if}

		{#if error}
			<div
				class="mb-6 p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg flex items-start gap-3"
			>
				<AlertCircle class="w-5 h-5 text-error-600 dark:text-error-400 flex-shrink-0 mt-0.5" />
				<p class="text-error-700 dark:text-error-300">{error}</p>
			</div>
		{/if}

		<!-- Google Search Console Section -->
		<div
			class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700"
		>
			<div class="p-6 border-b border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
						<Search class="w-6 h-6 text-brand-600 dark:text-brand-400" />
					</div>
					<div>
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Google Search Console
						</h2>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">
							Connect to track SEO performance metrics
						</p>
					</div>
				</div>
			</div>

			<div class="p-6">
				{#if loading}
					<div class="flex items-center justify-center py-8">
						<Loader2 class="w-6 h-6 text-brand-500 animate-spin" />
					</div>
				{:else if gscStatus && !gscStatus.feature_enabled}
					<EmptyState
						title="Google Search Console integration is disabled"
						description="Contact support to enable this feature."
						icon={Search}
					/>
				{:else if gscStatus && !gscStatus.connected}
					<EmptyState
						title="Connect Google Search Console"
						description="Connect your Google Search Console account to track SEO metrics for decisions."
					>
						{#snippet actions()}
							<button
								onclick={connectGSC}
								class="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg font-medium transition-colors"
							>
								<Link2 class="w-4 h-4" />
								Connect Google Search Console
							</button>
						{/snippet}
					</EmptyState>
				{:else if gscStatus && gscStatus.connected && !gscStatus.site_url}
					<!-- Connected, No Site Selected -->
					<div>
						<p class="text-neutral-600 dark:text-neutral-400 mb-4">
							Select a Search Console property to track:
						</p>

						{#if sitesLoading}
							<div class="flex items-center gap-2 text-neutral-500">
								<Loader2 class="w-4 h-4 animate-spin" />
								Loading sites...
							</div>
						{:else if gscSites && gscSites.sites.length > 0}
							<div class="space-y-2">
								{#each gscSites.sites as site (site.site_url)}
									<button
										onclick={() => selectSite(site.site_url)}
										disabled={selectingLoading}
										class="w-full flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-700/50 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg border border-neutral-200 dark:border-neutral-600 transition-colors disabled:opacity-50"
									>
										<div class="text-left">
											<p class="font-medium text-neutral-900 dark:text-white">
												{site.site_url}
											</p>
											<p class="text-sm text-neutral-500 dark:text-neutral-400">
												{site.permission_level}
											</p>
										</div>
										{#if selectingLoading}
											<Loader2 class="w-4 h-4 text-brand-500 animate-spin" />
										{:else}
											<span class="text-sm text-brand-600 dark:text-brand-400">Select</span>
										{/if}
									</button>
								{/each}
							</div>
						{:else}
							<p class="text-neutral-500 dark:text-neutral-400">
								No sites found. Make sure your Google account has access to Search Console
								properties.
							</p>
						{/if}

						<div class="mt-6 pt-4 border-t border-neutral-200 dark:border-neutral-700">
							<button
								onclick={disconnect}
								disabled={disconnectLoading}
								class="inline-flex items-center gap-2 text-sm text-error-600 dark:text-error-400 hover:text-error-700 dark:hover:text-error-300 disabled:opacity-50"
							>
								{#if disconnectLoading}
									<Loader2 class="w-4 h-4 animate-spin" />
								{:else}
									<Unlink class="w-4 h-4" />
								{/if}
								Disconnect
							</button>
						</div>
					</div>
				{:else if gscStatus && gscStatus.connected && gscStatus.site_url}
					<!-- Connected with Site -->
					<div>
						<div class="flex items-start justify-between">
							<div>
								<div class="flex items-center gap-2 mb-2">
									<CheckCircle class="w-5 h-5 text-success-500" />
									<span class="font-medium text-success-700 dark:text-success-400">Connected</span>
								</div>
								<p class="text-neutral-900 dark:text-white font-medium">{gscStatus.site_url}</p>
								{#if gscStatus.connected_at}
									<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
										Connected {new Date(gscStatus.connected_at).toLocaleDateString()}
										{#if gscStatus.connected_by}
											by {gscStatus.connected_by}
										{/if}
									</p>
								{/if}
							</div>
							<button
								onclick={disconnect}
								disabled={disconnectLoading}
								class="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-error-600 dark:text-error-400 hover:bg-error-50 dark:hover:bg-error-900/20 rounded-lg transition-colors disabled:opacity-50"
							>
								{#if disconnectLoading}
									<Loader2 class="w-4 h-4 animate-spin" />
								{:else}
									<Unlink class="w-4 h-4" />
								{/if}
								Disconnect
							</button>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</main>
</div>
