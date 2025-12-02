<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { apiClient } from '$lib/api/client';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	let problemStatement = '';
	let isSubmitting = false;
	let error: string | null = null;

	onMount(() => {
		const unsubscribe = isAuthenticated.subscribe((authenticated) => {
			if (!authenticated) {
				goto('/login');
			}
		});

		return unsubscribe;
	});

	async function handleSubmit() {
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

			// Create session
			const sessionData = await apiClient.createSession({
				problem_statement: problemStatement.trim()
			});

			const sessionId = sessionData.id;

			// Start deliberation
			await apiClient.startDeliberation(sessionId);

			// Redirect to meeting view
			goto(`/meeting/${sessionId}`);

		} catch (err) {
			console.error('Failed to create meeting:', err);
			error = err instanceof Error ? err.message : 'Failed to create meeting';
			isSubmitting = false;
		}
	}

	function handleKeyPress(event: KeyboardEvent) {
		// Allow Ctrl+Enter or Cmd+Enter to submit
		if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
			handleSubmit();
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
</script>

<svelte:head>
	<title>New Meeting - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
	<!-- Header -->
	<header class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center gap-4">
				<a
					href="/dashboard"
					class="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors duration-200"
					aria-label="Back to dashboard"
				>
					<svg class="w-5 h-5 text-slate-600 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
					</svg>
				</a>
				<div>
					<h1 class="text-2xl font-bold text-slate-900 dark:text-white">
						Start New Meeting
					</h1>
					<p class="text-sm text-slate-600 dark:text-slate-400">
						Describe your strategic decision
					</p>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-8">
			<form on:submit|preventDefault={handleSubmit} class="space-y-6">
				<!-- Problem Statement Input -->
				<div>
					<label for="problem" class="block text-lg font-semibold text-slate-900 dark:text-white mb-2">
						What decision do you need help with?
					</label>
					<p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
						Be specific about the decision you're facing. Include context like timeframes, constraints, or key considerations.
					</p>
					<textarea
						id="problem"
						bind:value={problemStatement}
						on:keydown={handleKeyPress}
						placeholder="Example: Should we raise a Series A round now or wait 6 months to improve our metrics? Our current burn rate is $200K/month, we have 8 months of runway, and our MRR growth is 15%..."
						rows="8"
						class="w-full px-4 py-3 bg-white dark:bg-slate-900 border-2 border-slate-300 dark:border-slate-600 rounded-lg focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 transition-colors duration-200"
						required
						minlength="20"
						maxlength="5000"
					></textarea>
					<div class="flex items-center justify-between mt-2">
						<p class="text-xs text-slate-500 dark:text-slate-400">
							{problemStatement.length}/5000 characters
							{#if problemStatement.length > 0 && problemStatement.length < 20}
								<span class="text-orange-600 dark:text-orange-400">
									(minimum 20 characters)
								</span>
							{/if}
						</p>
						<p class="text-xs text-slate-500 dark:text-slate-400">
							<kbd class="px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded text-xs">Ctrl</kbd>
							+
							<kbd class="px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded text-xs">Enter</kbd>
							to submit
						</p>
					</div>
				</div>

				<!-- Examples -->
				<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4">
					<h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-3">
						Need inspiration? Try one of these examples:
					</h3>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
						{#each examples as example}
							<button
								type="button"
								on:click={() => useExample(example)}
								class="text-left p-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:border-blue-400 dark:hover:border-blue-600 hover:shadow-sm transition-all duration-200 text-sm text-slate-700 dark:text-slate-300"
							>
								"{example.substring(0, 80)}{example.length > 80 ? '...' : ''}"
							</button>
						{/each}
					</div>
				</div>

				<!-- Error Message -->
				{#if error}
					<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
						<div class="flex items-center gap-2">
							<svg class="w-5 h-5 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<p class="text-sm text-red-900 dark:text-red-200">
								{error}
							</p>
						</div>
					</div>
				{/if}

				<!-- Submit Button -->
				<div class="flex items-center gap-4">
					<button
						type="submit"
						disabled={isSubmitting || problemStatement.trim().length < 20}
						class="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white font-medium rounded-lg transition-colors duration-200 disabled:cursor-not-allowed flex items-center justify-center gap-2"
					>
						{#if isSubmitting}
							<Spinner size="sm" variant="neutral" ariaLabel="Starting meeting" />
							Starting meeting...
						{:else}
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
							</svg>
							Start Meeting
						{/if}
					</button>

					<a
						href="/dashboard"
						class="px-6 py-3 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-300 font-medium rounded-lg transition-colors duration-200"
					>
						Cancel
					</a>
				</div>

				<!-- Info Box -->
				<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
					<div class="flex gap-3">
						<svg class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						<div class="text-sm text-blue-900 dark:text-blue-200">
							<p class="font-semibold mb-1">What happens next?</p>
							<ul class="list-disc list-inside space-y-1 text-blue-800 dark:text-blue-300">
								<li>Your decision will be analyzed and broken down into key focus areas</li>
								<li>3-5 expert personas will be selected to debate your decision</li>
								<li>Multiple rounds of deliberation will identify trade-offs and blind spots</li>
								<li>A clear recommendation with action steps will be synthesized</li>
							</ul>
							<p class="mt-2 text-xs text-blue-700 dark:text-blue-400">
								Average deliberation time: 5-15 minutes
							</p>
						</div>
					</div>
				</div>
			</form>
		</div>
	</main>
</div>
