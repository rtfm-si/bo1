<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { isAuthenticated } from '$lib/stores/auth';
	import { apiClient } from '$lib/api/client';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import HoneypotFields from '$lib/components/ui/HoneypotFields.svelte';
	import ContextRefreshBanner from '$lib/components/ui/ContextRefreshBanner.svelte';
	import MeetingContextSelector from '$lib/components/meeting/MeetingContextSelector.svelte';
	import MeetingProjectSelector from '$lib/components/meeting/MeetingProjectSelector.svelte';
	import { AlertTriangle, X, Clock, Plus, ChevronDown, ChevronUp } from 'lucide-svelte';
	import type { Dataset, StaleInsight, SessionContextIds, MeetingCapStatus, HoneypotFields as HoneypotFieldsType } from '$lib/api/types';
	import { toast } from '$lib/stores/toast';

	let problemStatement = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);
	let datasets = $state<Dataset[]>([]);
	let selectedDatasetId = $state<string | null>(null);
	let loadingDatasets = $state(false);
	// Staleness warning state
	let pendingSessionId = $state<string | null>(null);
	let staleInsights = $state<StaleInsight[]>([]);
	let showStalenessWarning = $state(false);
	// Context selection state
	let selectedContext = $state<SessionContextIds>({});
	// Project linking state
	let selectedProjectIds = $state<string[]>([]);
	// Project link warning state
	let projectLinkWarning = $state<string | null>(null);
	let projectLinkWarningTimeout: ReturnType<typeof setTimeout> | null = null;
	// Meeting cap state
	let capStatus = $state<MeetingCapStatus | null>(null);
	let loadingCapStatus = $state(false);
	// Honeypot state
	let honeypotValues = $state<HoneypotFieldsType>({});
	// Constraints state
	let showConstraints = $state(false);
	let constraintItems = $state<Array<{ type: string; description: string; value: string }>>([]);

	const CONSTRAINT_TYPES = ['budget', 'time', 'resource', 'regulatory', 'technical', 'ethical', 'other'] as const;

	function addConstraint() {
		constraintItems = [...constraintItems, { type: 'other', description: '', value: '' }];
	}

	function removeConstraint(index: number) {
		constraintItems = constraintItems.filter((_, i) => i !== index);
	}

	onMount(() => {
		const unsubscribe = isAuthenticated.subscribe((authenticated) => {
			if (!authenticated) {
				goto('/login');
			}
		});

		// Pre-fill from URL query param (from welcome page, demo questions, or deadlock follow-up)
		const prefillQuestion = $page.url.searchParams.get('q');
		if (prefillQuestion) {
			problemStatement = prefillQuestion;
		}

		// Handle follow-up from deadlock resolution
		const followupSessionId = $page.url.searchParams.get('followup');
		if (followupSessionId) {
			// Could pre-select the original session as context in the future
			console.log(`[NewMeeting] Follow-up from session: ${followupSessionId}`);
		}

		// Pre-select project if project_id is in URL (from project detail page)
		const projectIdParam = $page.url.searchParams.get('project_id');
		if (projectIdParam) {
			selectedProjectIds = [projectIdParam];
		}

		// Load user's datasets for the selector
		loadDatasets();

		// Check meeting cap status
		loadCapStatus();

		return unsubscribe;
	});

	async function loadCapStatus() {
		try {
			loadingCapStatus = true;
			capStatus = await apiClient.getMeetingCapStatus();
		} catch (err) {
			console.warn('Failed to load meeting cap status:', err);
			// Non-blocking - allow meeting creation even if cap check fails
		} finally {
			loadingCapStatus = false;
		}
	}

	function formatResetTime(resetTime: string | null): string {
		if (!resetTime) return '';
		const reset = new Date(resetTime);
		const now = new Date();
		const diffMs = reset.getTime() - now.getTime();
		const diffMins = Math.ceil(diffMs / 60000);
		const diffHours = Math.floor(diffMins / 60);
		const remainingMins = diffMins % 60;
		if (diffHours > 0) {
			return `${diffHours}h ${remainingMins}m`;
		}
		return `${diffMins} minutes`;
	}

	async function loadDatasets() {
		try {
			loadingDatasets = true;
			const response = await apiClient.getDatasets({ limit: 100 });
			datasets = response.datasets;
		} catch (err) {
			console.warn('Failed to load datasets:', err);
			// Non-blocking - user can still create meeting without dataset
		} finally {
			loadingDatasets = false;
		}
	}

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();

		if (!problemStatement.trim()) {
			error = 'Please describe your decision';
			return;
		}

		if (problemStatement.trim().length < 20) {
			error = 'Please provide at least 20 characters describing your decision';
			return;
		}

		try {
			isSubmitting = true;
			error = null;
			projectLinkWarning = null;
			if (projectLinkWarningTimeout) {
				clearTimeout(projectLinkWarningTimeout);
				projectLinkWarningTimeout = null;
			}

			// Build context_ids if any selected
			const hasContext =
				(selectedContext.meetings?.length ?? 0) > 0 ||
				(selectedContext.actions?.length ?? 0) > 0 ||
				(selectedContext.datasets?.length ?? 0) > 0;

			// Build constraints if any valid
			const validConstraints = constraintItems
				.filter(c => c.description.trim().length >= 5)
				.map(c => ({
					type: c.type,
					description: c.description.trim(),
					value: c.value.trim() || undefined
				}));

			// Create session with optional dataset, context, and constraints
			const sessionData = await apiClient.createSession({
				problem_statement: problemStatement.trim(),
				dataset_id: selectedDatasetId || undefined,
				context_ids: hasContext ? (selectedContext as Record<string, string[]>) : undefined,
				constraints: validConstraints.length > 0 ? validConstraints : undefined,
				...honeypotValues
			});

			const sessionId = sessionData.id;

			// Link selected projects if any
			if (selectedProjectIds.length > 0) {
				try {
					await apiClient.linkProjectsToSession(sessionId, {
						project_ids: selectedProjectIds,
						relationship: 'discusses'
					});
				} catch (projectErr) {
					console.warn('Failed to link projects to session:', projectErr);
					// Non-blocking - show warning but continue with meeting creation
					projectLinkWarning = 'Could not link project(s) to this meeting. You can link them later from the meeting page.';
					// Auto-dismiss after 5 seconds
					projectLinkWarningTimeout = setTimeout(() => {
						projectLinkWarning = null;
					}, 5000);
				}
			}

			// Check for stale insights warning
			if (sessionData.stale_insights && sessionData.stale_insights.length > 0) {
				pendingSessionId = sessionId;
				staleInsights = sessionData.stale_insights as unknown as typeof staleInsights;
				showStalenessWarning = true;
				isSubmitting = false;
				return;
			}

			// No stale insights - proceed immediately
			await startMeeting(sessionId);

		} catch (err) {
			console.error('Failed to create meeting:', err);
			toast.error(err instanceof Error ? err.message : 'Failed to create meeting');
			isSubmitting = false;
		}
	}

	async function startMeeting(sessionId: string) {
		try {
			isSubmitting = true;
			// Start deliberation
			await apiClient.startDeliberation(sessionId);
			// Redirect to meeting view
			goto(`/meeting/${sessionId}`);
		} catch (err) {
			console.error('Failed to start meeting:', err);
			toast.error(err instanceof Error ? err.message : 'Failed to start meeting');
			isSubmitting = false;
		}
	}

	function dismissStalenessWarning() {
		showStalenessWarning = false;
		if (pendingSessionId) {
			startMeeting(pendingSessionId);
		}
	}

	function handleKeyPress(event: KeyboardEvent) {
		// Allow Ctrl+Enter or Cmd+Enter to submit
		if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
			const form = (event.target as HTMLElement).closest('form');
			if (form) form.requestSubmit();
		}
	}

	const examples = [
		"Should we raise a Series A round now or wait 6 months to improve metrics?",
		"What pricing model should we use: subscription, usage-based, or hybrid?",
		"Should we hire a VP of Sales or invest in product-led growth instead?",
		"How should we prioritize: new features for enterprise customers or improving the core product?"
	];

	function useExample(example: string) {
		problemStatement = example;
	}

	function handleContextChange(context: SessionContextIds) {
		selectedContext = context;
	}

	function handleProjectSelectionChange(projectIds: string[]) {
		selectedProjectIds = projectIds;
	}
</script>

<svelte:head>
	<title>New Meeting - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center gap-4">
				<a
					href="/dashboard"
					class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
					aria-label="Back to dashboard"
				>
					<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
					</svg>
				</a>
				<div>
					<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
						Start New Meeting
					</h1>
					<p class="text-sm text-neutral-600 dark:text-neutral-400">
						Describe your strategic decision
					</p>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Context Refresh Banner -->
		<ContextRefreshBanner />

		<!-- Meeting Cap Warning Banner -->
		{#if capStatus?.exceeded}
			<div class="mb-6 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg p-4">
				<div class="flex items-start gap-3">
					<Clock class="w-5 h-5 text-warning-600 dark:text-warning-400 flex-shrink-0 mt-0.5" />
					<div class="flex-1">
						<h3 class="text-sm font-semibold text-warning-900 dark:text-warning-200">
							Meeting limit reached
						</h3>
						<p class="text-sm text-warning-800 dark:text-warning-300 mt-1">
							You've used all {capStatus.limit} meetings in the last 24 hours.
							{#if capStatus.reset_time}
								You can start a new meeting in <strong>{formatResetTime(capStatus.reset_time)}</strong>.
							{/if}
						</p>
						<p class="text-xs text-warning-700 dark:text-warning-400 mt-2">
							During beta, meetings are limited to {capStatus.limit} per 24-hour rolling window to ensure quality for all users.
						</p>
					</div>
				</div>
			</div>
		{:else if capStatus && capStatus.remaining <= 1 && capStatus.limit > 0}
			<div class="mb-6 bg-info-50 dark:bg-info-900/20 border border-info-200 dark:border-info-800 rounded-lg p-3">
				<div class="flex items-center gap-2">
					<Clock class="w-4 h-4 text-info-600 dark:text-info-400 flex-shrink-0" />
					<p class="text-sm text-info-800 dark:text-info-300">
						{capStatus.remaining} meeting{capStatus.remaining === 1 ? '' : 's'} remaining in this 24-hour period.
					</p>
				</div>
			</div>
		{/if}

		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-8">
			<form onsubmit={handleSubmit} class="space-y-6">
				<!-- Honeypot fields for bot detection -->
				<HoneypotFields bind:values={honeypotValues} />

				<!-- Problem Statement Input -->
				<div>
					<label for="problem" class="block text-lg font-semibold text-neutral-900 dark:text-white mb-2">
						What decision do you need help with?
					</label>
					<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
						Be specific about the decision you're facing. Include context like timeframes, constraints, or key considerations.
					</p>
					<textarea
						id="problem"
						bind:value={problemStatement}
						onkeydown={handleKeyPress}
						placeholder="Example: Should we raise a Series A round now or wait 6 months to improve our metrics? Our current burn rate is $200K/month, we have 8 months of runway, and our MRR growth is 15%..."
						rows="8"
						class="w-full px-4 py-3 bg-white dark:bg-neutral-900 border-2 border-neutral-300 dark:border-neutral-600 rounded-lg focus:border-info-500 dark:focus:border-info-400 focus:outline-none text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 transition-colors duration-200"
						required
						minlength="20"
						maxlength="5000"
					></textarea>
					<div class="flex items-center justify-between mt-2">
						<p class="text-xs text-neutral-500 dark:text-neutral-400">
							{problemStatement.length}/5000 characters
							{#if problemStatement.length > 0 && problemStatement.length < 20}
								<span class="text-orange-600 dark:text-orange-400">
									(minimum 20 characters)
								</span>
							{/if}
						</p>
						<p class="text-xs text-neutral-500 dark:text-neutral-400">
							<kbd class="px-2 py-1 bg-neutral-100 dark:bg-neutral-700 rounded text-xs">Ctrl</kbd>
							+
							<kbd class="px-2 py-1 bg-neutral-100 dark:bg-neutral-700 rounded text-xs">Enter</kbd>
							to submit
						</p>
					</div>
				</div>

				<!-- Dataset Selector -->
				{#if datasets.length > 0 || loadingDatasets}
					<div>
						<label for="dataset" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
							Attach Dataset (Optional)
						</label>
						<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-3">
							Include data from your datasets for data-driven analysis.
						</p>
						{#if loadingDatasets}
							<div class="flex items-center gap-2 text-sm text-neutral-500">
								<Spinner size="sm" variant="neutral" ariaLabel="Loading datasets" />
								Loading datasets...
							</div>
						{:else}
							<select
								id="dataset"
								bind:value={selectedDatasetId}
								class="w-full px-4 py-2.5 bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 rounded-lg focus:border-info-500 dark:focus:border-info-400 focus:ring-1 focus:ring-info-500 dark:focus:ring-info-400 focus:outline-none text-neutral-900 dark:text-white transition-colors duration-200"
							>
								<option value={null}>None - Problem-focused deliberation</option>
								{#each datasets as dataset (dataset.id)}
									<option value={dataset.id}>
										{dataset.name}
										{#if dataset.row_count}
											({dataset.row_count.toLocaleString()} rows)
										{/if}
									</option>
								{/each}
							</select>
						{/if}
					</div>
				{/if}

				<!-- Context Selector -->
				<MeetingContextSelector onContextChange={handleContextChange} />

				<!-- Constraints (collapsible) -->
				<div>
					<button
						type="button"
						class="flex items-center gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-neutral-100"
						onclick={() => { showConstraints = !showConstraints; if (showConstraints && constraintItems.length === 0) addConstraint(); }}
					>
						{#if showConstraints}
							<ChevronUp class="w-4 h-4" />
						{:else}
							<ChevronDown class="w-4 h-4" />
						{/if}
						Add Constraints (Optional)
					</button>

					{#if showConstraints}
						<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-2 mb-3">
							Set boundaries for the deliberation — budget limits, deadlines, regulatory requirements, etc.
						</p>
						<div class="space-y-2">
							{#each constraintItems as constraint, i (i)}
								<div class="flex gap-2 items-start">
									<select
										bind:value={constraint.type}
										class="w-28 flex-shrink-0 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-2 py-2 text-sm"
									>
										{#each CONSTRAINT_TYPES as t (t)}
											<option value={t}>{t}</option>
										{/each}
									</select>
									<input
										type="text"
										bind:value={constraint.description}
										placeholder="e.g., Total budget must not exceed $500K"
										class="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm"
									/>
									<input
										type="text"
										bind:value={constraint.value}
										placeholder="Value"
										class="w-24 flex-shrink-0 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm"
									/>
									<button
										type="button"
										class="flex-shrink-0 p-2 text-neutral-400 hover:text-error-500"
										onclick={() => removeConstraint(i)}
									>
										<X class="w-4 h-4" />
									</button>
								</div>
							{/each}
						</div>
						{#if constraintItems.length < 10}
							<button
								type="button"
								class="mt-2 inline-flex items-center gap-1 text-sm text-info-600 dark:text-info-400 hover:text-info-700 dark:hover:text-info-300"
								onclick={addConstraint}
							>
								<Plus class="w-4 h-4" />
								Add another constraint
							</button>
						{/if}
					{/if}
				</div>

				<!-- Project Selector -->
				<div>
					<span class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
						Link to Projects (Optional)
					</span>
					<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-3">
						Connect this meeting to existing projects for better organization.
					</p>
					<MeetingProjectSelector
						selectedProjectIds={selectedProjectIds}
						onSelectionChange={handleProjectSelectionChange}
					/>
				</div>

				<!-- Examples -->
				<div class="bg-neutral-50 dark:bg-neutral-900/50 rounded-lg p-4">
					<h3 class="text-sm font-semibold text-neutral-900 dark:text-white mb-3">
						Need inspiration? Try one of these examples:
					</h3>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
						{#each examples as example, i (i)}
							<button
								type="button"
								onclick={() => useExample(example)}
								class="text-left p-3 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:border-info-400 dark:hover:border-info-600 hover:shadow-sm transition-all duration-200 text-sm text-neutral-700 dark:text-neutral-300"
							>
								"{example.substring(0, 80)}{example.length > 80 ? '...' : ''}"
							</button>
						{/each}
					</div>
				</div>

				<!-- Project Link Warning -->
				{#if projectLinkWarning}
					<div class="bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg p-4">
						<div class="flex items-center justify-between gap-2">
							<div class="flex items-center gap-2">
								<AlertTriangle class="w-5 h-5 text-warning-600 dark:text-warning-400 flex-shrink-0" />
								<p class="text-sm text-warning-900 dark:text-warning-200">
									{projectLinkWarning}
								</p>
							</div>
							<button
								type="button"
								onclick={() => { projectLinkWarning = null; }}
								class="p-1 hover:bg-warning-100 dark:hover:bg-warning-900/30 rounded transition-colors"
								aria-label="Dismiss warning"
							>
								<X class="w-4 h-4 text-warning-600 dark:text-warning-400" />
							</button>
						</div>
					</div>
				{/if}

				<!-- Error Message -->
				{#if error}
					<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4">
						<div class="flex items-center gap-2">
							<svg class="w-5 h-5 text-error-600 dark:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<p class="text-sm text-error-900 dark:text-error-200">
								{error}
							</p>
						</div>
					</div>
				{/if}

				<!-- Submit Button -->
				<div class="flex items-center gap-4">
					<button
						type="submit"
						disabled={isSubmitting || problemStatement.trim().length < 20 || capStatus?.exceeded}
						class="flex-1 px-6 py-3 bg-info-600 hover:bg-info-700 disabled:bg-neutral-300 dark:disabled:bg-neutral-700 text-white font-medium rounded-lg transition-colors duration-200 disabled:cursor-not-allowed flex items-center justify-center gap-2"
					>
						{#if isSubmitting}
							<Spinner size="sm" variant="neutral" ariaLabel="Starting meeting" />
							Starting meeting...
						{:else if capStatus?.exceeded}
							<Clock class="w-5 h-5" />
							Limit Reached
						{:else}
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
							</svg>
							Start Meeting
						{/if}
					</button>

					<a
						href="/dashboard"
						class="px-6 py-3 bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 font-medium rounded-lg transition-colors duration-200"
					>
						Cancel
					</a>
				</div>

				<!-- Info Box -->
				<div class="bg-info-50 dark:bg-info-900/20 border border-info-200 dark:border-info-800 rounded-lg p-4">
					<div class="flex gap-3">
						<svg class="w-5 h-5 text-info-600 dark:text-info-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						<div class="text-sm text-info-900 dark:text-info-200">
							<p class="font-semibold mb-1">What happens next?</p>
							<ul class="list-disc list-inside space-y-1 text-info-800 dark:text-info-300">
								<li>Your decision will be analyzed and broken down into key focus areas</li>
								<li>3-5 expert personas will be selected to debate your decision</li>
								<li>Multiple rounds of deliberation will identify trade-offs and blind spots</li>
								<li>A clear recommendation with action steps will be synthesized</li>
							</ul>
							<p class="mt-2 text-xs text-info-700 dark:text-info-400">
								Average deliberation time: 5-15 minutes
							</p>
						</div>
					</div>
				</div>
			</form>
		</div>
	</main>
</div>

<!-- Staleness Warning Modal -->
{#if showStalenessWarning}
	<div
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
		role="dialog"
		aria-modal="true"
		aria-labelledby="staleness-warning-title"
		tabindex="-1"
		onkeydown={(e) => e.key === 'Escape' && dismissStalenessWarning()}
	>
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-lg w-full p-6">
			<div class="flex items-start gap-4 mb-4">
				<div class="flex-shrink-0 p-2 bg-warning-100 dark:bg-warning-900/30 rounded-full">
					<svg class="w-6 h-6 text-warning-600 dark:text-warning-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
					</svg>
				</div>
				<div>
					<h3 id="staleness-warning-title" class="text-lg font-semibold text-neutral-900 dark:text-white">
						Some of your insights may be outdated
					</h3>
					<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
						The following insights haven't been updated in over 30 days. Refreshing them may improve your meeting's recommendations.
					</p>
				</div>
			</div>

			<div class="bg-neutral-50 dark:bg-neutral-900/50 rounded-lg p-4 mb-4 max-h-48 overflow-y-auto">
				<ul class="space-y-2">
					{#each staleInsights as insight (insight.question)}
						<li class="flex items-start gap-2 text-sm">
							<span class="text-warning-500 mt-0.5">•</span>
							<div>
								<p class="text-neutral-700 dark:text-neutral-300">{insight.question}</p>
								<p class="text-xs text-neutral-500 dark:text-neutral-400">
									{insight.days_stale} days since last update
								</p>
							</div>
						</li>
					{/each}
				</ul>
			</div>

			<div class="flex flex-col sm:flex-row gap-3">
				<a
					href="/context/insights"
					class="flex-1 px-4 py-2 bg-warning-100 hover:bg-warning-200 dark:bg-warning-900/30 dark:hover:bg-warning-900/50 text-warning-800 dark:text-warning-200 font-medium rounded-lg transition-colors duration-200 text-center"
				>
					Update Insights
				</a>
				<button
					onclick={dismissStalenessWarning}
					disabled={isSubmitting}
					class="flex-1 px-4 py-2 bg-info-600 hover:bg-info-700 disabled:bg-neutral-300 dark:disabled:bg-neutral-700 text-white font-medium rounded-lg transition-colors duration-200 flex items-center justify-center gap-2"
				>
					{#if isSubmitting}
						<Spinner size="sm" variant="neutral" ariaLabel="Starting meeting" />
						Starting...
					{:else}
						Continue Anyway
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
