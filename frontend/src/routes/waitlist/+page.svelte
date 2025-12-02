<script lang="ts">
	import { browser } from '$app/environment';
	import { env } from '$env/dynamic/public';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	let email = $state('');
	let loading = $state(false);
	let error = $state('');
	let submitted = $state(false);
	let isWhitelisted = $state(false);

	async function handleSubmit(e: Event) {
		e.preventDefault();

		if (!email || !email.includes('@')) {
			error = 'Please enter a valid email address';
			return;
		}

		loading = true;
		error = '';

		try {
			const API_BASE_URL = browser
				? env.PUBLIC_API_URL || 'http://localhost:8000'
				: 'http://api:8000';

			const response = await fetch(`${API_BASE_URL}/api/v1/waitlist`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email }),
			});

			const data = await response.json();

			if (response.ok) {
				submitted = true;
				isWhitelisted = data.is_whitelisted || false;
			} else {
				error = data.detail || 'Something went wrong. Please try again.';
			}
		} catch (err) {
			error = 'Network error. Please check your connection and try again.';
			console.error('Waitlist error:', err);
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Join Waitlist - Board of One</title>
	<meta
		name="description"
		content="Join the waitlist for Board of One - AI-powered strategic decision-making"
	/>
</svelte:head>

<div
	class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 px-4"
>
	<div class="max-w-lg w-full">
		<!-- Logo -->
		<div class="text-center mb-8">
			<a href="/" class="inline-block">
				<h1 class="text-4xl font-bold text-slate-900 dark:text-white mb-2">Board of One</h1>
			</a>
			<p class="text-slate-600 dark:text-slate-400">
				AI-powered strategic decision-making
			</p>
		</div>

		<!-- Waitlist Card -->
		<div
			class="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8 border border-slate-200 dark:border-slate-700"
		>
			{#if !submitted}
				<h2 class="text-2xl font-semibold text-slate-900 dark:text-white mb-4">
					Join the Waitlist
				</h2>

				<p class="text-slate-600 dark:text-slate-400 mb-6">
					We're currently in closed beta. Enter your email to join the waitlist and get early
					access when we open up.
				</p>

				<!-- Waitlist Form -->
				<form onsubmit={handleSubmit} class="space-y-4">
					<div>
						<label for="email" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
							Email Address
						</label>
						<input
							id="email"
							type="email"
							bind:value={email}
							placeholder="you@example.com"
							disabled={loading}
							class="w-full px-4 py-3 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 disabled:opacity-50 disabled:cursor-not-allowed"
							required
						/>
					</div>

					{#if error}
						<div class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
							<p class="text-sm text-red-900 dark:text-red-200">{error}</p>
						</div>
					{/if}

					<button
						type="submit"
						disabled={loading}
						class="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
					>
						{#if loading}
							<Spinner size="sm" variant="neutral" ariaLabel="Joining waitlist" />
							<span>Joining...</span>
						{:else}
							<span>Join Waitlist</span>
						{/if}
					</button>
				</form>

				<!-- Benefits -->
				<div class="mt-8 pt-8 border-t border-slate-200 dark:border-slate-700">
					<h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-4">
						What you'll get:
					</h3>
					<ul class="space-y-3">
						<li class="flex items-start gap-3">
							<svg
								class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M5 13l4 4L19 7"
								></path>
							</svg>
							<span class="text-sm text-slate-700 dark:text-slate-300">
								Early access to Board of One platform
							</span>
						</li>
						<li class="flex items-start gap-3">
							<svg
								class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M5 13l4 4L19 7"
								></path>
							</svg>
							<span class="text-sm text-slate-700 dark:text-slate-300">
								Expert AI personas for strategic decisions
							</span>
						</li>
						<li class="flex items-start gap-3">
							<svg
								class="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M5 13l4 4L19 7"
								></path>
							</svg>
							<span class="text-sm text-slate-700 dark:text-slate-300">
								Priority support and feature requests
							</span>
						</li>
					</ul>
				</div>
			{:else}
				<!-- Success Message -->
				<div class="text-center">
					{#if isWhitelisted}
						<div class="mb-6">
							<div
								class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/20 mb-4"
							>
								<svg
									class="w-8 h-8 text-green-600 dark:text-green-400"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M5 13l4 4L19 7"
									></path>
								</svg>
							</div>
							<h2 class="text-2xl font-semibold text-slate-900 dark:text-white mb-2">
								You're Already Whitelisted!
							</h2>
							<p class="text-slate-600 dark:text-slate-400 mb-6">
								Great news! You have immediate access to Board of One.
							</p>
							<a
								href="/login"
								class="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200"
							>
								Sign In Now
							</a>
						</div>
					{:else}
						<div class="mb-6">
							<div
								class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/20 mb-4"
							>
								<svg
									class="w-8 h-8 text-blue-600 dark:text-blue-400"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M3 19v-8.93a2 2 0 01.89-1.664l7-4.666a2 2 0 012.22 0l7 4.666A2 2 0 0121 10.07V19M3 19a2 2 0 002 2h14a2 2 0 002-2M3 19l6.75-4.5M21 19l-6.75-4.5M3 10l6.75 4.5M21 10l-6.75 4.5m0 0l-1.14.76a2 2 0 01-2.22 0l-1.14-.76"
									></path>
								</svg>
							</div>
							<h2 class="text-2xl font-semibold text-slate-900 dark:text-white mb-2">
								You're on the List!
							</h2>
							<p class="text-slate-600 dark:text-slate-400 mb-6">
								We'll notify you via email when your spot is ready. Check your inbox for a
								confirmation email.
							</p>
						</div>
					{/if}

					<a
						href="/"
						class="text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors"
					>
						← Back to home
					</a>
				</div>
			{/if}
		</div>

		<!-- Additional Info -->
		{#if !submitted}
			<div class="mt-6 text-center">
				<p class="text-sm text-slate-600 dark:text-slate-400">
					Already have access?
					<a
						href="/login"
						class="text-blue-600 dark:text-blue-400 hover:underline font-medium"
					>
						Sign in
					</a>
				</p>
			</div>
		{/if}
	</div>
</div>
