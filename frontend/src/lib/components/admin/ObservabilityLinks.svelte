<script lang="ts">
	import { ExternalLink } from 'lucide-svelte';

	interface Props {
		grafana_url?: string | null;
		prometheus_url?: string | null;
		sentry_url?: string | null;
		status_url?: string | null;
		analytics_url?: string | null;
	}

	let { grafana_url, prometheus_url, sentry_url, status_url, analytics_url }: Props = $props();

	// Only show card if at least one URL is configured
	const hasAnyLinks = grafana_url || prometheus_url || sentry_url || status_url || analytics_url;
</script>

{#if hasAnyLinks}
	<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 mb-8">
		<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Quick Links</h2>
		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
			{#if grafana_url}
				<a
					href={grafana_url}
					target="_blank"
					rel="noopener noreferrer"
					class="flex items-center justify-between px-4 py-3 rounded-lg bg-neutral-50 dark:bg-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-600 border border-neutral-200 dark:border-neutral-600 transition-colors group"
				>
					<div class="flex items-center gap-3">
						<div class="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
							<svg
								class="w-5 h-5 text-orange-600 dark:text-orange-400"
								fill="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z"
								/>
							</svg>
						</div>
						<div>
							<p class="font-medium text-neutral-900 dark:text-white">Grafana</p>
							<p class="text-xs text-neutral-500">Dashboards & Monitoring</p>
						</div>
					</div>
					<ExternalLink class="w-4 h-4 text-neutral-400 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors" />
				</a>
			{/if}

			{#if prometheus_url}
				<a
					href={prometheus_url}
					target="_blank"
					rel="noopener noreferrer"
					class="flex items-center justify-between px-4 py-3 rounded-lg bg-neutral-50 dark:bg-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-600 border border-neutral-200 dark:border-neutral-600 transition-colors group"
				>
					<div class="flex items-center gap-3">
						<div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
							<svg
								class="w-5 h-5 text-blue-600 dark:text-blue-400"
								fill="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"
								/>
							</svg>
						</div>
						<div>
							<p class="font-medium text-neutral-900 dark:text-white">Prometheus</p>
							<p class="text-xs text-neutral-500">Metrics & Queries</p>
						</div>
					</div>
					<ExternalLink class="w-4 h-4 text-neutral-400 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors" />
				</a>
			{/if}

			{#if sentry_url}
				<a
					href={sentry_url}
					target="_blank"
					rel="noopener noreferrer"
					class="flex items-center justify-between px-4 py-3 rounded-lg bg-neutral-50 dark:bg-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-600 border border-neutral-200 dark:border-neutral-600 transition-colors group"
				>
					<div class="flex items-center gap-3">
						<div class="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
							<svg
								class="w-5 h-5 text-purple-600 dark:text-purple-400"
								fill="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"
								/>
							</svg>
						</div>
						<div>
							<p class="font-medium text-neutral-900 dark:text-white">Sentry</p>
							<p class="text-xs text-neutral-500">Error Tracking</p>
						</div>
					</div>
					<ExternalLink class="w-4 h-4 text-neutral-400 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors" />
				</a>
			{/if}

			{#if status_url}
				<a
					href={status_url}
					target="_blank"
					rel="noopener noreferrer"
					class="flex items-center justify-between px-4 py-3 rounded-lg bg-neutral-50 dark:bg-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-600 border border-neutral-200 dark:border-neutral-600 transition-colors group"
				>
					<div class="flex items-center gap-3">
						<div class="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
							<svg
								class="w-5 h-5 text-green-600 dark:text-green-400"
								fill="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"
								/>
							</svg>
						</div>
						<div>
							<p class="font-medium text-neutral-900 dark:text-white">Status</p>
							<p class="text-xs text-neutral-500">Uptime Monitoring</p>
						</div>
					</div>
					<ExternalLink class="w-4 h-4 text-neutral-400 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors" />
				</a>
			{/if}

			{#if analytics_url}
				<a
					href={analytics_url}
					target="_blank"
					rel="noopener noreferrer"
					class="flex items-center justify-between px-4 py-3 rounded-lg bg-neutral-50 dark:bg-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-600 border border-neutral-200 dark:border-neutral-600 transition-colors group"
				>
					<div class="flex items-center gap-3">
						<div class="p-2 bg-pink-100 dark:bg-pink-900/30 rounded-lg">
							<svg
								class="w-5 h-5 text-pink-600 dark:text-pink-400"
								fill="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"
								/>
							</svg>
						</div>
						<div>
							<p class="font-medium text-neutral-900 dark:text-white">Analytics</p>
							<p class="text-xs text-neutral-500">Traffic & Usage</p>
						</div>
					</div>
					<ExternalLink class="w-4 h-4 text-neutral-400 group-hover:text-neutral-600 dark:group-hover:text-neutral-300 transition-colors" />
				</a>
			{/if}
		</div>
	</div>
{/if}
