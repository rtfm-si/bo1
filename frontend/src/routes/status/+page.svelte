<script lang="ts">
	/**
	 * Status Page - External service monitoring links
	 */
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { onMount } from 'svelte';

	interface TrafficStats {
		timestamp: string;
		status: 'green' | 'amber' | 'red';
		message: string;
		current_hour: string;
		requests_this_hour: number;
		hourly_average: number;
	}

	let trafficStats: TrafficStats | null = $state(null);
	let trafficError: string | null = $state(null);
	let trafficNotAvailable = $state(false);

	onMount(async () => {
		try {
			const res = await fetch('/api/status/traffic');
			if (res.ok) {
				trafficStats = await res.json();
			} else if (res.status === 404) {
				// Endpoint not implemented yet - show graceful message
				trafficNotAvailable = true;
			} else {
				trafficError = 'Unable to load traffic stats';
			}
		} catch {
			trafficError = 'Unable to load traffic stats';
		}
	});

	const services = [
		{
			name: 'Board of One',
			description: 'Application & API',
			provider: 'Digital Ocean',
			statusUrl: 'https://status.digitalocean.com',
			icon: 'app'
		},
		{
			name: 'Anthropic (Claude)',
			description: 'Primary AI Provider',
			provider: 'Anthropic',
			statusUrl: 'https://status.anthropic.com',
			icon: 'ai'
		},
		{
			name: 'OpenAI',
			description: 'Secondary AI Provider',
			provider: 'OpenAI',
			statusUrl: 'https://status.openai.com',
			icon: 'ai'
		},
		{
			name: 'Voyage AI',
			description: 'Embeddings Provider',
			provider: 'Voyage AI',
			statusUrl: 'https://voyageai.com',
			icon: 'embed'
		}
	];
</script>

<svelte:head>
	<title>Status - Board of One</title>
	<meta name="description" content="Check the operational status of Board of One and our service providers." />
</svelte:head>

<div class="min-h-screen flex flex-col">
	<Header />

	<main class="flex-grow bg-white dark:bg-neutral-900 py-16">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="text-center mb-12">
				<h1 class="text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
					System Status
				</h1>
				<p class="text-lg text-neutral-600 dark:text-neutral-400">
					Monitor the status of Board of One and our service providers.
				</p>
			</div>

			<!-- Traffic Health -->
			<div class="mb-8">
				<div class="bg-white dark:bg-neutral-800 rounded-xl border border-neutral-200 dark:border-neutral-700 p-6">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-4">
							<div class="w-12 h-12 rounded-lg flex items-center justify-center
								{trafficStats?.status === 'green' ? 'bg-green-100 dark:bg-green-900/30' : ''}
								{trafficStats?.status === 'amber' ? 'bg-amber-100 dark:bg-amber-900/30' : ''}
								{trafficStats?.status === 'red' ? 'bg-red-100 dark:bg-red-900/30' : ''}
								{!trafficStats && !trafficNotAvailable ? 'bg-neutral-100 dark:bg-neutral-700' : ''}
								{trafficNotAvailable ? 'bg-neutral-100 dark:bg-neutral-700' : ''}
							">
								{#if trafficStats?.status === 'green'}
									<svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
									</svg>
								{:else if trafficStats?.status === 'amber'}
									<svg class="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
									</svg>
								{:else if trafficStats?.status === 'red'}
									<svg class="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
									</svg>
								{:else if trafficNotAvailable}
									<svg class="w-6 h-6 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
								{:else}
									<svg class="w-6 h-6 text-neutral-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
								{/if}
							</div>
							<div>
								<h2 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
									Traffic Health
								</h2>
								<p class="text-sm text-neutral-600 dark:text-neutral-400">
									{#if trafficStats}
										{trafficStats.message} &middot; {trafficStats.requests_this_hour} requests this hour
									{:else if trafficNotAvailable}
										<span class="text-neutral-500 dark:text-neutral-400">Traffic monitoring coming soon</span>
									{:else if trafficError}
										{trafficError}
									{:else}
										Loading...
									{/if}
								</p>
							</div>
						</div>
						{#if trafficStats}
							<div class="flex items-center gap-2">
								<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
									{trafficStats.status === 'green' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : ''}
									{trafficStats.status === 'amber' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' : ''}
									{trafficStats.status === 'red' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' : ''}
								">
									{trafficStats.status === 'green' ? 'Operational' : trafficStats.status === 'amber' ? 'Degraded' : 'Issue'}
								</span>
							</div>
						{/if}
					</div>
				</div>
			</div>

			<!-- Status Cards -->
			<div class="space-y-4">
				{#each services as service}
					<a
						href={service.statusUrl}
						target="_blank"
						rel="noopener noreferrer"
						class="block bg-white dark:bg-neutral-800 rounded-xl border border-neutral-200 dark:border-neutral-700 p-6 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-md transition-all group"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-4">
								<div class="w-12 h-12 rounded-lg flex items-center justify-center
									{service.icon === 'app' ? 'bg-brand-100 dark:bg-brand-900/30' : ''}
									{service.icon === 'ai' ? 'bg-purple-100 dark:bg-purple-900/30' : ''}
									{service.icon === 'embed' ? 'bg-blue-100 dark:bg-blue-900/30' : ''}
								">
									{#if service.icon === 'app'}
										<svg class="w-6 h-6 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
										</svg>
									{:else if service.icon === 'ai'}
										<svg class="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
										</svg>
									{:else}
										<svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
										</svg>
									{/if}
								</div>
								<div>
									<h2 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
										{service.name}
									</h2>
									<p class="text-sm text-neutral-600 dark:text-neutral-400">
										{service.description} &middot; {service.provider}
									</p>
								</div>
							</div>
							<div class="flex items-center gap-2 text-neutral-400 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
								<span class="text-sm">View Status</span>
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
								</svg>
							</div>
						</div>
					</a>
				{/each}
			</div>

			<!-- Note -->
			<div class="mt-12 p-6 bg-neutral-50 dark:bg-neutral-800 rounded-xl border border-neutral-200 dark:border-neutral-700">
				<div class="flex gap-4">
					<div class="flex-shrink-0">
						<svg class="w-6 h-6 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
					</div>
					<div>
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 mb-1">About Service Status</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">
							Board of One relies on multiple AI providers to deliver expert deliberation.
							If you experience issues, check the status pages above. For application-specific
							issues, contact us at <a href="mailto:support@boardofone.com" class="text-brand-600 dark:text-brand-400 hover:underline">support@boardofone.com</a>.
						</p>
					</div>
				</div>
			</div>
		</div>
	</main>

	<Footer />
</div>
