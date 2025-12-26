<script lang="ts">
	import { onMount } from 'svelte';
	import { ArrowLeft, FlaskConical, Users, Clock, DollarSign, CheckCircle } from 'lucide-svelte';
	import { adminApi, type ExperimentMetricsResponse } from '$lib/api/admin';

	let experimentData = $state<ExperimentMetricsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			experimentData = await adminApi.getPersonaCountExperiment();
		} catch (e) {
			console.error('Failed to load experiment data:', e);
			error = e instanceof Error ? e.message : 'Failed to load experiment data';
		} finally {
			loading = false;
		}
	});

	function formatDuration(seconds: number | null): string {
		if (seconds === null) return '-';
		const mins = Math.floor(seconds / 60);
		const secs = Math.round(seconds % 60);
		return `${mins}m ${secs}s`;
	}
</script>

<svelte:head>
	<title>A/B Experiments - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center gap-4">
				<a
					href="/admin"
					class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
					aria-label="Back to admin"
				>
					<ArrowLeft class="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
				</a>
				<div class="flex items-center gap-3">
					<FlaskConical class="w-6 h-6 text-brand-600 dark:text-brand-400" />
					<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
						A/B Experiments
					</h1>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if loading}
			<div class="flex items-center justify-center h-64">
				<div class="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-500"></div>
			</div>
		{:else if error}
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4">
				<p class="text-error-700 dark:text-error-400">{error}</p>
			</div>
		{:else if experimentData}
			<!-- Persona Count Experiment -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
				<div class="p-6 border-b border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<h2 class="text-xl font-semibold text-neutral-900 dark:text-white">
								Persona Count Experiment
							</h2>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
								Testing 3 vs 5 personas per meeting for cost optimization
							</p>
						</div>
						<div class="text-right">
							<p class="text-sm text-neutral-600 dark:text-neutral-400">Total Sessions</p>
							<p class="text-2xl font-bold text-neutral-900 dark:text-white">
								{experimentData.total_sessions}
							</p>
						</div>
					</div>
					<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-2">
						Period: {new Date(experimentData.period_start).toLocaleDateString()} - {new Date(experimentData.period_end).toLocaleDateString()}
					</p>
				</div>

				<!-- Variants Grid -->
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
					{#each experimentData.variants as variant}
						<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-5">
							<div class="flex items-center justify-between mb-4">
								<div class="flex items-center gap-2">
									<Users class="w-5 h-5 text-brand-600 dark:text-brand-400" />
									<span class="text-lg font-semibold text-neutral-900 dark:text-white">
										{variant.variant} Personas
									</span>
								</div>
								<span class="px-3 py-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-full text-sm font-medium">
									{variant.variant === 3 ? 'Treatment' : 'Control'}
								</span>
							</div>

							<div class="grid grid-cols-2 gap-4">
								<!-- Sessions -->
								<div>
									<p class="text-sm text-neutral-600 dark:text-neutral-400">Sessions</p>
									<p class="text-xl font-semibold text-neutral-900 dark:text-white">
										{variant.session_count}
									</p>
								</div>

								<!-- Completion Rate -->
								<div>
									<p class="text-sm text-neutral-600 dark:text-neutral-400 flex items-center gap-1">
										<CheckCircle class="w-3.5 h-3.5" />
										Completion
									</p>
									<p class="text-xl font-semibold text-neutral-900 dark:text-white">
										{variant.completion_rate.toFixed(1)}%
									</p>
								</div>

								<!-- Avg Cost -->
								<div>
									<p class="text-sm text-neutral-600 dark:text-neutral-400 flex items-center gap-1">
										<DollarSign class="w-3.5 h-3.5" />
										Avg Cost
									</p>
									<p class="text-xl font-semibold text-neutral-900 dark:text-white">
										{variant.avg_cost !== null ? `$${variant.avg_cost.toFixed(3)}` : '-'}
									</p>
								</div>

								<!-- Avg Duration -->
								<div>
									<p class="text-sm text-neutral-600 dark:text-neutral-400 flex items-center gap-1">
										<Clock class="w-3.5 h-3.5" />
										Avg Duration
									</p>
									<p class="text-xl font-semibold text-neutral-900 dark:text-white">
										{formatDuration(variant.avg_duration_seconds)}
									</p>
								</div>

								<!-- Avg Rounds -->
								<div>
									<p class="text-sm text-neutral-600 dark:text-neutral-400">Avg Rounds</p>
									<p class="text-xl font-semibold text-neutral-900 dark:text-white">
										{variant.avg_rounds !== null ? variant.avg_rounds.toFixed(1) : '-'}
									</p>
								</div>

								<!-- Actual Persona Count -->
								<div>
									<p class="text-sm text-neutral-600 dark:text-neutral-400">Actual Personas</p>
									<p class="text-xl font-semibold text-neutral-900 dark:text-white">
										{variant.avg_persona_count !== null ? variant.avg_persona_count.toFixed(1) : '-'}
									</p>
								</div>
							</div>
						</div>
					{/each}
				</div>

				<!-- Summary -->
				{#if experimentData.variants.length >= 2}
					{@const treatment = experimentData.variants.find(v => v.variant === 3)}
					{@const control = experimentData.variants.find(v => v.variant === 5)}
					{#if treatment && control && treatment.avg_cost !== null && control.avg_cost !== null}
						{@const costDiff = control.avg_cost - treatment.avg_cost}
						{@const costPctDiff = (costDiff / control.avg_cost) * 100}
						<div class="p-6 bg-neutral-100 dark:bg-neutral-700/30 border-t border-neutral-200 dark:border-neutral-700">
							<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
								Cost Savings Analysis
							</h3>
							<p class="text-neutral-600 dark:text-neutral-400">
								{#if costDiff > 0}
									3 personas saves <span class="font-semibold text-success-600 dark:text-success-400">${costDiff.toFixed(4)}</span>
									(<span class="font-semibold text-success-600 dark:text-success-400">{costPctDiff.toFixed(1)}%</span>) per session compared to 5 personas.
								{:else}
									3 personas costs <span class="font-semibold text-error-600 dark:text-error-400">${Math.abs(costDiff).toFixed(4)}</span>
									more per session compared to 5 personas.
								{/if}
							</p>
						</div>
					{/if}
				{/if}
			</div>
		{:else}
			<div class="bg-neutral-100 dark:bg-neutral-800 rounded-lg p-8 text-center">
				<FlaskConical class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
				<p class="text-neutral-600 dark:text-neutral-400">No experiment data available yet.</p>
			</div>
		{/if}
	</main>
</div>
