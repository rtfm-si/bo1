<script lang="ts">
	import { onMount } from 'svelte';
	import {
		ArrowLeft,
		FlaskConical,
		Users,
		Clock,
		DollarSign,
		CheckCircle,
		Plus,
		Play,
		Pause,
		StopCircle,
		Trash2,
		ChevronUp,
		HelpCircle
	} from 'lucide-svelte';
	import {
		adminApi,
		type ExperimentMetricsResponse,
		type Experiment
	} from '$lib/api/admin';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';

	// Legacy persona count experiment data
	let legacyData = $state<ExperimentMetricsResponse | null>(null);

	// New experiments management
	let experiments = $state<Experiment[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Modal states
	let showCreateModal = $state(false);
	let showHelpPanel = $state(false);

	// Create form state
	let createForm = $state({
		name: '',
		description: '',
		variants: [
			{ name: 'control', weight: 50 },
			{ name: 'treatment', weight: 50 }
		],
		metrics: ''
	});
	let createError = $state<string | null>(null);
	let creating = $state(false);

	// Action loading states
	let actionLoading = $state<Record<string, boolean>>({});

	onMount(async () => {
		await loadData();
	});

	async function loadData() {
		loading = true;
		error = null;
		try {
			const [legacyResponse, experimentsResponse] = await Promise.all([
				adminApi.getPersonaCountExperiment().catch(() => null),
				adminApi.listExperiments()
			]);
			legacyData = legacyResponse;
			experiments = experimentsResponse.experiments;
		} catch (e) {
			console.error('Failed to load experiments:', e);
			error = e instanceof Error ? e.message : 'Failed to load experiments';
		} finally {
			loading = false;
		}
	}

	async function createExperiment() {
		createError = null;
		creating = true;
		try {
			const metricsArray = createForm.metrics
				.split(',')
				.map((m) => m.trim())
				.filter(Boolean);

			await adminApi.createExperiment({
				name: createForm.name,
				description: createForm.description || undefined,
				variants: createForm.variants,
				metrics: metricsArray.length > 0 ? metricsArray : undefined
			});
			showCreateModal = false;
			resetCreateForm();
			await loadData();
		} catch (e) {
			createError = e instanceof Error ? e.message : 'Failed to create experiment';
		} finally {
			creating = false;
		}
	}

	function resetCreateForm() {
		createForm = {
			name: '',
			description: '',
			variants: [
				{ name: 'control', weight: 50 },
				{ name: 'treatment', weight: 50 }
			],
			metrics: ''
		};
		createError = null;
	}

	async function startExperiment(id: string) {
		actionLoading[id] = true;
		try {
			await adminApi.startExperiment(id);
			await loadData();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to start experiment';
		} finally {
			actionLoading[id] = false;
		}
	}

	async function pauseExperiment(id: string) {
		actionLoading[id] = true;
		try {
			await adminApi.pauseExperiment(id);
			await loadData();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to pause experiment';
		} finally {
			actionLoading[id] = false;
		}
	}

	async function concludeExperiment(id: string) {
		if (!confirm('Conclude this experiment? This action cannot be undone.')) return;
		actionLoading[id] = true;
		try {
			await adminApi.concludeExperiment(id);
			await loadData();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to conclude experiment';
		} finally {
			actionLoading[id] = false;
		}
	}

	async function deleteExperiment(id: string) {
		if (!confirm('Delete this experiment? This action cannot be undone.')) return;
		actionLoading[id] = true;
		try {
			await adminApi.deleteExperiment(id);
			await loadData();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete experiment';
		} finally {
			actionLoading[id] = false;
		}
	}

	function addVariant() {
		createForm.variants = [...createForm.variants, { name: '', weight: 0 }];
	}

	function removeVariant(index: number) {
		if (createForm.variants.length > 2) {
			createForm.variants = createForm.variants.filter((_, i) => i !== index);
		}
	}

	function formatDuration(seconds: number | null): string {
		if (seconds === null) return '-';
		const mins = Math.floor(seconds / 60);
		const secs = Math.round(seconds % 60);
		return `${mins}m ${secs}s`;
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleDateString();
	}

	function getStatusVariant(
		status: string
	): 'brand' | 'success' | 'warning' | 'error' | 'info' | 'neutral' {
		switch (status) {
			case 'running':
				return 'success';
			case 'paused':
				return 'warning';
			case 'concluded':
				return 'info';
			default:
				return 'neutral';
		}
	}

	const variantWeightSum = $derived(createForm.variants.reduce((sum, v) => sum + v.weight, 0));
</script>

<svelte:head>
	<title>A/B Experiments - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
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
						<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">A/B Experiments</h1>
					</div>
				</div>
				<div class="flex items-center gap-2">
					<button
						onclick={() => (showHelpPanel = !showHelpPanel)}
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
						aria-label="Toggle help"
					>
						<HelpCircle class="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
					</button>
					<BoButton variant="brand" onclick={() => (showCreateModal = true)}>
						<Plus class="w-4 h-4 mr-1" />
						New Experiment
					</BoButton>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
		<!-- Help Panel -->
		{#if showHelpPanel}
			<div
				class="bg-info-50 dark:bg-info-900/20 border border-info-200 dark:border-info-800 rounded-lg p-6"
			>
				<div class="flex items-start justify-between">
					<h3 class="text-lg font-semibold text-info-900 dark:text-info-100 mb-4">
						How to Manage Experiments
					</h3>
					<button
						onclick={() => (showHelpPanel = false)}
						class="text-info-600 dark:text-info-400 hover:text-info-800 dark:hover:text-info-200"
					>
						<ChevronUp class="w-5 h-5" />
					</button>
				</div>
				<div class="grid md:grid-cols-2 gap-6 text-sm text-info-800 dark:text-info-200">
					<div>
						<h4 class="font-medium mb-2">Experiment Lifecycle</h4>
						<ul class="space-y-1 list-disc list-inside">
							<li><strong>Draft</strong>: Configure variants and metrics</li>
							<li><strong>Running</strong>: Users are assigned to variants</li>
							<li><strong>Paused</strong>: Assignment stops, can resume</li>
							<li><strong>Concluded</strong>: Final state, analyze results</li>
						</ul>
					</div>
					<div>
						<h4 class="font-medium mb-2">Best Practices</h4>
						<ul class="space-y-1 list-disc list-inside">
							<li>Variant weights must sum to 100</li>
							<li>Define clear, measurable metrics</li>
							<li>Run until statistically significant</li>
							<li>Only one running experiment per feature</li>
						</ul>
					</div>
					<div>
						<h4 class="font-medium mb-2">Variant Assignment</h4>
						<p>Users are deterministically assigned using a hash of experiment name + user ID. The same user always gets the same variant.</p>
					</div>
					<div>
						<h4 class="font-medium mb-2">Status Transitions</h4>
						<p>
							<code class="bg-info-200 dark:bg-info-800 px-1 rounded">draft</code>
							&rarr;
							<code class="bg-info-200 dark:bg-info-800 px-1 rounded">running</code>
							&harr;
							<code class="bg-info-200 dark:bg-info-800 px-1 rounded">paused</code>
							&rarr;
							<code class="bg-info-200 dark:bg-info-800 px-1 rounded">concluded</code>
						</p>
					</div>
				</div>
			</div>
		{/if}

		{#if error}
			<Alert variant="error">{error}</Alert>
		{/if}

		{#if loading}
			<div class="flex items-center justify-center h-64">
				<div class="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-500"></div>
			</div>
		{:else}
			<!-- Experiments List -->
			<div class="space-y-4">
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Managed Experiments</h2>

				{#if experiments.length === 0}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center"
					>
						<FlaskConical class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
						<p class="text-neutral-600 dark:text-neutral-400 mb-4">No experiments created yet.</p>
						<BoButton variant="brand" onclick={() => (showCreateModal = true)}>
							<Plus class="w-4 h-4 mr-1" />
							Create First Experiment
						</BoButton>
					</div>
				{:else}
					<div class="grid gap-4">
						{#each experiments as exp}
							<div
								class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6"
							>
								<div class="flex items-start justify-between mb-4">
									<div>
										<div class="flex items-center gap-3">
											<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">
												{exp.name}
											</h3>
											<Badge variant={getStatusVariant(exp.status)}>{exp.status}</Badge>
										</div>
										{#if exp.description}
											<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
												{exp.description}
											</p>
										{/if}
									</div>
									<div class="flex items-center gap-2">
										{#if exp.status === 'draft'}
											<BoButton
												variant="brand"
												size="sm"
												loading={actionLoading[exp.id]}
												onclick={() => startExperiment(exp.id)}
											>
												<Play class="w-4 h-4 mr-1" />
												Start
											</BoButton>
											<BoButton
												variant="danger"
												size="sm"
												loading={actionLoading[exp.id]}
												onclick={() => deleteExperiment(exp.id)}
											>
												<Trash2 class="w-4 h-4" />
											</BoButton>
										{:else if exp.status === 'running'}
											<BoButton
												variant="outline"
												size="sm"
												loading={actionLoading[exp.id]}
												onclick={() => pauseExperiment(exp.id)}
											>
												<Pause class="w-4 h-4 mr-1" />
												Pause
											</BoButton>
											<BoButton
												variant="secondary"
												size="sm"
												loading={actionLoading[exp.id]}
												onclick={() => concludeExperiment(exp.id)}
											>
												<StopCircle class="w-4 h-4 mr-1" />
												Conclude
											</BoButton>
										{:else if exp.status === 'paused'}
											<BoButton
												variant="brand"
												size="sm"
												loading={actionLoading[exp.id]}
												onclick={() => startExperiment(exp.id)}
											>
												<Play class="w-4 h-4 mr-1" />
												Resume
											</BoButton>
											<BoButton
												variant="secondary"
												size="sm"
												loading={actionLoading[exp.id]}
												onclick={() => concludeExperiment(exp.id)}
											>
												<StopCircle class="w-4 h-4 mr-1" />
												Conclude
											</BoButton>
										{/if}
									</div>
								</div>

								<!-- Variants -->
								<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
									{#each exp.variants as variant}
										<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-3">
											<p class="text-sm font-medium text-neutral-900 dark:text-white">
												{variant.name}
											</p>
											<p class="text-xs text-neutral-600 dark:text-neutral-400">
												{variant.weight}% weight
											</p>
										</div>
									{/each}
								</div>

								<!-- Metrics & Dates -->
								<div class="flex flex-wrap items-center gap-4 text-sm text-neutral-600 dark:text-neutral-400">
									{#if exp.metrics.length > 0}
										<span>Metrics: {exp.metrics.join(', ')}</span>
									{/if}
									{#if exp.start_date}
										<span>Started: {formatDate(exp.start_date)}</span>
									{/if}
									{#if exp.end_date}
										<span>Concluded: {formatDate(exp.end_date)}</span>
									{/if}
									<span>Created: {formatDate(exp.created_at)}</span>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Legacy Persona Count Experiment -->
			{#if legacyData}
				<div class="mt-8">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
						Legacy Experiments
					</h2>
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden"
					>
						<div class="p-6 border-b border-neutral-200 dark:border-neutral-700">
							<div class="flex items-center justify-between">
								<div>
									<h3 class="text-xl font-semibold text-neutral-900 dark:text-white">
										Persona Count Experiment
									</h3>
									<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
										Testing 3 vs 5 personas per meeting for cost optimization
									</p>
								</div>
								<div class="text-right">
									<p class="text-sm text-neutral-600 dark:text-neutral-400">Total Sessions</p>
									<p class="text-2xl font-bold text-neutral-900 dark:text-white">
										{legacyData.total_sessions}
									</p>
								</div>
							</div>
							<p class="text-xs text-neutral-500 dark:text-neutral-500 mt-2">
								Period: {new Date(legacyData.period_start).toLocaleDateString()} - {new Date(
									legacyData.period_end
								).toLocaleDateString()}
							</p>
						</div>

						<!-- Variants Grid -->
						<div class="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
							{#each legacyData.variants as variant}
								<div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-lg p-5">
									<div class="flex items-center justify-between mb-4">
										<div class="flex items-center gap-2">
											<Users class="w-5 h-5 text-brand-600 dark:text-brand-400" />
											<span class="text-lg font-semibold text-neutral-900 dark:text-white">
												{variant.variant} Personas
											</span>
										</div>
										<span
											class="px-3 py-1 bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-full text-sm font-medium"
										>
											{variant.variant === 3 ? 'Treatment' : 'Control'}
										</span>
									</div>

									<div class="grid grid-cols-2 gap-4">
										<div>
											<p class="text-sm text-neutral-600 dark:text-neutral-400">Sessions</p>
											<p class="text-xl font-semibold text-neutral-900 dark:text-white">
												{variant.session_count}
											</p>
										</div>

										<div>
											<p
												class="text-sm text-neutral-600 dark:text-neutral-400 flex items-center gap-1"
											>
												<CheckCircle class="w-3.5 h-3.5" />
												Completion
											</p>
											<p class="text-xl font-semibold text-neutral-900 dark:text-white">
												{variant.completion_rate.toFixed(1)}%
											</p>
										</div>

										<div>
											<p
												class="text-sm text-neutral-600 dark:text-neutral-400 flex items-center gap-1"
											>
												<DollarSign class="w-3.5 h-3.5" />
												Avg Cost
											</p>
											<p class="text-xl font-semibold text-neutral-900 dark:text-white">
												{variant.avg_cost !== null ? `$${variant.avg_cost.toFixed(3)}` : '-'}
											</p>
										</div>

										<div>
											<p
												class="text-sm text-neutral-600 dark:text-neutral-400 flex items-center gap-1"
											>
												<Clock class="w-3.5 h-3.5" />
												Avg Duration
											</p>
											<p class="text-xl font-semibold text-neutral-900 dark:text-white">
												{formatDuration(variant.avg_duration_seconds)}
											</p>
										</div>

										<div>
											<p class="text-sm text-neutral-600 dark:text-neutral-400">Avg Rounds</p>
											<p class="text-xl font-semibold text-neutral-900 dark:text-white">
												{variant.avg_rounds !== null ? variant.avg_rounds.toFixed(1) : '-'}
											</p>
										</div>

										<div>
											<p class="text-sm text-neutral-600 dark:text-neutral-400">Actual Personas</p>
											<p class="text-xl font-semibold text-neutral-900 dark:text-white">
												{variant.avg_persona_count !== null
													? variant.avg_persona_count.toFixed(1)
													: '-'}
											</p>
										</div>
									</div>
								</div>
							{/each}
						</div>

						<!-- Summary -->
						{#if legacyData.variants.length >= 2}
							{@const treatment = legacyData.variants.find((v) => v.variant === 3)}
							{@const control = legacyData.variants.find((v) => v.variant === 5)}
							{#if treatment && control && treatment.avg_cost !== null && control.avg_cost !== null}
								{@const costDiff = control.avg_cost - treatment.avg_cost}
								{@const costPctDiff = (costDiff / control.avg_cost) * 100}
								<div
									class="p-6 bg-neutral-100 dark:bg-neutral-700/30 border-t border-neutral-200 dark:border-neutral-700"
								>
									<h4 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
										Cost Savings Analysis
									</h4>
									<p class="text-neutral-600 dark:text-neutral-400">
										{#if costDiff > 0}
											3 personas saves <span
												class="font-semibold text-success-600 dark:text-success-400"
												>${costDiff.toFixed(4)}</span
											>
											(<span class="font-semibold text-success-600 dark:text-success-400"
												>{costPctDiff.toFixed(1)}%</span
											>) per session compared to 5 personas.
										{:else}
											3 personas costs <span
												class="font-semibold text-error-600 dark:text-error-400"
												>${Math.abs(costDiff).toFixed(4)}</span
											>
											more per session compared to 5 personas.
										{/if}
									</p>
								</div>
							{/if}
						{/if}
					</div>
				</div>
			{/if}
		{/if}
	</main>
</div>

<!-- Create Experiment Modal -->
<Modal
	bind:open={showCreateModal}
	title="Create New Experiment"
	size="lg"
	onclose={() => {
		showCreateModal = false;
		resetCreateForm();
	}}
>
	<form
		onsubmit={(e) => {
			e.preventDefault();
			createExperiment();
		}}
		class="space-y-6"
	>
		{#if createError}
			<Alert variant="error">{createError}</Alert>
		{/if}

		<div>
			<label for="exp-name" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
				Experiment Name *
			</label>
			<input
				id="exp-name"
				type="text"
				bind:value={createForm.name}
				required
				class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				placeholder="e.g., pricing_test_2024"
			/>
		</div>

		<div>
			<label for="exp-desc" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
				Description
			</label>
			<textarea
				id="exp-desc"
				bind:value={createForm.description}
				rows="2"
				class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				placeholder="Describe the experiment goal..."
			></textarea>
		</div>

		<div>
			<div class="flex items-center justify-between mb-2">
				<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
					Variants *
				</label>
				<span class="text-sm {variantWeightSum === 100 ? 'text-success-600' : 'text-error-600'}">
					Total: {variantWeightSum}% {variantWeightSum !== 100 ? '(must be 100)' : ''}
				</span>
			</div>
			<div class="space-y-2">
				{#each createForm.variants as variant, i}
					<div class="flex items-center gap-2">
						<input
							type="text"
							bind:value={variant.name}
							required
							class="flex-1 px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
							placeholder="Variant name"
						/>
						<input
							type="number"
							bind:value={variant.weight}
							required
							min="0"
							max="100"
							class="w-24 px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
							placeholder="%"
						/>
						{#if createForm.variants.length > 2}
							<button
								type="button"
								onclick={() => removeVariant(i)}
								class="p-2 text-error-600 hover:bg-error-100 dark:hover:bg-error-900/30 rounded-lg"
							>
								<Trash2 class="w-4 h-4" />
							</button>
						{/if}
					</div>
				{/each}
			</div>
			<button
				type="button"
				onclick={addVariant}
				class="mt-2 text-sm text-brand-600 dark:text-brand-400 hover:underline"
			>
				+ Add variant
			</button>
		</div>

		<div>
			<label for="exp-metrics" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
				Metrics (comma-separated)
			</label>
			<input
				id="exp-metrics"
				type="text"
				bind:value={createForm.metrics}
				class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
				placeholder="e.g., conversion_rate, avg_cost, completion_time"
			/>
		</div>
	</form>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<BoButton
				variant="ghost"
				onclick={() => {
					showCreateModal = false;
					resetCreateForm();
				}}
			>
				Cancel
			</BoButton>
			<BoButton
				variant="brand"
				disabled={!createForm.name || variantWeightSum !== 100 || creating}
				loading={creating}
				onclick={createExperiment}
			>
				Create Experiment
			</BoButton>
		</div>
	{/snippet}
</Modal>
