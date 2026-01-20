<script lang="ts">
	/**
	 * Cognition Page - Primary assessment experience
	 *
	 * Two modes:
	 * - No profile: Full-page assessment flow
	 * - Has profile: Summary card with retake option
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { CognitionProfileResponse, LiteCognitionAssessmentRequest } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import CognitionQuestionFlow from '$lib/components/cognition/CognitionQuestionFlow.svelte';

	// State
	let profile = $state<CognitionProfileResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let isSaving = $state(false);
	let showRetakeFlow = $state(false);
	let showSuccess = $state(false);

	// Computed
	const hasProfile = $derived(profile?.exists && profile?.gravity?.assessed_at);

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
			showRetakeFlow = false;
			showSuccess = true;
			await loadProfile();
		} catch (e) {
			console.error('Failed to save assessment:', e);
			error = 'Failed to save assessment';
		} finally {
			isSaving = false;
		}
	}

	function startRetake() {
		showRetakeFlow = true;
		showSuccess = false;
	}

	function cancelRetake() {
		showRetakeFlow = false;
	}
</script>

<div class="max-w-3xl mx-auto py-8 px-4">
	{#if isLoading}
		<!-- Loading state -->
		<div class="flex items-center justify-center gap-3 text-slate-500 py-16">
			<svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
				></circle>
				<path
					class="opacity-75"
					fill="currentColor"
					d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
				></path>
			</svg>
			<span>Loading...</span>
		</div>
	{:else if error && !hasProfile}
		<!-- Error state -->
		<div
			class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6"
		>
			<p class="text-red-700 dark:text-red-300">{error}</p>
			<Button variant="secondary" onclick={loadProfile} class="mt-4">Retry</Button>
		</div>
	{:else if !hasProfile || showRetakeFlow}
		<!-- Assessment flow (full page, not modal) -->
		<div class="text-center mb-8">
			<div
				class="w-16 h-16 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center mx-auto mb-4"
			>
				<span class="text-3xl">🧠</span>
			</div>
			<h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">
				{showRetakeFlow ? 'Retake Your Assessment' : 'Discover Your Decision Style'}
			</h1>
			<p class="text-slate-600 dark:text-slate-400 max-w-md mx-auto">
				Answer 9 quick questions to help us personalize recommendations to how you think and decide.
			</p>
		</div>

		<CognitionQuestionFlow
			onComplete={handleAssessmentComplete}
			onCancel={showRetakeFlow ? cancelRetake : undefined}
		/>
	{:else if showSuccess}
		<!-- Success state after completing assessment -->
		<div class="text-center py-12">
			<div
				class="w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-6"
			>
				<svg class="w-10 h-10 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
				</svg>
			</div>
			<h2 class="text-2xl font-bold text-slate-900 dark:text-white mb-3">
				Profile Updated!
			</h2>
			<p class="text-slate-600 dark:text-slate-400 mb-8 max-w-md mx-auto">
				Your cognitive profile has been saved. We'll use this to personalize your meeting recommendations.
			</p>

			{#if profile?.cognitive_style_summary}
				<div
					class="bg-gradient-to-r from-brand-50 to-purple-50 dark:from-brand-900/20 dark:to-purple-900/20 rounded-xl p-6 border border-brand-200 dark:border-brand-800 text-left max-w-lg mx-auto mb-8"
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

			<div class="flex flex-col sm:flex-row gap-3 justify-center">
				<Button variant="brand" href="/meeting/new">
					Start a Meeting
				</Button>
				<Button variant="secondary" href="/settings/cognition">
					View Full Profile
				</Button>
			</div>
		</div>
	{:else}
		<!-- Has profile - show summary -->
		<div class="space-y-6">
			<div class="text-center mb-8">
				<h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">
					Your Cognitive Profile
				</h1>
				<p class="text-slate-600 dark:text-slate-400">
					How you think and decide, used to personalize your recommendations
				</p>
			</div>

			<!-- Style Summary Card -->
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

			<!-- Blindspots Preview -->
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
					<p class="text-sm text-amber-700 dark:text-amber-300 mb-3">
						Areas where your natural tendencies may create blind spots.
					</p>
					<div class="space-y-2">
						{#each profile.primary_blindspots.slice(0, 2) as blindspot (blindspot.label)}
							<div class="bg-white dark:bg-slate-800 rounded-lg p-3">
								<span class="font-medium text-slate-900 dark:text-white">{blindspot.label}</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Actions -->
			<div class="flex flex-col sm:flex-row gap-3 justify-center pt-4">
				<Button variant="brand" onclick={startRetake}>
					Retake Assessment
				</Button>
				<Button variant="secondary" href="/settings/cognition">
					View Full Details
				</Button>
			</div>
		</div>
	{/if}
</div>
