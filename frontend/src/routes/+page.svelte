<script lang="ts">
	/**
	 * Landing Page - Board of One Closed Beta
	 * Hormozi Framework: Complete implementation with personality
	 * Design Token System: Applied throughout with alive animations
	 */
	import { onMount } from 'svelte';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import {
		HeroSection,
		MetricsGrid,
		FAQAccordion,
		SampleDecisionModal
	} from '$lib/components/landing';
	import { useSectionObservers } from '$lib/hooks/useIntersectionObserver.svelte';
	import {
		valueBlocks,
		metrics,
		betaBenefits,
		decisionTypes,
		faqs
	} from '$lib/data/landing-page-data';

	// Waitlist form state
	let email = $state('');
	let loading = $state(false);
	let submitted = $state(false);
	let error = $state('');

	// Animation state
	let mounted = $state(false);

	// Sample decision modal
	let showSampleModal = $state(false);

	// Section visibility tracking
	const visibility = useSectionObservers([
		'value-blocks',
		'features',
		'metrics-section',
		'beta-invite-section'
	]);

	onMount(() => {
		mounted = true;
	});

	async function handleWaitlistSubmit(e: Event) {
		e.preventDefault();
		if (!email || !email.includes('@')) {
			error = 'Please enter a valid email address';
			return;
		}

		loading = true;
		error = '';

		try {
			const response = await fetch('/api/v1/waitlist', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email })
			});

			if (response.ok) {
				submitted = true;
			} else {
				error = 'Something went wrong. Please try again.';
			}
		} catch {
			error = 'Network error. Please try again.';
		} finally {
			loading = false;
		}
	}

	// Icon SVG paths (Lucide-inspired, theme-aligned)
	function getIconPath(icon: string): string {
		const icons: Record<string, string> = {
			target:
				'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16zm0-14a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 10a4 4 0 1 1 0-8 4 4 0 0 1 0 8z',
			users: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0z',
			zap: 'M13 2L3 14h8l-1 8 10-12h-8l1-8z',
			'check-circle': 'M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4L12 14.01l-3-3'
		};
		return icons[icon] || '';
	}
</script>

<svelte:head>
	<title>Board of One - Decide With Confidence. Move With Clarity.</title>
	<meta
		name="description"
		content="A strategic thinking engine that turns complex decisions into clear, actionable recommendations — in minutes. Not another AI chat. A complete decision process."
	/>
</svelte:head>

<style>
	:global(html) {
		scroll-behavior: smooth;
	}

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

	.animate-float {
		animation: float 8s ease-in-out infinite;
	}

	.animate-float-reverse {
		animation: floatReverse 10s ease-in-out infinite;
	}

	/* Card hover effects */
	.card-hover {
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}

	.card-hover:hover {
		transform: translateY(-8px);
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

	/* Border glow on hover */
	.border-glow {
		position: relative;
		transition: all 0.3s ease;
	}

	.border-glow::before {
		content: '';
		position: absolute;
		inset: 0;
		border-radius: inherit;
		padding: 2px;
		background: linear-gradient(135deg, #00c8b3, #d4844f);
		-webkit-mask:
			linear-gradient(#fff 0 0) content-box,
			linear-gradient(#fff 0 0);
		-webkit-mask-composite: xor;
		mask:
			linear-gradient(#fff 0 0) content-box,
			linear-gradient(#fff 0 0);
		mask-composite: exclude;
		opacity: 0;
		transition: opacity 0.3s ease;
	}

	.border-glow:hover::before {
		opacity: 0.6;
	}

	/* Staggered fade-in animations */
	@keyframes fadeInUp {
		from {
			opacity: 0;
			transform: translateY(30px);
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
	.stagger-item:nth-child(4) {
		animation-delay: 0.4s;
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

	/* Infinite horizontal carousel */
	.carousel-container {
		display: flex;
		overflow: hidden;
	}

	.carousel-group {
		display: flex;
		flex-shrink: 0;
		gap: 0;
		animation: scroll-left 50s linear infinite;
		will-change: transform;
	}

	.carousel-container:hover .carousel-group {
		animation-play-state: paused;
	}

	@keyframes scroll-left {
		0% {
			transform: translateX(0);
		}
		100% {
			transform: translateX(-100%);
		}
	}

	.carousel-item {
		white-space: nowrap;
		padding: 0 1.5rem;
		position: relative;
		flex-shrink: 0;
	}

	.carousel-item::after {
		content: '•';
		position: absolute;
		right: 0;
		top: 50%;
		transform: translateY(-50%);
		color: var(--color-brand);
		opacity: 0.3;
	}

	/* Subtle "no" shake animation for stuck/frustrated state */
	@keyframes shake-no {
		0%,
		100% {
			transform: translateX(0);
		}
		15%,
		45%,
		75% {
			transform: translateX(-2px);
		}
		30%,
		60%,
		90% {
			transform: translateX(2px);
		}
	}

	.shake-stuck:hover {
		animation: shake-no 0.5s ease-in-out;
	}

	/* Subtle "yes" nod animation for positive/clarity state */
	@keyframes nod-yes {
		0%,
		100% {
			transform: translateY(0);
		}
		15%,
		45%,
		75% {
			transform: translateY(-3px);
		}
		30%,
		60%,
		90% {
			transform: translateY(0px);
		}
	}

	.nod-clarity:hover {
		animation: nod-yes 0.6s ease-in-out;
	}
</style>

<div class="min-h-screen flex flex-col">
	<Header transparent={false} />

	<HeroSection
		bind:email
		{loading}
		{submitted}
		{error}
		{mounted}
		onSubmit={handleWaitlistSubmit}
		onShowSample={() => (showSampleModal = true)}
	/>

	<MetricsGrid {metrics} visible={visibility.get('metrics-section') ?? false} />

	<!-- Why This Matters -->
	<section
		class="py-20 bg-neutral-50 dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-800"
	>
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
			<h2
				class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-4 text-center leading-tight"
			>
				<span class="text-neutral-700 dark:text-neutral-300 font-normal"
					>The toughest part of running a business isn't the work.</span
				><br />
				<span class="text-brand-600 dark:text-brand-400 emphasis-word"
					>It's the <span class="italic font-extrabold">decisions</span>.</span
				>
			</h2>
			<p
				class="text-lg text-neutral-600 dark:text-neutral-400 text-center max-w-2xl mx-auto leading-relaxed"
			>
				Most founders operate in a fog: incomplete information, too many angles, no one to
				sanity-check thinking. Bad decisions cost time. No decisions cost growth.
			</p>
			<p class="text-lg font-semibold text-brand-600 dark:text-brand-400 text-center mt-6">
				You deserve clarity without hiring a team.
			</p>
		</div>
	</section>

	<!-- Use Cases -->
	<section
		class="py-16 bg-white dark:bg-neutral-900 overflow-hidden border-y border-neutral-200 dark:border-neutral-800"
	>
		<div class="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="text-center mb-8">
				<h3 class="text-xl md:text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					What kind of decisions does <span
						class="text-brand-600 dark:text-brand-400 italic font-extrabold">Board of One</span
					> help with?
				</h3>
			</div>

			<!-- Infinite horizontal carousel -->
			<div class="relative w-full">
				<!-- Gradient fade edges -->
				<div
					class="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-white dark:from-neutral-900 to-transparent z-10 pointer-events-none"
				></div>
				<div
					class="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-white dark:from-neutral-900 to-transparent z-10 pointer-events-none"
				></div>

				<!-- Carousel container with two identical groups for seamless loop -->
				<div
					class="carousel-container text-lg font-medium text-neutral-700 dark:text-neutral-300"
				>
					<!-- First group -->
					<div class="carousel-group">
						{#each decisionTypes as decision, i (i)}
							<span class="carousel-item">{decision}</span>
						{/each}
					</div>
					<!-- Second group (duplicate for seamless loop) -->
					<div class="carousel-group" aria-hidden="true">
						{#each decisionTypes as decision, i (`duplicate-${i}`)}
							<span class="carousel-item">{decision}</span>
						{/each}
					</div>
				</div>
			</div>
		</div>
	</section>

	<!-- How It Works -->
	<section
		id="how-it-works"
		class="py-24 bg-white dark:bg-neutral-900 relative overflow-hidden border-y border-neutral-200 dark:border-neutral-800"
	>
		<!-- Background decoration -->
		<div
			class="absolute top-0 right-0 w-96 h-96 bg-brand-400/5 dark:bg-brand-600/5 rounded-full blur-3xl animate-float"
		></div>

		<div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="text-center mb-16">
				<h2
					class="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-4 leading-tight"
				>
					<span class="text-neutral-700 dark:text-neutral-300 font-normal"
						>You bring the question.</span
					><br />
					<span class="text-brand-600 dark:text-brand-400 emphasis-word"
						>We bring the <span class="italic font-extrabold">clarity</span>.</span
					>
				</h2>
			</div>

			<!-- 3-Step Process -->
			<div class="max-w-5xl mx-auto">
				<div class="grid md:grid-cols-3 gap-8 md:gap-12">
					<!-- Step 1 -->
					<div class="relative">
						<div class="flex flex-col items-center text-center">
							<div
								class="w-16 h-16 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center mb-4"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									width="32"
									height="32"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
									class="text-brand-600 dark:text-brand-400"
								>
									<path
										d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
									/>
								</svg>
							</div>
							<div
								class="text-sm font-bold text-brand-600 dark:text-brand-400 mb-2 uppercase tracking-wide"
							>
								Step 1
							</div>
							<h3 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
								Ask Your Question
							</h3>
							<p class="text-neutral-600 dark:text-neutral-400">
								Describe your decision in plain language
							</p>
						</div>
						<!-- Arrow for desktop -->
						<div
							class="hidden md:block absolute top-8 -right-6 text-brand-400 dark:text-brand-600 text-3xl"
						>
							→
						</div>
					</div>

					<!-- Step 2 -->
					<div class="relative">
						<div class="flex flex-col items-center text-center">
							<div
								class="w-16 h-16 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center mb-4"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									width="32"
									height="32"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
									class="text-brand-600 dark:text-brand-400"
								>
									<path d={getIconPath('users')} />
								</svg>
							</div>
							<div
								class="text-sm font-bold text-brand-600 dark:text-brand-400 mb-2 uppercase tracking-wide"
							>
								Step 2
							</div>
							<h3 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
								Get Expert Analysis
							</h3>
							<p class="text-neutral-600 dark:text-neutral-400">
								3-5 expert perspectives surface blind spots and trade-offs
							</p>
						</div>
						<!-- Arrow for desktop -->
						<div
							class="hidden md:block absolute top-8 -right-6 text-brand-400 dark:text-brand-600 text-3xl"
						>
							→
						</div>
					</div>

					<!-- Step 3 -->
					<div class="flex flex-col items-center text-center">
						<div
							class="w-16 h-16 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center mb-4"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="32"
								height="32"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								class="text-brand-600 dark:text-brand-400"
							>
								<path d={getIconPath('check-circle')} />
							</svg>
						</div>
						<div
							class="text-sm font-bold text-brand-600 dark:text-brand-400 mb-2 uppercase tracking-wide"
						>
							Step 3
						</div>
						<h3 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
							Take Action
						</h3>
						<p class="text-neutral-600 dark:text-neutral-400">
							Walk away with a clear recommendation and next steps
						</p>
					</div>
				</div>
			</div>

			<!-- Value Blocks -->
			<div id="value-blocks" class="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto mt-16">
				{#each valueBlocks as block, i}
					<div
						class="bg-white dark:bg-neutral-900 rounded-lg p-8 border border-neutral-200 dark:border-neutral-700 card-hover border-glow group"
						class:stagger-item={visibility.get('value-blocks')}
					>
						<div class="card-icon mb-6">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="40"
								height="40"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								class="text-brand-600 dark:text-brand-400"
							>
								<path d={getIconPath(block.icon)} />
							</svg>
						</div>
						<h3 class="font-bold text-xl text-neutral-900 dark:text-neutral-100 mb-3">
							{block.title}
						</h3>
						<p class="text-base text-neutral-600 dark:text-neutral-400 leading-relaxed mb-4">
							{block.description}
						</p>

						<!-- Hover Example -->
						<div
							class="opacity-0 group-hover:opacity-100 transition-opacity duration-300 pt-4 border-t border-neutral-200 dark:border-neutral-700"
						>
							<p class="text-sm text-brand-600 dark:text-brand-400 font-medium mb-1">Example:</p>
							<p class="text-sm text-neutral-700 dark:text-neutral-300 italic">
								"{block.example}"
							</p>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</section>


	<!-- Before/After Snippet -->
	<section
		class="py-24 bg-white dark:bg-neutral-900 relative overflow-hidden border-y border-neutral-200 dark:border-neutral-800"
	>
		<div class="absolute inset-0 pointer-events-none opacity-30">
			<div
				class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-br from-brand-400/20 to-success-400/20 dark:from-brand-600/10 dark:to-success-600/10 rounded-full blur-3xl"
			></div>
		</div>

		<div class="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
			<h2
				class="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-16 text-center leading-tight"
			>
				<span class="text-neutral-700 dark:text-neutral-300 font-normal"
					>From <span class="italic font-bold">Fog</span> to</span
				>
				<span class="text-brand-600 dark:text-brand-400 italic font-extrabold emphasis-word"
					>Focus</span
				>
			</h2>
			<div class="grid md:grid-cols-2 gap-12 items-center">
				<!-- Before -->
				<div class="relative shake-stuck">
					<div
						class="absolute -inset-0.5 bg-gradient-to-br from-error-300/10 to-warning-300/10 dark:from-error-500/10 dark:to-warning-500/10 rounded-xl blur-sm"
					></div>
					<div
						class="relative bg-white dark:bg-neutral-800 rounded-xl p-8 border-2 border-neutral-300 dark:border-neutral-600 hover:border-neutral-400 dark:hover:border-neutral-500 transition-all duration-300 shadow-md"
					>
						<div
							class="text-xs font-bold text-error-600 dark:text-error-400 mb-4 uppercase tracking-wider flex items-center gap-2"
						>
							<span class="inline-block w-2 h-2 bg-error-500 rounded-full opacity-50"></span>
							Before
						</div>
						<p class="text-neutral-700 dark:text-neutral-300 leading-relaxed text-base font-medium">
							Spinning in circles. Second-guessing yourself. Paralyzed by too many variables.
							Reading everything but deciding nothing.
						</p>
					</div>
				</div>

				<!-- After -->
				<div class="relative after-card-wrapper nod-clarity">
					<div
						class="absolute -inset-0.5 bg-gradient-to-br from-brand-400/15 to-success-400/10 dark:from-brand-500/20 dark:to-success-500/15 rounded-xl blur-sm"
					></div>
					<div
						class="relative bg-white dark:bg-neutral-800 rounded-xl p-8 border-2 border-brand-200 dark:border-brand-700 hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 shadow-md"
					>
						<div
							class="text-xs font-bold text-brand-600 dark:text-brand-400 mb-4 uppercase tracking-wider flex items-center gap-2"
						>
							<span class="inline-block w-2 h-2 bg-success-500 rounded-full"></span>
							After
						</div>
						<div class="space-y-4">
							<p
								class="text-neutral-900 dark:text-neutral-100 leading-relaxed font-semibold text-lg"
							>
								A clear recommendation with reasoning you can defend.
							</p>
							<p class="text-neutral-700 dark:text-neutral-300 leading-relaxed text-base">
								The key trade-offs mapped out. Blind spots surfaced. Concrete next steps. Decision
								made.
							</p>
							<div class="pt-2 text-sm font-medium text-brand-600 dark:text-brand-400">
								→ Move forward with confidence
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</section>

	<!-- Social Proof -->
	<section
		class="py-16 bg-neutral-50 dark:bg-neutral-800 border-y border-neutral-200 dark:border-neutral-800"
	>
		<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="grid md:grid-cols-3 gap-8">
				<div class="text-center">
					<p class="text-neutral-700 dark:text-neutral-300 leading-relaxed mb-3">
						"Saved 3 days of research on a pricing decision."
					</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">— Founder, B2B SaaS</p>
				</div>
				<div class="text-center">
					<p class="text-neutral-700 dark:text-neutral-300 leading-relaxed mb-3">
						"Caught a risk I totally missed in my hiring plan."
					</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">— Solo Consultant</p>
				</div>
				<div class="text-center">
					<p class="text-neutral-700 dark:text-neutral-300 leading-relaxed mb-3">
						"Made my first confident pricing decision in minutes."
					</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">— E-commerce Operator</p>
				</div>
			</div>
		</div>
	</section>

	<!-- Closed Beta Invitation -->
	<section
		id="beta-invite-section"
		class="py-24 bg-white dark:bg-neutral-900 border-y border-neutral-200 dark:border-neutral-800"
	>
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="text-center mb-12">
				<h2 class="text-3xl md:text-4xl font-bold mb-4 leading-tight">
					<span class="text-neutral-700 dark:text-neutral-300 font-normal">Early access</span>
					<span class="text-brand-600 dark:text-brand-400 italic font-extrabold emphasis-word"
						>is open</span
					>
				</h2>
				<p class="text-lg text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
					For operators who need clarity, fast.
				</p>
			</div>

			<div
				class="bg-white dark:bg-neutral-800 rounded-xl p-8 md:p-12 border border-neutral-200 dark:border-neutral-700"
			>
				<h3 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">What you get:</h3>
				<div class="grid md:grid-cols-2 gap-4 mb-8">
					{#each betaBenefits as benefit, i}
						<div
							class="flex items-start gap-3"
							class:stagger-item={visibility.get('beta-invite-section')}
							style="animation-delay: {i * 0.1}s"
						>
							<div
								class="w-6 h-6 rounded-full bg-brand-600 dark:bg-brand-400 flex items-center justify-center flex-shrink-0 mt-0.5"
							>
								<span class="text-white dark:text-neutral-900 text-sm">✓</span>
							</div>
							<p class="text-neutral-700 dark:text-neutral-300 font-medium">{benefit}</p>
						</div>
					{/each}
				</div>
				<div class="text-center">
					<Button
						variant="brand"
						size="lg"
						onclick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
						class="transform hover:scale-105 transition-transform duration-300"
					>
						Request Early Access
					</Button>
					<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-4">
						Invites sent weekly. First-come, first-served.
					</p>
				</div>
			</div>
		</div>
	</section>

	<!-- Future Pricing Note -->
	<section
		class="py-16 bg-neutral-50 dark:bg-neutral-800 border-y border-neutral-200 dark:border-neutral-800"
	>
		<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
			<div
				class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-700 mb-4"
			>
				<span class="text-brand-600 dark:text-brand-400 text-sm font-semibold">Beta Pricing</span>
			</div>
			<h3 class="text-xl md:text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">
				Pricing launches later this year
			</h3>
			<p class="text-base text-neutral-600 dark:text-neutral-400 mb-4">
				Beta users get preferential pricing. No credit card. No commitment.
			</p>
			<div class="flex flex-wrap justify-center gap-4 text-sm text-neutral-600 dark:text-neutral-400">
				<span class="flex items-center gap-2">
					<span class="text-brand-600 dark:text-brand-400">✓</span>
					<span>Far less than hiring an advisor</span>
				</span>
				<span class="flex items-center gap-2">
					<span class="text-brand-600 dark:text-brand-400">✓</span>
					<span>Cheaper than a single wrong decision</span>
				</span>
			</div>
		</div>
	</section>

	<FAQAccordion {faqs} />

	<!-- Final CTA -->
	<section
		class="relative py-24 bg-gradient-to-r from-brand-600 to-brand-700 dark:from-brand-700 dark:to-brand-800 overflow-hidden"
	>
		<div class="absolute inset-0 opacity-10">
			<div
				class="absolute top-10 left-20 w-64 h-64 bg-white rounded-full blur-3xl animate-float"
			></div>
			<div
				class="absolute bottom-10 right-20 w-80 h-80 bg-white rounded-full blur-3xl animate-float-reverse"
			></div>
		</div>
		<div class="relative max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
			<h2 class="text-3xl md:text-4xl font-bold !text-white mb-4 drop-shadow-md">
				Get Clarity in Minutes
			</h2>
			<p class="text-lg !text-white mb-8 max-w-xl mx-auto drop-shadow-md">
				Small cohort. Rolling invites. Request access if you're ready.
			</p>
			<Button
				variant="secondary"
				size="lg"
				onclick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
				class="transform hover:scale-105 transition-transform duration-300"
			>
				Request Early Access
			</Button>
			<p class="text-sm !text-white/95 mt-6 drop-shadow-md">No credit card. Limited spots.</p>
		</div>
	</section>

	<Footer />
</div>

<SampleDecisionModal show={showSampleModal} onClose={() => (showSampleModal = false)} />
