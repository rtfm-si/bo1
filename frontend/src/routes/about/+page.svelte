<script lang="ts">
	/**
	 * About Page - Company information
	 */
	import { onMount } from 'svelte';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Card from '$lib/components/ui/Card.svelte';
	import Button from '$lib/components/ui/Button.svelte';

	let mounted = $state(false);

	onMount(() => {
		mounted = true;
	});
</script>

<style>
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

	/* Floating animation for background elements */
	@keyframes float {
		0%,
		100% {
			transform: translateY(0px) scale(1);
		}
		50% {
			transform: translateY(-20px) scale(1.02);
		}
	}

	.animate-float {
		animation: float 8s ease-in-out infinite;
	}

	/* Card hover effects */
	.card-hover {
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}

	.card-hover:hover {
		transform: translateY(-6px);
		box-shadow:
			0 20px 25px -5px rgb(0 0 0 / 0.1),
			0 8px 10px -6px rgb(0 0 0 / 0.1);
	}

	.card-hover:hover .card-icon {
		transform: scale(1.05) rotate(3deg);
	}

	.card-icon {
		transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}

	/* Staggered fade-in animations */
	@keyframes fadeInUp {
		from {
			opacity: 0;
			transform: translateY(20px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.stagger-item {
		opacity: 0;
		animation: fadeInUp 0.6s ease forwards;
	}

	.stagger-item:nth-child(1) {
		animation-delay: 0.1s;
	}
	.stagger-item:nth-child(2) {
		animation-delay: 0.2s;
	}
	.stagger-item:nth-child(3) {
		animation-delay: 0.3s;
	}
</style>

<svelte:head>
	<title>About - Board of One</title>
	<meta name="description" content="Board of One gives independent founders the thinking power of a high-quality board—on demand. Make better decisions without going it alone." />
	<link rel="canonical" href="https://boardof.one/about" />
	<meta property="og:type" content="website" />
	<meta property="og:url" content="https://boardof.one/about" />
	<meta property="og:title" content="About - Board of One" />
	<meta property="og:description" content="Board of One gives independent founders the thinking power of a high-quality board—on demand." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="About - Board of One" />
	<meta name="twitter:description" content="Board of One gives independent founders the thinking power of a high-quality board—on demand." />
	<meta name="twitter:image" content="https://boardof.one/og-image.png" />
</svelte:head>

<div class="min-h-screen flex flex-col">
	<Header />

	<main class="flex-grow bg-white dark:bg-neutral-900">
		<!-- Hero -->
		<section class="py-24 bg-gradient-to-b from-brand-50 to-white dark:from-neutral-800 dark:to-neutral-900 relative overflow-hidden">
			<!-- Background decoration -->
			<div
				class="absolute top-10 right-10 w-72 h-72 bg-brand-400/10 dark:bg-brand-600/10 rounded-full blur-3xl animate-float"
			></div>
			<div class="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6 leading-tight">
					<span class="text-neutral-700 dark:text-neutral-300 font-normal">Make better decisions.</span><br />
					<span class="text-brand-600 dark:text-brand-400 emphasis-word">Without going it <span class="italic font-extrabold">alone</span>.</span>
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto leading-relaxed">
					Board of One gives independent founders the thinking power of a high-quality board—on demand.
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-20 border-b border-neutral-200 dark:border-neutral-800">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
				<p class="text-xl md:text-2xl text-neutral-700 dark:text-neutral-300 leading-relaxed mb-6">
					When you're building solo, the hardest decisions often happen without challenge, debate, or perspective.
				</p>
				<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mb-8 flex items-start gap-3">
					<span class="text-neutral-400 dark:text-neutral-500 mt-1">→</span>
					<span>That's where mistakes creep in, confidence wobbles, and momentum slows.</span>
				</p>
				<p class="text-2xl font-bold text-brand-600 dark:text-brand-400 emphasis-word">
					Board of One exists to <span class="italic">fix that</span>.
				</p>
			</div>
		</section>

		<!-- Why We Built It -->
		<section class="py-20 bg-neutral-50 dark:bg-neutral-800 border-y border-neutral-200 dark:border-neutral-700">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-10 leading-tight">
					<span class="text-neutral-700 dark:text-neutral-300 font-normal">Why we</span>
					<span class="text-brand-600 dark:text-brand-400 italic"> built it</span>
				</h2>
				<div class="space-y-8">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<p class="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
							Most founders don't need more information.
						</p>
						<p class="text-lg text-brand-600 dark:text-brand-400 font-medium">
							They need structured <span class="italic">challenge</span>.
						</p>
					</div>
					<div class="space-y-3">
						<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed flex items-start gap-3">
							<span class="text-neutral-400 dark:text-neutral-500 mt-1">→</span>
							<span>Advisors are expensive.</span>
						</p>
						<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed flex items-start gap-3">
							<span class="text-neutral-400 dark:text-neutral-500 mt-1">→</span>
							<span>Peer groups are slow.</span>
						</p>
						<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed flex items-start gap-3">
							<span class="text-neutral-400 dark:text-neutral-500 mt-1">→</span>
							<span>Mentors aren't always available.</span>
						</p>
					</div>
					<p class="text-lg text-neutral-700 dark:text-neutral-300 leading-relaxed">
						So critical decisions get made in isolation—often under pressure.
					</p>
					<p class="text-xl font-bold text-brand-600 dark:text-brand-400 pt-2">
						We built Board of One to bring disciplined, board-level thinking into those moments.
					</p>
				</div>
			</div>
		</section>

		<!-- How It Works -->
		<section class="py-20 relative overflow-hidden">
			<!-- Background decoration -->
			<div
				class="absolute bottom-0 left-10 w-64 h-64 bg-brand-400/5 dark:bg-brand-600/5 rounded-full blur-3xl animate-float"
			></div>
			<div class="relative max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-10 leading-tight">
					<span class="text-neutral-700 dark:text-neutral-300 font-normal">How it</span>
					<span class="text-brand-600 dark:text-brand-400 italic"> works</span>
				</h2>
				<div class="space-y-8">
					<p class="text-lg text-neutral-700 dark:text-neutral-300 leading-relaxed">
						Board of One uses AI-powered expert panels to simulate real board discussions.
					</p>
					<div class="grid sm:grid-cols-3 gap-4">
						<div class="text-center p-4">
							<div class="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-1">1</div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400">Challenge assumptions</p>
						</div>
						<div class="text-center p-4">
							<div class="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-1">2</div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400">Surface risks</p>
						</div>
						<div class="text-center p-4">
							<div class="text-2xl font-bold text-brand-600 dark:text-brand-400 mb-1">3</div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400">Test options</p>
						</div>
					</div>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Different perspectives converge on a clear recommendation and next steps.
					</p>
					<Card variant="bordered" padding="lg" class="bg-gradient-to-br from-brand-50 to-white dark:from-brand-900/20 dark:to-neutral-800 border-brand-200 dark:border-brand-800">
						<p class="text-lg text-neutral-900 dark:text-neutral-100 leading-relaxed">
							<span class="font-bold">Not chat for chat's sake.</span>
						</p>
						<p class="text-brand-600 dark:text-brand-400 font-medium mt-2">
							Focused debate. Clear outcomes. <span class="italic">Forward motion</span>.
						</p>
					</Card>
				</div>
			</div>
		</section>

		<!-- What We Believe -->
		<section class="py-20 bg-neutral-50 dark:bg-neutral-800 border-y border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-12 text-center leading-tight">
					<span class="text-neutral-700 dark:text-neutral-300 font-normal">What we</span>
					<span class="text-brand-600 dark:text-brand-400 italic"> believe</span>
				</h2>
				<div class="grid md:grid-cols-3 gap-8">
					<div
						class="bg-white dark:bg-neutral-900 rounded-xl p-8 border border-neutral-200 dark:border-neutral-700 card-hover stagger-item"
						class:stagger-item={mounted}
					>
						<div class="card-icon w-12 h-12 bg-brand-100 dark:bg-brand-900/30 rounded-xl flex items-center justify-center mb-5">
							<svg class="w-6 h-6 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
						</div>
						<h3 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">Clarity beats consensus</h3>
						<p class="text-neutral-600 dark:text-neutral-400 leading-relaxed">Good decisions come from sharp thinking, not agreement for its own sake.</p>
					</div>
					<div
						class="bg-white dark:bg-neutral-900 rounded-xl p-8 border border-neutral-200 dark:border-neutral-700 card-hover stagger-item"
						class:stagger-item={mounted}
					>
						<div class="card-icon w-12 h-12 bg-brand-100 dark:bg-brand-900/30 rounded-xl flex items-center justify-center mb-5">
							<svg class="w-6 h-6 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
							</svg>
						</div>
						<h3 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">Challenge strengthens decisions</h3>
						<p class="text-neutral-600 dark:text-neutral-400 leading-relaxed">Constructive disagreement uncovers blind spots and improves judgement.</p>
					</div>
					<div
						class="bg-white dark:bg-neutral-900 rounded-xl p-8 border border-neutral-200 dark:border-neutral-700 card-hover stagger-item"
						class:stagger-item={mounted}
					>
						<div class="card-icon w-12 h-12 bg-brand-100 dark:bg-brand-900/30 rounded-xl flex items-center justify-center mb-5">
							<svg class="w-6 h-6 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
							</svg>
						</div>
						<h3 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">Decisions lead to action</h3>
						<p class="text-neutral-600 dark:text-neutral-400 leading-relaxed">Insight is only valuable if it helps you move forward.</p>
					</div>
				</div>
			</div>
		</section>

		<!-- Built For -->
		<section class="py-20">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-6 leading-tight">
					<span class="text-neutral-700 dark:text-neutral-300 font-normal">Built for founders who</span><br />
					<span class="text-brand-600 dark:text-brand-400 emphasis-word italic font-extrabold">decide</span>
				</h2>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 leading-relaxed max-w-2xl mx-auto">
					If you're making high-stakes calls without a board behind you, Board of One is built for exactly that moment.
				</p>
			</div>
		</section>

		<!-- Contact CTA -->
		<section class="relative py-20 bg-gradient-to-r from-brand-600 to-brand-700 dark:from-brand-700 dark:to-brand-800 overflow-hidden">
			<!-- Background decoration -->
			<div class="absolute inset-0 opacity-10">
				<div class="absolute top-10 left-20 w-64 h-64 bg-white rounded-full blur-3xl animate-float"></div>
				<div class="absolute bottom-10 right-20 w-80 h-80 bg-white rounded-full blur-3xl"></div>
			</div>
			<div class="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-3xl md:text-4xl font-bold text-white mb-4 drop-shadow-md">Get in Touch</h2>
				<p class="text-brand-100 text-lg mb-8 drop-shadow-md">Have questions? We'd love to hear from you.</p>
				<Button
					variant="secondary"
					size="lg"
					onclick={() => window.location.href = 'mailto:hello@boardofone.com'}
					class="inline-flex items-center gap-2 transform hover:scale-105 transition-transform duration-300"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
					</svg>
					hello@boardofone.com
				</Button>
			</div>
		</section>
	</main>

	<Footer />
</div>
