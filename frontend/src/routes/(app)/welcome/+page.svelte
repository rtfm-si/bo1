<script lang="ts">
	/**
	 * Welcome page with demo questions
	 *
	 * Shows personalized question suggestions after onboarding
	 * to help users start their first meeting.
	 */
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { apiClient, type DemoQuestion } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	// State
	let questions = $state<DemoQuestion[]>([]);
	let isLoading = $state(true);
	let isRefreshing = $state(false);
	let error = $state<string | null>(null);
	let userName = $state('');

	// Category colors
	const categoryColors: Record<string, string> = {
		strategy: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
		growth: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
		operations: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
		product: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
		finance: 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300'
	};

	onMount(async () => {
		await loadQuestions();

		// Get user name from context if available
		try {
			const contextResponse = await apiClient.getUserContext();
			if (contextResponse.exists && contextResponse.context?.company_name) {
				userName = contextResponse.context.company_name;
			}
		} catch {
			// Ignore - name is optional
		}
	});

	async function loadQuestions() {
		isLoading = true;
		error = null;

		try {
			const data = await apiClient.getDemoQuestions();
			questions = data.questions || [];
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load suggestions';
		} finally {
			isLoading = false;
		}
	}

	async function refreshQuestions() {
		isRefreshing = true;
		error = null;

		try {
			const data = await apiClient.getDemoQuestions(true);
			questions = data.questions || [];
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to refresh suggestions';
		} finally {
			isRefreshing = false;
		}
	}

	function useQuestion(question: string) {
		// Navigate to new meeting with pre-filled question
		const encodedQuestion = encodeURIComponent(question);
		goto(`/meeting/new?q=${encodedQuestion}`);
	}

	function skipToMeeting() {
		goto('/meeting/new');
	}

	function goToDashboard() {
		goto('/dashboard');
	}
</script>

<svelte:head>
	<title>Get Started - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
	<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
		<!-- Header -->
		<div class="text-center mb-10">
			<div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-brand-100 dark:bg-brand-900/30 mb-4">
				<svg class="w-8 h-8 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
				</svg>
			</div>
			<h1 class="text-3xl font-bold text-slate-900 dark:text-white mb-3">
				{#if userName}
					Ready to make your first decision, {userName}?
				{:else}
					Ready to make your first decision?
				{/if}
			</h1>
			<p class="text-lg text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
				Here are some questions tailored to your business. Pick one to get started, or ask your own.
			</p>
		</div>

		<!-- Questions grid -->
		{#if isLoading}
			<div class="flex justify-center py-12">
				<Spinner size="lg" />
			</div>
		{:else if error}
			<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
				<p class="text-red-700 dark:text-red-300 mb-4">{error}</p>
				<Button variant="secondary" onclick={loadQuestions}>Try again</Button>
			</div>
		{:else if questions.length === 0}
			<div class="bg-slate-100 dark:bg-slate-800 rounded-lg p-6 text-center">
				<p class="text-slate-600 dark:text-slate-400 mb-4">No suggestions available.</p>
				<Button onclick={skipToMeeting}>Start with your own question</Button>
			</div>
		{:else}
			<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-8">
				{#each questions as q, i (i)}
					<button
						type="button"
						onclick={() => useQuestion(q.question)}
						class="text-left bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-5 hover:border-brand-300 dark:hover:border-brand-600 hover:shadow-md transition-all group"
					>
						<!-- Category badge -->
						<span class={`inline-block px-2 py-1 rounded text-xs font-medium mb-3 ${categoryColors[q.category] || categoryColors.strategy}`}>
							{q.category}
						</span>

						<!-- Question text -->
						<p class="text-slate-900 dark:text-white font-medium mb-2 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
							{q.question}
						</p>

						<!-- Relevance -->
						<p class="text-sm text-slate-500 dark:text-slate-400">
							{q.relevance}
						</p>

						<!-- Arrow indicator -->
						<div class="mt-3 flex items-center text-sm text-brand-600 dark:text-brand-400 opacity-0 group-hover:opacity-100 transition-opacity">
							<span>Use this question</span>
							<svg class="w-4 h-4 ml-1 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
							</svg>
						</div>
					</button>
				{/each}
			</div>

			<!-- Actions -->
			<div class="flex flex-col sm:flex-row items-center justify-center gap-4">
				<Button variant="secondary" onclick={refreshQuestions} disabled={isRefreshing} loading={isRefreshing}>
					{#if isRefreshing}
						Generating new suggestions...
					{:else}
						<svg class="w-4 h-4 mr-2 -ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
						</svg>
						Generate more suggestions
					{/if}
				</Button>

				<Button variant="ghost" onclick={skipToMeeting}>
					Ask my own question instead
				</Button>
			</div>
		{/if}

		<!-- Footer -->
		<div class="mt-12 text-center">
			<button
				type="button"
				onclick={goToDashboard}
				class="text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
			>
				Skip to dashboard
			</button>
		</div>
	</div>
</div>
