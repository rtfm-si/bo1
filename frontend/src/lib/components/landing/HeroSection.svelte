<script lang="ts">
	/**
	 * Hero Section - Landing page hero with animated background and waitlist form.
	 * Enhanced with product demo carousel (TODO.md Tier 1)
	 */
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import HeroCarousel from './HeroCarousel.svelte';

	interface Props {
		email: string;
		loading: boolean;
		submitted: boolean;
		error: string;
		mounted: boolean;
		onSubmit: (e: Event) => void;
		onShowSample: () => void;
	}

	let { email = $bindable(), loading, submitted, error, mounted, onSubmit, onShowSample }: Props =
		$props();
</script>

<section
	class="relative overflow-hidden bg-gradient-to-br from-brand-50 via-white to-neutral-50 dark:from-neutral-900 dark:via-neutral-900 dark:to-neutral-800 py-20 md:py-32 animate-gradient"
>
	<!-- Animated background elements -->
	<div class="absolute inset-0 overflow-hidden pointer-events-none">
		<div
			class="absolute top-20 left-10 w-72 h-72 bg-brand-400/15 dark:bg-brand-600/10 rounded-full blur-3xl animate-float"
		></div>
		<div
			class="absolute bottom-20 right-10 w-96 h-96 bg-brand-300/10 dark:bg-brand-700/10 rounded-full blur-3xl animate-float-reverse"
		></div>
	</div>

	<div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
		<div class="text-center max-w-4xl mx-auto">
			<h1
				class="text-4xl md:text-5xl lg:text-6xl font-bold text-neutral-900 dark:text-neutral-100 mb-6 leading-tight transition-all duration-700"
				class:opacity-0={!mounted}
				class:translate-y-8={!mounted}
			>
				Decide With Confidence.<br />
				<span class="text-brand-600 dark:text-brand-400 italic font-extrabold emphasis-word"
					>Move With Clarity.</span
				>
			</h1>
			<div
				class="space-y-4 mb-8 transition-all duration-700 delay-200"
				class:opacity-0={!mounted}
				class:translate-y-8={!mounted}
			>
				<p class="text-lg md:text-xl text-neutral-700 dark:text-neutral-300 max-w-2xl mx-auto">
					Turns complex decisions into clear, actionable recommendations — in minutes.
				</p>

				<!-- Trust Band -->
				<div
					class="flex flex-wrap justify-center gap-3 items-center text-sm text-neutral-600 dark:text-neutral-400 pt-2"
				>
					<span
						class="trust-badge inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/50 dark:bg-neutral-800/50 backdrop-blur border border-brand-200 dark:border-brand-800"
					>
						<span class="text-brand-600 dark:text-brand-400">✓</span>
						<span>Built for founders & operators</span>
					</span>
					<span
						class="trust-badge inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/50 dark:bg-neutral-800/50 backdrop-blur border border-brand-200 dark:border-brand-800"
					>
						<span class="text-brand-600 dark:text-brand-400">✓</span>
						<span>No credit card required</span>
					</span>
					<span
						class="trust-badge inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/50 dark:bg-neutral-800/50 backdrop-blur border border-brand-200 dark:border-brand-800"
					>
						<span class="text-brand-600 dark:text-brand-400">✓</span>
						<span>Limited beta spots</span>
					</span>
				</div>
			</div>

			<!-- Product Demo Carousel -->
			<div
				class="my-12 transition-all duration-700 delay-250"
				class:opacity-0={!mounted}
				class:translate-y-8={!mounted}
			>
				<HeroCarousel />

				<!-- Feature highlights under carousel -->
				<div class="mt-8 grid md:grid-cols-3 gap-6 text-center max-w-3xl mx-auto">
					<div>
						<div class="text-sm font-bold text-brand-600 dark:text-brand-400 mb-1 uppercase tracking-wide">
							Complete Breakdown
						</div>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">
							Full analysis with reasoning, not just a single answer
						</p>
					</div>
					<div>
						<div class="text-sm font-bold text-brand-600 dark:text-brand-400 mb-1 uppercase tracking-wide">
							Multiple Perspectives
						</div>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">
							See blind spots and trade-offs you wouldn't find alone
						</p>
					</div>
					<div>
						<div class="text-sm font-bold text-brand-600 dark:text-brand-400 mb-1 uppercase tracking-wide">
							Clear Recommendations
						</div>
						<p class="text-sm text-neutral-600 dark:text-neutral-400">
							Decisions that hold up when stakes are high
						</p>
					</div>
				</div>
			</div>

			<!-- Waitlist Form -->
			{#if !submitted}
				<div
					class="max-w-md mx-auto mb-6 transition-all duration-700 delay-300"
					class:opacity-0={!mounted}
					class:translate-y-8={!mounted}
				>
					<div
						class="relative bg-white/90 dark:bg-neutral-800/90 backdrop-blur-lg rounded-xl shadow-xl p-8 border border-brand-200 dark:border-brand-700 hover:shadow-2xl transition-shadow duration-300"
					>
						<div class="relative">
							<h2 class="text-xl font-bold mb-2 text-neutral-900 dark:text-neutral-100">
								Request Early Access
							</h2>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-6">
								We're onboarding in batches during beta. Request access to join the queue.
							</p>
							<form onsubmit={onSubmit} class="space-y-4">
								<Input
									type="email"
									placeholder="your.email@example.com"
									bind:value={email}
									disabled={loading}
									ariaLabel="Email address"
								/>
								{#if error}
									<p class="text-error-600 dark:text-error-400 text-sm">{error}</p>
								{/if}
								<Button type="submit" variant="brand" size="lg" {loading} class="w-full">
									{loading ? 'Requesting Access...' : 'Request Early Access'}
								</Button>
							</form>
							<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-4">
								No credit card. No commitment.
							</p>
						</div>
					</div>
				</div>

				<!-- Secondary CTA -->
				<div
					class="transition-all duration-700 delay-400"
					class:opacity-0={!mounted}
					class:translate-y-8={!mounted}
				>
					<button
						onclick={onShowSample}
						class="text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 font-medium text-sm underline underline-offset-4 transition-colors"
					>
						See a Sample Decision →
					</button>
				</div>
			{:else}
				<div
					class="max-w-md mx-auto bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg p-8"
				>
					<div class="text-center">
						<div class="text-5xl mb-4">✓</div>
						<h3 class="text-2xl font-semibold text-success-900 dark:text-success-100 mb-2">
							You're on the list!
						</h3>
						<p class="text-success-700 dark:text-success-300">
							Check your inbox ({email}) for next steps. We'll notify you when your spot is ready.
						</p>
					</div>
				</div>
			{/if}
		</div>
	</div>
</section>

<style>
	/* Floating animation for background elements */
	@keyframes float {
		0%,
		100% {
			transform: translateY(0px) scale(1);
		}
		50% {
			transform: translateY(-30px) scale(1.05);
		}
	}

	@keyframes floatReverse {
		0%,
		100% {
			transform: translateY(0px) scale(1);
		}
		50% {
			transform: translateY(30px) scale(1.05);
		}
	}

	/* Subtle gradient shift */
	@keyframes gradientShift {
		0%,
		100% {
			background-position: 0% 50%;
		}
		50% {
			background-position: 100% 50%;
		}
	}

	.animate-float {
		animation: float 8s ease-in-out infinite;
	}

	.animate-float-reverse {
		animation: floatReverse 10s ease-in-out infinite;
	}

	.animate-gradient {
		background-size: 200% 200%;
		animation: gradientShift 8s ease infinite;
	}

	/* Subtle emphasis animation for key words */
	@keyframes emphasis-glow {
		0%,
		100% {
			text-shadow: 0 0 8px rgba(0, 200, 179, 0.15);
		}
		50% {
			text-shadow: 0 0 12px rgba(0, 200, 179, 0.25);
		}
	}

	.emphasis-word {
		animation: emphasis-glow 3s ease-in-out infinite;
	}

	/* Trust band badge effect */
	.trust-badge {
		transition: all 0.3s ease;
	}

	.trust-badge:hover {
		transform: scale(1.05);
		box-shadow: 0 4px 12px rgba(0, 200, 179, 0.2);
	}
</style>
