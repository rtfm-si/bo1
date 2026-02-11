<script lang="ts">
	import { onMount } from 'svelte';
	import { Bell, RefreshCw, Calendar, Filter, CheckCircle, XCircle } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';
	import { adminApi, type AlertHistoryResponse, type AlertHistoryItem } from '$lib/api/admin';

	import { formatDate } from '$lib/utils/time-formatting';
	// State
	let alerts = $state<AlertHistoryResponse | null>(null);
	let alertTypes = $state<string[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let page = $state(0);
	let selectedType = $state<string>('');
	const pageSize = 50;

	async function loadAlerts() {
		try {
			loading = true;
			alerts = await adminApi.getAlertHistory({
				alert_type: selectedType || undefined,
				limit: pageSize,
				offset: page * pageSize
			});
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load alert history';
		} finally {
			loading = false;
		}
	}

	async function loadAlertTypes() {
		try {
			alertTypes = await adminApi.getAlertTypes();
		} catch {
			// Ignore - types are optional for filtering
		}
	}


	function getSeverityBadge(severity: string): { bg: string; text: string } {
		switch (severity) {
			case 'critical':
			case 'urgent':
				return { bg: 'bg-error-100 dark:bg-error-900/30', text: 'text-error-700 dark:text-error-400' };
			case 'high':
				return { bg: 'bg-warning-100 dark:bg-warning-900/30', text: 'text-warning-700 dark:text-warning-400' };
			case 'warning':
				return { bg: 'bg-warning-100 dark:bg-warning-900/30', text: 'text-warning-700 dark:text-warning-400' };
			case 'info':
			default:
				return { bg: 'bg-info-100 dark:bg-info-900/30', text: 'text-info-700 dark:text-info-400' };
		}
	}

	function formatAlertType(type: string): string {
		return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
	}

	function handleTypeChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		selectedType = target.value;
		page = 0;
		loadAlerts();
	}

	function nextPage() {
		if (alerts && (page + 1) * pageSize < alerts.total) {
			page++;
			loadAlerts();
		}
	}

	function prevPage() {
		if (page > 0) {
			page--;
			loadAlerts();
		}
	}

	onMount(() => {
		loadAlerts();
		loadAlertTypes();
	});
</script>

<svelte:head>
	<title>Alert History - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="Alert History" icon={Bell}>
		{#snippet actions()}
			<a href="/admin/alerts/settings">
				<Button variant="secondary" size="sm">
					Settings
				</Button>
			</a>
			<Button variant="secondary" size="sm" onclick={loadAlerts}>
				<RefreshCw class="w-4 h-4" />
				Refresh
			</Button>
		{/snippet}
	</AdminPageHeader>

	<!-- Main Content -->
	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-8">
		{#if error}
			<Alert variant="error" class="mb-6">{error}</Alert>
		{/if}

		<!-- Filter Bar -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 mb-6">
			<div class="flex items-center gap-4">
				<Filter class="w-5 h-5 text-neutral-400" />
				<label for="alert-type" class="text-sm text-neutral-600 dark:text-neutral-400">Filter by type:</label>
				<select
					id="alert-type"
					class="px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
					value={selectedType}
					onchange={handleTypeChange}
				>
					<option value="">All types</option>
					{#each alertTypes as type}
						<option value={type}>{formatAlertType(type)}</option>
					{/each}
				</select>
			</div>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
			</div>
		{:else if alerts}
			{#if alerts.alerts.length === 0}
				<EmptyState
					title="No alerts found"
					description={selectedType ? 'No alerts of this type yet' : 'Alert history will appear here when alerts are sent'}
					icon={Bell}
				/>
			{:else}
				<!-- Stats -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 mb-6">
					<div class="flex items-center gap-4">
						<div class="p-3 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
							<Bell class="w-6 h-6 text-warning-600 dark:text-warning-400" />
						</div>
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400">
								{selectedType ? `${formatAlertType(selectedType)} Alerts` : 'Total Alerts'}
							</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{alerts.total}</p>
						</div>
					</div>
				</div>

				<!-- Alert History Table -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					<table class="w-full">
						<thead class="bg-neutral-50 dark:bg-neutral-700">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Time</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Type</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Severity</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Title</th>
								<th class="px-6 py-3 text-center text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Delivered</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each alerts.alerts as alert (alert.id)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors">
									<td class="px-6 py-4">
										<div class="flex items-center gap-2">
											<Calendar class="w-4 h-4 text-neutral-400" />
											<span class="text-sm text-neutral-700 dark:text-neutral-300">{formatDate(alert.created_at)}</span>
										</div>
									</td>
									<td class="px-6 py-4">
										<span class="text-sm font-medium text-neutral-900 dark:text-white">
											{formatAlertType(alert.alert_type)}
										</span>
									</td>
									<td class="px-6 py-4">
										{#if true}
											{@const badge = getSeverityBadge(alert.severity)}
											<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {badge.bg} {badge.text}">
												{alert.severity}
											</span>
										{/if}
									</td>
									<td class="px-6 py-4">
										<span class="text-sm text-neutral-600 dark:text-neutral-400 truncate max-w-[300px] inline-block" title={alert.title}>
											{alert.title}
										</span>
									</td>
									<td class="px-6 py-4 text-center">
										{#if alert.delivered}
											<CheckCircle class="w-5 h-5 text-success-500 mx-auto" />
										{:else}
											<XCircle class="w-5 h-5 text-error-500 mx-auto" />
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>

					<!-- Pagination -->
					{#if alerts.total > pageSize}
						<div class="px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
							<p class="text-sm text-neutral-600 dark:text-neutral-400">
								Showing {page * pageSize + 1} - {Math.min((page + 1) * pageSize, alerts.total)} of {alerts.total}
							</p>
							<div class="flex items-center gap-2">
								<Button variant="secondary" size="sm" onclick={prevPage} disabled={page === 0}>
									Previous
								</Button>
								<Button variant="secondary" size="sm" onclick={nextPage} disabled={(page + 1) * pageSize >= alerts.total}>
									Next
								</Button>
							</div>
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</main>
</div>
