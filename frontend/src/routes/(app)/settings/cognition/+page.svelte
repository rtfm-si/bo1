<script lang="ts">
	/**
	 * Cognition Settings Page
	 *
	 * Displays cognitive profile and allows retaking assessment.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type {
		CognitionProfileResponse,
		CognitionBlindspot,
		LiteCognitionAssessmentRequest
	} from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import CognitionQuestionFlow from '$lib/components/cognition/CognitionQuestionFlow.svelte';
	import Tier2AssessmentFlow from '$lib/components/cognition/Tier2AssessmentFlow.svelte';

	type Tier2Instrument = 'leverage' | 'tension' | 'time_bias';

	// State
	let profile = $state<CognitionProfileResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let showAssessmentModal = $state(false);
	let showTier2Modal = $state(false);
	let selectedTier2Instrument = $state<Tier2Instrument>('leverage');
	let isSaving = $state(false);

	// Computed
	const hasProfile = $derived(profile?.exists && profile?.gravity?.assessed_at);
	const tier1Complete = $derived(
		hasProfile &&
			profile?.gravity?.assessed_at &&
			profile?.friction?.assessed_at &&
			profile?.uncertainty?.assessed_at
	);
	const tier2Unlocked = $derived(profile?.tier2_unlocked ?? false);
	const leverageAssessed = $derived(!!profile?.leverage?.assessed_at);
	const tensionAssessed = $derived(!!profile?.tension?.assessed_at);
	const timeBiasAssessed = $derived(!!profile?.time_bias?.assessed_at);
	const allTier2Complete = $derived(leverageAssessed && tensionAssessed && timeBiasAssessed);

	onMount(async () => {
		await loadProfile();
	});

	async function loadProfile() {
		isLoading = true;
		error = null;
		try {
			profile = await apiClient.getCognitionProfile();
		} catch (e) {
			error = 'Failed to load cognitive profile';
			console.error(e);
		} finally {
			isLoading = false;
		}
	}

	async function handleAssessmentComplete(responses: Record<string, number>) {
		isSaving = true;
		try {
			await apiClient.submitLiteCognitionAssessment(
				responses as unknown as LiteCognitionAssessmentRequest
			);
			showAssessmentModal = false;
			await loadProfile();
		} catch (e) {
			console.error('Failed to save assessment:', e);
			error = 'Failed to save assessment';
		} finally {
			isSaving = false;
		}
	}

	function openTier2Assessment(instrument: Tier2Instrument) {
		selectedTier2Instrument = instrument;
		showTier2Modal = true;
	}

	async function handleTier2Complete(instrument: Tier2Instrument, responses: Record<string, number>) {
		isSaving = true;
		try {
			await apiClient.submitTier2CognitionAssessment(instrument, responses);
			showTier2Modal = false;
			await loadProfile();
		} catch (e) {
			console.error('Failed to save Tier 2 assessment:', e);
			error = 'Failed to save assessment';
		} finally {
			isSaving = false;
		}
	}

	function getTier2DimensionLabel(key: string, value: number | null | undefined): string {
		if (value === null || value === undefined) return 'Not assessed';

		// For tension values (-1 to 1 scale)
		if (key.startsWith('tension_')) {
			const labels: Record<string, [string, string]> = {
				autonomy_security: ['Values autonomy', 'Values security'],
				mastery_speed: ['Prioritizes mastery', 'Prioritizes speed'],
				growth_stability: ['Growth-oriented', 'Stability-oriented']
			};
			const shortKey = key.replace('tension_', '');
			const [low, high] = labels[shortKey] || ['Low', 'High'];
			if (value < -0.3) return low;
			if (value > 0.3) return high;
			return 'Balanced';
		}

		// For 0-1 scale values
		if (value < 0.35) return 'Low';
		if (value > 0.65) return 'High';
		return 'Moderate';
	}

	function formatDimension(value: number | null | undefined): string {
		if (value === null || value === undefined) return 'Not assessed';
		const percent = Math.round(value * 100);
		return `${percent}%`;
	}

	function getDimensionLabel(key: string, value: number | null | undefined): string {
		if (value === null || value === undefined) return 'Not assessed';

		const labels: Record<string, [string, string]> = {
			time_horizon: ['Short-term focused', 'Long-term strategic'],
			information_density: ['Big-picture', 'Detail-oriented'],
			control_style: ['Delegator', 'Hands-on'],
			risk_sensitivity: ['Risk-tolerant', 'Risk-averse'],
			cognitive_load: ['Thrives on complexity', 'Prefers simplicity'],
			ambiguity_tolerance: ['Ambiguity-tolerant', 'Clarity-seeking'],
			threat_lens: ['Opportunity-focused', 'Risk-focused'],
			control_need: ['Flexible', 'Structured'],
			exploration_drive: ['Optimizer', 'Explorer']
		};

		const [low, high] = labels[key] || ['Low', 'High'];
		if (value < 0.35) return low;
		if (value > 0.65) return high;
		return 'Balanced';
	}
</script>

<div class="space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h2 class="text-xl font-semibold text-slate-900 dark:text-white">Cognitive Profile</h2>
			<p class="text-sm text-slate-600 dark:text-slate-400 mt-1">
				How you think and decide, used to personalize your recommendations
			</p>
		</div>
		{#if hasProfile}
			<Button variant="secondary" onclick={() => (showAssessmentModal = true)}>
				Retake Assessment
			</Button>
		{/if}
	</div>

	{#if isLoading}
		<!-- Loading state -->
		<div class="bg-white dark:bg-slate-800 rounded-xl p-8 border border-slate-200 dark:border-slate-700">
			<div class="flex items-center justify-center gap-3 text-slate-500">
				<svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
					></circle>
					<path
						class="opacity-75"
						fill="currentColor"
						d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
					></path>
				</svg>
				<span>Loading profile...</span>
			</div>
		</div>
	{:else if error}
		<!-- Error state -->
		<div
			class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6"
		>
			<p class="text-red-700 dark:text-red-300">{error}</p>
			<Button variant="secondary" onclick={loadProfile} class="mt-4">Retry</Button>
		</div>
	{:else if !hasProfile}
		<!-- No profile - show CTA to take assessment -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl p-8 border border-slate-200 dark:border-slate-700 text-center"
		>
			<div
				class="w-16 h-16 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center mx-auto mb-4"
			>
				<span class="text-3xl">🧠</span>
			</div>
			<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-2">
				Discover Your Decision Style
			</h3>
			<p class="text-slate-600 dark:text-slate-400 mb-6 max-w-md mx-auto">
				Take a 90-second assessment to help us personalize recommendations to how you think and
				decide.
			</p>
			<Button variant="brand" onclick={() => (showAssessmentModal = true)}>
				Start Assessment
			</Button>
		</div>
	{:else}
		<!-- Profile display -->
		<div class="space-y-6">
			<!-- Style Summary -->
			{#if profile?.cognitive_style_summary}
				<div
					class="bg-gradient-to-r from-brand-50 to-purple-50 dark:from-brand-900/20 dark:to-purple-900/20 rounded-xl p-6 border border-brand-200 dark:border-brand-800"
				>
					<div class="flex items-start gap-4">
						<div
							class="w-12 h-12 bg-white dark:bg-slate-800 rounded-lg flex items-center justify-center flex-shrink-0"
						>
							<span class="text-2xl">🧠</span>
						</div>
						<div>
							<h3 class="font-medium text-slate-900 dark:text-white mb-1">Your Decision Style</h3>
							<p class="text-slate-700 dark:text-slate-300">{profile.cognitive_style_summary}</p>
						</div>
					</div>
				</div>
			{/if}

			<!-- Blindspots -->
			{#if profile?.primary_blindspots && profile.primary_blindspots.length > 0}
				<div
					class="bg-amber-50 dark:bg-amber-900/20 rounded-xl p-6 border border-amber-200 dark:border-amber-800"
				>
					<h3 class="font-medium text-amber-800 dark:text-amber-200 mb-3 flex items-center gap-2">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
							/>
						</svg>
						Blindspot Awareness
					</h3>
					<p class="text-sm text-amber-700 dark:text-amber-300 mb-4">
						These are areas where your natural tendencies may create blind spots. Our
						recommendations will actively address these.
					</p>
					<div class="space-y-3">
						{#each profile.primary_blindspots as blindspot}
							<div class="bg-white dark:bg-slate-800 rounded-lg p-4">
								<h4 class="font-medium text-slate-900 dark:text-white">{blindspot.label}</h4>
								<p class="text-sm text-slate-600 dark:text-slate-400 mt-1">
									{blindspot.compensation}
								</p>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Dimension Details -->
			<div class="grid gap-6 md:grid-cols-3">
				<!-- Cognitive Gravity -->
				<div
					class="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700"
				>
					<h3 class="font-medium text-slate-900 dark:text-white mb-4 flex items-center gap-2">
						<span class="text-lg">🎯</span>
						Decision Style
					</h3>
					<div class="space-y-4">
						<div>
							<div class="flex justify-between text-sm mb-1">
								<span class="text-slate-600 dark:text-slate-400">Time Horizon</span>
								<span class="font-medium text-slate-900 dark:text-white">
									{getDimensionLabel('time_horizon', profile?.gravity?.time_horizon)}
								</span>
							</div>
							<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full">
								<div
									class="h-full bg-brand-500 rounded-full transition-all"
									style="width: {(profile?.gravity?.time_horizon ?? 0.5) * 100}%"
								></div>
							</div>
						</div>
						<div>
							<div class="flex justify-between text-sm mb-1">
								<span class="text-slate-600 dark:text-slate-400">Information Preference</span>
								<span class="font-medium text-slate-900 dark:text-white">
									{getDimensionLabel('information_density', profile?.gravity?.information_density)}
								</span>
							</div>
							<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full">
								<div
									class="h-full bg-brand-500 rounded-full transition-all"
									style="width: {(profile?.gravity?.information_density ?? 0.5) * 100}%"
								></div>
							</div>
						</div>
						<div>
							<div class="flex justify-between text-sm mb-1">
								<span class="text-slate-600 dark:text-slate-400">Control Style</span>
								<span class="font-medium text-slate-900 dark:text-white">
									{getDimensionLabel('control_style', profile?.gravity?.control_style)}
								</span>
							</div>
							<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full">
								<div
									class="h-full bg-brand-500 rounded-full transition-all"
									style="width: {(profile?.gravity?.control_style ?? 0.5) * 100}%"
								></div>
							</div>
						</div>
					</div>
				</div>

				<!-- Decision Friction -->
				<div
					class="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700"
				>
					<h3 class="font-medium text-slate-900 dark:text-white mb-4 flex items-center gap-2">
						<span class="text-lg">⚡</span>
						Decision Friction
					</h3>
					<div class="space-y-4">
						<div>
							<div class="flex justify-between text-sm mb-1">
								<span class="text-slate-600 dark:text-slate-400">Risk Sensitivity</span>
								<span class="font-medium text-slate-900 dark:text-white">
									{getDimensionLabel('risk_sensitivity', profile?.friction?.risk_sensitivity)}
								</span>
							</div>
							<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full">
								<div
									class="h-full bg-purple-500 rounded-full transition-all"
									style="width: {(profile?.friction?.risk_sensitivity ?? 0.5) * 100}%"
								></div>
							</div>
						</div>
						<div>
							<div class="flex justify-between text-sm mb-1">
								<span class="text-slate-600 dark:text-slate-400">Complexity Handling</span>
								<span class="font-medium text-slate-900 dark:text-white">
									{getDimensionLabel('cognitive_load', profile?.friction?.cognitive_load)}
								</span>
							</div>
							<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full">
								<div
									class="h-full bg-purple-500 rounded-full transition-all"
									style="width: {(profile?.friction?.cognitive_load ?? 0.5) * 100}%"
								></div>
							</div>
						</div>
						<div>
							<div class="flex justify-between text-sm mb-1">
								<span class="text-slate-600 dark:text-slate-400">Ambiguity Tolerance</span>
								<span class="font-medium text-slate-900 dark:text-white">
									{getDimensionLabel('ambiguity_tolerance', profile?.friction?.ambiguity_tolerance)}
								</span>
							</div>
							<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full">
								<div
									class="h-full bg-purple-500 rounded-full transition-all"
									style="width: {(profile?.friction?.ambiguity_tolerance ?? 0.5) * 100}%"
								></div>
							</div>
						</div>
					</div>
				</div>

				<!-- Uncertainty Posture -->
				<div
					class="bg-white dark:bg-slate-800 rounded-xl p-6 border border-slate-200 dark:border-slate-700"
				>
					<h3 class="font-medium text-slate-900 dark:text-white mb-4 flex items-center gap-2">
						<span class="text-lg">🔮</span>
						Uncertainty Response
					</h3>
					<div class="space-y-4">
						<div>
							<div class="flex justify-between text-sm mb-1">
								<span class="text-slate-600 dark:text-slate-400">Threat Lens</span>
								<span class="font-medium text-slate-900 dark:text-white">
									{getDimensionLabel('threat_lens', profile?.uncertainty?.threat_lens)}
								</span>
							</div>
							<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full">
								<div
									class="h-full bg-teal-500 rounded-full transition-all"
									style="width: {(profile?.uncertainty?.threat_lens ?? 0.5) * 100}%"
								></div>
							</div>
						</div>
						<div>
							<div class="flex justify-between text-sm mb-1">
								<span class="text-slate-600 dark:text-slate-400">Structure Need</span>
								<span class="font-medium text-slate-900 dark:text-white">
									{getDimensionLabel('control_need', profile?.uncertainty?.control_need)}
								</span>
							</div>
							<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full">
								<div
									class="h-full bg-teal-500 rounded-full transition-all"
									style="width: {(profile?.uncertainty?.control_need ?? 0.5) * 100}%"
								></div>
							</div>
						</div>
						<div>
							<div class="flex justify-between text-sm mb-1">
								<span class="text-slate-600 dark:text-slate-400">Exploration Drive</span>
								<span class="font-medium text-slate-900 dark:text-white">
									{getDimensionLabel('exploration_drive', profile?.uncertainty?.exploration_drive)}
								</span>
							</div>
							<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full">
								<div
									class="h-full bg-teal-500 rounded-full transition-all"
									style="width: {(profile?.uncertainty?.exploration_drive ?? 0.5) * 100}%"
								></div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Tier 2 Unlock Banner (shown when close to unlock or just unlocked) -->
			{#if profile?.unlock_prompt?.show && !allTier2Complete}
				<div
					class="bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-xl p-6 border border-indigo-200 dark:border-indigo-800"
				>
					<div class="flex items-center gap-4">
						<div
							class="w-12 h-12 bg-indigo-100 dark:bg-indigo-900/50 rounded-lg flex items-center justify-center flex-shrink-0"
						>
							<span class="text-2xl">🔓</span>
						</div>
						<div class="flex-1">
							<h3 class="font-medium text-indigo-900 dark:text-indigo-100">
								{profile.unlock_prompt.message}
							</h3>
							{#if profile.unlock_prompt.meetings_remaining > 0}
								<p class="text-sm text-indigo-700 dark:text-indigo-300 mt-1">
									{profile.unlock_prompt.meetings_remaining} meeting{profile.unlock_prompt
										.meetings_remaining > 1
										? 's'
										: ''} to go
								</p>
							{/if}
						</div>
					</div>
				</div>
			{/if}

			<!-- Tier 2: Advanced Profiling (shown when unlocked) -->
			{#if tier2Unlocked}
				<div class="space-y-4">
					<div class="flex items-center justify-between">
						<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
							Advanced Profiling
						</h3>
						{#if allTier2Complete}
							<span class="text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full">
								Complete
							</span>
						{/if}
					</div>

					<div class="grid gap-4 md:grid-cols-3">
						<!-- Leverage Instinct -->
						<div
							class="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700"
						>
							<div class="flex items-center justify-between mb-3">
								<h4 class="font-medium text-slate-900 dark:text-white flex items-center gap-2">
									<span class="text-lg">💪</span>
									Leverage Style
								</h4>
								{#if !leverageAssessed}
									<button
										onclick={() => openTier2Assessment('leverage')}
										class="text-xs px-2 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-full hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors"
									>
										Take Assessment
									</button>
								{/if}
							</div>
							{#if leverageAssessed}
								<div class="space-y-2 text-sm">
									<div class="flex justify-between">
										<span class="text-slate-600 dark:text-slate-400">Systems</span>
										<span class="text-slate-900 dark:text-white">{getTier2DimensionLabel('structural', profile?.leverage?.structural)}</span>
									</div>
									<div class="flex justify-between">
										<span class="text-slate-600 dark:text-slate-400">Data</span>
										<span class="text-slate-900 dark:text-white">{getTier2DimensionLabel('informational', profile?.leverage?.informational)}</span>
									</div>
									<div class="flex justify-between">
										<span class="text-slate-600 dark:text-slate-400">Networks</span>
										<span class="text-slate-900 dark:text-white">{getTier2DimensionLabel('relational', profile?.leverage?.relational)}</span>
									</div>
									<div class="flex justify-between">
										<span class="text-slate-600 dark:text-slate-400">Timing</span>
										<span class="text-slate-900 dark:text-white">{getTier2DimensionLabel('temporal', profile?.leverage?.temporal)}</span>
									</div>
								</div>
								<button
									onclick={() => openTier2Assessment('leverage')}
									class="mt-3 text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
								>
									Retake
								</button>
							{:else}
								<p class="text-sm text-slate-500 dark:text-slate-400">
									How you naturally create power and influence
								</p>
							{/if}
						</div>

						<!-- Value Tensions -->
						<div
							class="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700"
						>
							<div class="flex items-center justify-between mb-3">
								<h4 class="font-medium text-slate-900 dark:text-white flex items-center gap-2">
									<span class="text-lg">⚖️</span>
									Value Tensions
								</h4>
								{#if !tensionAssessed}
									<button
										onclick={() => openTier2Assessment('tension')}
										class="text-xs px-2 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-full hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors"
									>
										Take Assessment
									</button>
								{/if}
							</div>
							{#if tensionAssessed}
								<div class="space-y-2 text-sm">
									<div class="flex justify-between">
										<span class="text-slate-600 dark:text-slate-400">Autonomy/Security</span>
										<span class="text-slate-900 dark:text-white">{getTier2DimensionLabel('tension_autonomy_security', profile?.tension?.autonomy_security)}</span>
									</div>
									<div class="flex justify-between">
										<span class="text-slate-600 dark:text-slate-400">Mastery/Speed</span>
										<span class="text-slate-900 dark:text-white">{getTier2DimensionLabel('tension_mastery_speed', profile?.tension?.mastery_speed)}</span>
									</div>
									<div class="flex justify-between">
										<span class="text-slate-600 dark:text-slate-400">Growth/Stability</span>
										<span class="text-slate-900 dark:text-white">{getTier2DimensionLabel('tension_growth_stability', profile?.tension?.growth_stability)}</span>
									</div>
								</div>
								<button
									onclick={() => openTier2Assessment('tension')}
									class="mt-3 text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
								>
									Retake
								</button>
							{:else}
								<p class="text-sm text-slate-500 dark:text-slate-400">
									Your competing priorities and trade-offs
								</p>
							{/if}
						</div>

						<!-- Time Orientation -->
						<div
							class="bg-white dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700"
						>
							<div class="flex items-center justify-between mb-3">
								<h4 class="font-medium text-slate-900 dark:text-white flex items-center gap-2">
									<span class="text-lg">⏳</span>
									Time Orientation
								</h4>
								{#if !timeBiasAssessed}
									<button
										onclick={() => openTier2Assessment('time_bias')}
										class="text-xs px-2 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-full hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors"
									>
										Take Assessment
									</button>
								{/if}
							</div>
							{#if timeBiasAssessed}
								<div class="space-y-2 text-sm">
									<div class="flex justify-between">
										<span class="text-slate-600 dark:text-slate-400">Time Bias</span>
										<span class="text-slate-900 dark:text-white">
											{#if (profile?.time_bias?.score ?? 0.5) < 0.35}
												Short-term optimizer
											{:else if (profile?.time_bias?.score ?? 0.5) > 0.65}
												Long-term strategist
											{:else}
												Balanced horizon
											{/if}
										</span>
									</div>
								</div>
								<button
									onclick={() => openTier2Assessment('time_bias')}
									class="mt-3 text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
								>
									Retake
								</button>
							{:else}
								<p class="text-sm text-slate-500 dark:text-slate-400">
									Short-term vs long-term orientation
								</p>
							{/if}
						</div>
					</div>
				</div>
			{/if}

			<!-- Meeting count -->
			<div class="text-sm text-slate-500 dark:text-slate-400">
				Based on {profile?.completed_meetings_count || 0} completed meetings
			</div>
		</div>
	{/if}
</div>

<!-- Assessment Modal -->
<Modal bind:open={showAssessmentModal} title="Cognitive Assessment" size="lg">
	<div class="py-4">
		<CognitionQuestionFlow
			onComplete={handleAssessmentComplete}
			onCancel={() => (showAssessmentModal = false)}
		/>
	</div>
</Modal>

<!-- Tier 2 Assessment Modal -->
<Modal
	bind:open={showTier2Modal}
	title={selectedTier2Instrument === 'leverage'
		? 'Leverage Instinct Assessment'
		: selectedTier2Instrument === 'tension'
			? 'Value Tensions Assessment'
			: 'Time Orientation Assessment'}
	size="lg"
>
	<div class="py-4">
		<Tier2AssessmentFlow
			instrument={selectedTier2Instrument}
			onComplete={handleTier2Complete}
			onCancel={() => (showTier2Modal = false)}
		/>
	</div>
</Modal>
