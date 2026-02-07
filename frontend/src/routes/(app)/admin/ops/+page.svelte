<script lang="ts">
	import { onMount } from 'svelte';
	import {
		Activity,
		AlertTriangle,
		CheckCircle,
		Clock,
		Database,
		RefreshCw,
		Server,
		Settings,
		Wrench,
		XCircle,
		Zap
	} from 'lucide-svelte';
	import {
		adminApi,
		type ErrorPattern,
		type RemediationLogEntry,
		type SystemHealthResponse
	} from '$lib/api/admin';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';

	// State
	let health = $state<SystemHealthResponse | null>(null);
	let patterns = $state<ErrorPattern[]>([]);
	let remediations = $state<RemediationLogEntry[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let checkRunning = $state(false);
	let lastCheckResult = $state<{ message: string; type: 'success' | 'error' } | null>(null);

	// Auto-refresh interval
	let refreshInterval: ReturnType<typeof setInterval>;
	const REFRESH_INTERVAL_MS = 30000;

	onMount(() => {
		loadData();
		refreshInterval = setInterval(loadData, REFRESH_INTERVAL_MS);
		return () => clearInterval(refreshInterval);
	});

	async function loadData() {
		try {
			const [healthRes, patternsRes, remediationsRes] = await Promise.all([
				adminApi.getSystemHealth(),
				adminApi.getErrorPatterns(),
				adminApi.getRemediationHistory({ limit: 20 })
			]);
			health = healthRes;
			patterns = patternsRes.patterns;
			remediations = remediationsRes.entries;
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load data';
		} finally {
			loading = false;
		}
	}

	async function triggerCheck() {
		checkRunning = true;
		lastCheckResult = null;
		try {
			const result = await adminApi.triggerErrorCheck(true);
			if (result.error) {
				lastCheckResult = { message: result.error, type: 'error' };
			} else {
				lastCheckResult = {
					message: `Scanned ${result.errors_scanned} errors, ${result.patterns_matched} matches, ${result.remediations_triggered} remediations`,
					type: 'success'
				};
			}
			await loadData();
		} catch (e) {
			lastCheckResult = {
				message: e instanceof Error ? e.message : 'Check failed',
				type: 'error'
			};
		} finally {
			checkRunning = false;
		}
	}

	async function togglePattern(pattern: ErrorPattern) {
		try {
			await adminApi.updateErrorPattern(pattern.id, { enabled: !pattern.enabled });
			await loadData();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update pattern';
		}
	}

	function getHealthStatusColor(status: string): string {
		switch (status) {
			case 'healthy':
				return 'text-success-600 dark:text-success-400';
			case 'degraded':
				return 'text-warning-600 dark:text-warning-400';
			case 'unhealthy':
				return 'text-error-600 dark:text-error-400';
			default:
				return 'text-neutral-600 dark:text-neutral-400';
		}
	}

	function getHealthBgColor(status: string): string {
		switch (status) {
			case 'healthy':
				return 'bg-success-100 dark:bg-success-900/30';
			case 'degraded':
				return 'bg-warning-100 dark:bg-warning-900/30';
			case 'unhealthy':
				return 'bg-error-100 dark:bg-error-900/30';
			default:
				return 'bg-neutral-100 dark:bg-neutral-800';
		}
	}

	function getSeverityColor(severity: string): string {
		switch (severity) {
			case 'critical':
				return 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400';
			case 'high':
				return 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400';
			case 'medium':
				return 'bg-info-100 text-info-700 dark:bg-info-900/30 dark:text-info-400';
			default:
				return 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-400';
		}
	}

	function getOutcomeColor(outcome: string): string {
		switch (outcome) {
			case 'success':
				return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400';
			case 'failure':
				return 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400';
			case 'partial':
				return 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400';
			default:
				return 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-400';
		}
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleString();
	}

	function getComponentIcon(name: string) {
		switch (name) {
			case 'redis':
				return Database;
			case 'postgres':
				return Database;
			case 'llm_providers':
				return Zap;
			default:
				return Server;
		}
	}
</script>

<svelte:head>
	<title>AI Ops Self-Healing - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="AI Ops Self-Healing" icon={Wrench}>
		{#snippet badge()}
			<span class="text-sm text-neutral-600 dark:text-neutral-400">
				Error pattern detection and automated recovery
			</span>
		{/snippet}
		{#snippet actions()}
			<BoButton variant="outline" onclick={loadData} disabled={loading}>
				<RefreshCw class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
				Refresh
			</BoButton>
			<BoButton variant="brand" onclick={triggerCheck} disabled={checkRunning}>
				<Wrench class="w-4 h-4 {checkRunning ? 'animate-spin' : ''}" />
				Run Check
			</BoButton>
		{/snippet}
	</AdminPageHeader>

	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-8">
		{#if error}
			<Alert variant="error" class="mb-6">
				{error}
			</Alert>
		{/if}

		{#if lastCheckResult}
			<Alert variant={lastCheckResult.type === 'success' ? 'success' : 'error'} class="mb-6">
				{lastCheckResult.message}
			</Alert>
		{/if}

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<RefreshCw class="w-8 h-8 animate-spin text-brand-600" />
			</div>
		{:else}
			<!-- System Health Overview -->
			<section class="mb-8">
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
					System Health
				</h2>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
					<!-- Overall Status -->
					<BoCard>
						<div class="flex items-center gap-4">
							<div
								class="p-3 rounded-lg {getHealthBgColor(health?.overall ?? 'unknown')}"
							>
								{#if health?.overall === 'healthy'}
									<CheckCircle class="w-6 h-6 {getHealthStatusColor('healthy')}" />
								{:else if health?.overall === 'degraded'}
									<AlertTriangle
										class="w-6 h-6 {getHealthStatusColor('degraded')}"
									/>
								{:else}
									<XCircle class="w-6 h-6 {getHealthStatusColor('unhealthy')}" />
								{/if}
							</div>
							<div>
								<p class="text-sm text-neutral-600 dark:text-neutral-400">
									Overall Status
								</p>
								<p
									class="text-xl font-semibold capitalize {getHealthStatusColor(health?.overall ?? 'unknown')}"
								>
									{health?.overall ?? 'Unknown'}
								</p>
							</div>
						</div>
					</BoCard>

					<!-- Component Health -->
					{#each Object.entries(health?.components ?? {}) as [name, component]}
						{@const status =
							typeof component === 'object' && 'status' in component
								? (component.status as string)
								: 'unknown'}
						{@const Icon = getComponentIcon(name)}
						<BoCard>
							<div class="flex items-center gap-4">
								<div class="p-3 rounded-lg {getHealthBgColor(status)}">
									<Icon class="w-6 h-6 {getHealthStatusColor(status)}" />
								</div>
								<div>
									<p class="text-sm text-neutral-600 dark:text-neutral-400 capitalize">
										{name.replace('_', ' ')}
									</p>
									<p
										class="text-xl font-semibold capitalize {getHealthStatusColor(status)}"
									>
										{status}
									</p>
								</div>
							</div>
						</BoCard>
					{/each}
				</div>
			</section>

			<!-- Error Patterns -->
			<section class="mb-8">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
						Error Patterns
					</h2>
					<span class="text-sm text-neutral-600 dark:text-neutral-400">
						{patterns.length} patterns configured
					</span>
				</div>
				<BoCard>
					<div class="overflow-x-auto">
						<table class="w-full">
							<thead>
								<tr
									class="border-b border-neutral-200 dark:border-neutral-700 text-left"
								>
									<th
										class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
									>
										Pattern
									</th>
									<th
										class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
									>
										Type
									</th>
									<th
										class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
									>
										Severity
									</th>
									<th
										class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
									>
										Threshold
									</th>
									<th
										class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
									>
										Matches
									</th>
									<th
										class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
									>
										Last Remediation
									</th>
									<th
										class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
									>
										Status
									</th>
								</tr>
							</thead>
							<tbody>
								{#each patterns as pattern}
									<tr
										class="border-b border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
									>
										<td class="px-4 py-3">
											<div>
												<p
													class="font-medium text-neutral-900 dark:text-white"
												>
													{pattern.pattern_name}
												</p>
												{#if pattern.description}
													<p
														class="text-sm text-neutral-500 dark:text-neutral-400"
													>
														{pattern.description}
													</p>
												{/if}
											</div>
										</td>
										<td class="px-4 py-3">
											<span
												class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
											>
												{pattern.error_type}
											</span>
										</td>
										<td class="px-4 py-3">
											<span
												class="inline-flex items-center px-2 py-1 rounded text-xs font-medium {getSeverityColor(pattern.severity)}"
											>
												{pattern.severity}
											</span>
										</td>
										<td class="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-400">
											{pattern.threshold_count} / {pattern.threshold_window_minutes}min
										</td>
										<td class="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-400">
											<span
												class="font-medium {pattern.match_count > 0
													? 'text-warning-600 dark:text-warning-400'
													: ''}"
											>
												{pattern.match_count.toLocaleString()}
											</span>
											{#if pattern.last_match_at}
												<p class="text-xs text-neutral-400">
													{formatDate(pattern.last_match_at)}
												</p>
											{/if}
										</td>
										<td class="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-400">
											{#if pattern.last_remediation}
												{formatDate(pattern.last_remediation)}
											{:else}
												<span class="text-neutral-400">Never</span>
											{/if}
										</td>
										<td class="px-4 py-3">
											<button
												class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {pattern.enabled
													? 'bg-brand-600'
													: 'bg-neutral-300 dark:bg-neutral-600'}"
												onclick={() => togglePattern(pattern)}
												aria-label={pattern.enabled ? 'Disable' : 'Enable'}
											>
												<span
													class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {pattern.enabled
														? 'tranneutral-x-6'
														: 'tranneutral-x-1'}"
												></span>
											</button>
										</td>
									</tr>
								{:else}
									<tr>
										<td colspan="7">
											<EmptyState title="No error patterns configured" icon={Settings} />
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</BoCard>
			</section>

			<!-- Recent Remediations -->
			<section>
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
						Recent Remediations
					</h2>
					<span class="text-sm text-neutral-600 dark:text-neutral-400">
						Last 20 actions
					</span>
				</div>
				<BoCard>
					{#if remediations.length === 0}
						<EmptyState title="No remediations yet" description="Auto-remediation events will appear here" icon={Activity} />
					{:else}
						<div class="overflow-x-auto">
							<table class="w-full">
								<thead>
									<tr
										class="border-b border-neutral-200 dark:border-neutral-700 text-left"
									>
										<th
											class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
										>
											Time
										</th>
										<th
											class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
										>
											Pattern
										</th>
										<th
											class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
										>
											Fix Type
										</th>
										<th
											class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
										>
											Outcome
										</th>
										<th
											class="px-4 py-3 text-sm font-medium text-neutral-600 dark:text-neutral-400"
										>
											Duration
										</th>
									</tr>
								</thead>
								<tbody>
									{#each remediations as entry}
										<tr
											class="border-b border-neutral-100 dark:border-neutral-800"
										>
											<td class="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-400">
												{formatDate(entry.triggered_at)}
											</td>
											<td class="px-4 py-3 text-sm font-medium text-neutral-900 dark:text-white">
												{entry.pattern_name ?? 'Unknown'}
											</td>
											<td class="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-400">
												{entry.fix_type ?? '-'}
											</td>
											<td class="px-4 py-3">
												<span
													class="inline-flex items-center px-2 py-1 rounded text-xs font-medium {getOutcomeColor(entry.outcome)}"
												>
													{entry.outcome}
												</span>
											</td>
											<td class="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-400">
												{entry.duration_ms ? `${entry.duration_ms}ms` : '-'}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</BoCard>
			</section>
		{/if}
	</main>
</div>
