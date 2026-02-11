<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { Button } from '$lib/components/ui';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import { ChevronLeft, ChevronRight, FileText, Clock, Globe, User } from 'lucide-svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';

	import { formatDate } from '$lib/utils/time-formatting';
	interface ConsentAuditItem {
		user_id: string;
		email: string | null;
		terms_version: string;
		consented_at: string;
		ip_address: string | null;
	}

	let { data } = $props();

	let consents = $state<ConsentAuditItem[]>([]);
	let total = $state(0);
	let limit = $state(50);
	let offset = $state(0);
	let hasMore = $state(false);
	let currentPeriod = $state('all');

	const periods = [
		{ value: 'hour', label: 'Last Hour' },
		{ value: 'day', label: 'Last Day' },
		{ value: 'week', label: 'Last Week' },
		{ value: 'month', label: 'Last Month' },
		{ value: 'all', label: 'All Time' }
	];

	$effect(() => {
		consents = data.consents || [];
		total = data.total || 0;
		limit = data.limit || 50;
		offset = data.offset || 0;
		hasMore = data.hasMore || false;
		currentPeriod = data.period || 'all';
	});

	function handlePeriodChange(period: string) {
		const url = new URL($page.url);
		url.searchParams.set('period', period);
		url.searchParams.set('offset', '0');
		goto(url.toString());
	}

	function nextPage() {
		if (hasMore) {
			const url = new URL($page.url);
			url.searchParams.set('offset', (offset + limit).toString());
			goto(url.toString());
		}
	}

	function prevPage() {
		if (offset > 0) {
			const url = new URL($page.url);
			url.searchParams.set('offset', Math.max(0, offset - limit).toString());
			goto(url.toString());
		}
	}


	function maskIp(ip: string | null): string {
		if (!ip) return '-';
		// Show partial IP for privacy
		const parts = ip.split('.');
		if (parts.length === 4) {
			return `${parts[0]}.${parts[1]}.*.*`;
		}
		return ip.substring(0, 8) + '...';
	}

	const currentPage = $derived(Math.floor(offset / limit) + 1);
	const totalPages = $derived(Math.ceil(total / limit));
</script>

<svelte:head>
	<title>T&C Consent Audit - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="Terms & Conditions" />

	<!-- Tabs -->
	<div class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12">
			<nav class="flex gap-4">
				<a
					href="/admin/terms"
					class="py-3 px-1 border-b-2 border-transparent text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white font-medium text-sm"
				>
					Versions
				</a>
				<a
					href="/admin/terms/consents"
					class="py-3 px-1 border-b-2 border-brand-600 text-brand-600 dark:text-brand-400 font-medium text-sm"
					aria-current="page"
				>
					Consent Audit
				</a>
			</nav>
		</div>
	</div>

	<!-- Main Content -->
	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-8">
		<!-- Filters -->
		<div class="mb-6 bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
			<div class="flex items-center gap-4 flex-wrap">
				<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300">Time Period:</span>
				<div class="flex gap-2 flex-wrap">
					{#each periods as period}
						<button
							onclick={() => handlePeriodChange(period.value)}
							class="px-3 py-1.5 text-sm rounded-md transition-colors {currentPeriod === period.value
								? 'bg-brand-600 text-white'
								: 'bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600'}"
						>
							{period.label}
						</button>
					{/each}
				</div>
			</div>
		</div>

		<!-- Stats -->
		<div class="mb-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
			<div class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-brand-100 dark:bg-brand-900/20 rounded-lg">
						<FileText class="w-5 h-5 text-brand-600 dark:text-brand-400" />
					</div>
					<div>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Total Consents</p>
						<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{total}</p>
					</div>
				</div>
			</div>
			<div class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-info-100 dark:bg-info-900/20 rounded-lg">
						<Clock class="w-5 h-5 text-info-600 dark:text-info-400" />
					</div>
					<div>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Period</p>
						<p class="text-lg font-medium text-neutral-900 dark:text-white capitalize">{currentPeriod === 'all' ? 'All Time' : currentPeriod}</p>
					</div>
				</div>
			</div>
			<div class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-success-100 dark:bg-success-900/20 rounded-lg">
						<User class="w-5 h-5 text-success-600 dark:text-success-400" />
					</div>
					<div>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Page</p>
						<p class="text-lg font-medium text-neutral-900 dark:text-white">{currentPage} of {totalPages || 1}</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Table -->
		{#if consents.length === 0}
			<EmptyState title="No consent records found" description="Try adjusting the time period filter" icon={FileText} />
		{:else}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-neutral-200 dark:divide-neutral-700">
						<thead class="bg-neutral-50 dark:bg-neutral-900">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
									User
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
									Version
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
									Consented At
								</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
									IP Address
								</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each consents as consent (consent.user_id + consent.consented_at)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
									<td class="px-6 py-4 whitespace-nowrap">
										<div class="flex items-center gap-2">
											<User class="w-4 h-4 text-neutral-400" />
											<div>
												<p class="text-sm font-medium text-neutral-900 dark:text-white">
													{consent.email || 'Unknown'}
												</p>
												<p class="text-xs text-neutral-500 dark:text-neutral-400 font-mono">
													{consent.user_id.substring(0, 12)}...
												</p>
											</div>
										</div>
									</td>
									<td class="px-6 py-4 whitespace-nowrap">
										<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-brand-100 dark:bg-brand-900/20 text-brand-800 dark:text-brand-200">
											v{consent.terms_version}
										</span>
									</td>
									<td class="px-6 py-4 whitespace-nowrap">
										<div class="flex items-center gap-2 text-sm text-neutral-900 dark:text-white">
											<Clock class="w-4 h-4 text-neutral-400" />
											{formatDate(consent.consented_at)}
										</div>
									</td>
									<td class="px-6 py-4 whitespace-nowrap">
										<div class="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400 font-mono">
											<Globe class="w-4 h-4 text-neutral-400" />
											{maskIp(consent.ip_address)}
										</div>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>

				<!-- Pagination -->
				<div class="bg-neutral-50 dark:bg-neutral-900 px-6 py-3 flex items-center justify-between border-t border-neutral-200 dark:border-neutral-700">
					<div class="text-sm text-neutral-700 dark:text-neutral-300">
						Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} records
					</div>
					<div class="flex gap-2">
						<Button
							variant="secondary"
							size="sm"
							disabled={offset === 0}
							onclick={prevPage}
						>
							{#snippet children()}
								<ChevronLeft class="w-4 h-4" />
								Previous
							{/snippet}
						</Button>
						<Button
							variant="secondary"
							size="sm"
							disabled={!hasMore}
							onclick={nextPage}
						>
							{#snippet children()}
								Next
								<ChevronRight class="w-4 h-4" />
							{/snippet}
						</Button>
					</div>
				</div>
			</div>
		{/if}
	</main>
</div>
