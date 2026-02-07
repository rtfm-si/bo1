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
	import type { CognitionProfileResponse, LiteCognitionAssessmentRequest, CognitionBlindspot } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import CognitionQuestionFlow from '$lib/components/cognition/CognitionQuestionFlow.svelte';
	import { MessageCircle } from 'lucide-svelte';

	// State
	let profile = $state<CognitionProfileResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let isSaving = $state(false);
	let showRetakeFlow = $state(false);
	let showSuccess = $state(false);
	let discussionCounts = $state<Record<string, number>>({});

	// Computed
	const hasProfile = $derived(profile?.exists && profile?.gravity?.assessed_at);

	// Generate blindspot discussion URL
	function getBlindspotDiscussUrl(blindspot: CognitionBlindspot): string {
		const message = encodeURIComponent(
			`I'd like to discuss my "${blindspot.label}" blindspot. ${blindspot.compensation}\n\nCan you help me understand this better and suggest strategies to address it?`
		);
		const blindspotId = blindspot.label.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
		return `/advisor/discuss?message=${message}&blindspot_id=${blindspotId}`;
	}

	// Get blindspot ID from label
	function getBlindspotId(label: string): string {
		return label.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
	}

	// Load discussion counts for blindspots
	async function loadDiscussionCounts() {
		if (!profile?.primary_blindspots?.length) return;

		for (const blindspot of profile.primary_blindspots) {
			const blindspotId = getBlindspotId(blindspot.label);
			try {
				const resp = await apiClient.getBlindspotDiscussions(blindspotId, 1);
				discussionCounts[blindspotId] = resp.total;
			} catch {
				// Ignore errors
			}
		}
	}

	onMount(async () => {
		await loadProfile();
	});

	async function loadProfile() {
		isLoading = true;
		error = null;
		try {
			profile = await apiClient.getCognitionProfile();
			// Load discussion counts after profile is loaded
			await loadDiscussionCounts();
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
		<div class="flex items-center justify-center gap-3 text-neutral-500 py-16">
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
			class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-xl p-6"
		>
			<p class="text-error-700 dark:text-error-300">{error}</p>
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
			<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-2">
				{showRetakeFlow ? 'Retake Your Assessment' : 'Discover Your Decision Style'}
			</h1>
			<p class="text-neutral-600 dark:text-neutral-400 max-w-md mx-auto">
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
				class="w-20 h-20 bg-success-100 dark:bg-success-900/30 rounded-full flex items-center justify-center mx-auto mb-6"
			>
				<svg class="w-10 h-10 text-success-600 dark:text-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
				</svg>
			</div>
			<h2 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-3">
				Profile Updated!
			</h2>
			<p class="text-neutral-600 dark:text-neutral-400 mb-8 max-w-md mx-auto">
				Your cognitive profile has been saved. We'll use this to personalize your meeting recommendations.
			</p>

			{#if profile?.cognitive_style_summary}
				<div
					class="bg-gradient-to-r from-brand-50 to-purple-50 dark:from-brand-900/20 dark:to-purple-900/20 rounded-xl p-6 border border-brand-200 dark:border-brand-800 text-left max-w-lg mx-auto mb-8"
				>
					<div class="flex items-start gap-4">
						<div
							class="w-12 h-12 bg-white dark:bg-neutral-800 rounded-lg flex items-center justify-center flex-shrink-0"
						>
							<span class="text-2xl">🧠</span>
						</div>
						<div>
							<h3 class="font-medium text-neutral-900 dark:text-white mb-1">Your Decision Style</h3>
							<p class="text-neutral-700 dark:text-neutral-300">{profile.cognitive_style_summary}</p>
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
				<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-2">
					Your Cognitive Profile
				</h1>
				<p class="text-neutral-600 dark:text-neutral-400">
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
							class="w-12 h-12 bg-white dark:bg-neutral-800 rounded-lg flex items-center justify-center flex-shrink-0"
						>
							<span class="text-2xl">🧠</span>
						</div>
						<div>
							<h3 class="font-medium text-neutral-900 dark:text-white mb-1">Your Decision Style</h3>
							<p class="text-neutral-700 dark:text-neutral-300">{profile.cognitive_style_summary}</p>
						</div>
					</div>
				</div>
			{/if}

			<!-- Blindspots Preview -->
			{#if profile?.primary_blindspots && profile.primary_blindspots.length > 0}
				<div
					class="bg-warning-50 dark:bg-warning-900/20 rounded-xl p-6 border border-warning-200 dark:border-warning-800"
				>
					<h3 class="font-medium text-warning-800 dark:text-warning-200 mb-3 flex items-center gap-2">
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
					<p class="text-sm text-warning-700 dark:text-warning-300 mb-3">
						Areas where your natural tendencies may create blind spots. Click to discuss with your advisor.
					</p>
					<div class="space-y-2">
						{#each profile.primary_blindspots.slice(0, 2) as blindspot (blindspot.label)}
							{@const blindspotId = getBlindspotId(blindspot.label)}
							{@const count = discussionCounts[blindspotId] || 0}
							<a
								href={getBlindspotDiscussUrl(blindspot)}
								class="block bg-white dark:bg-neutral-800 rounded-lg p-3 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors group"
							>
								<div class="flex items-center justify-between">
									<span class="font-medium text-neutral-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-400">{blindspot.label}</span>
									<div class="flex items-center gap-2">
										{#if count > 0}
											<span class="text-xs text-neutral-500 dark:text-neutral-400 flex items-center gap-1">
												<MessageCircle class="w-3 h-3" />
												{count}
											</span>
										{/if}
										<svg class="w-4 h-4 text-neutral-400 group-hover:text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
										</svg>
									</div>
								</div>
							</a>
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
