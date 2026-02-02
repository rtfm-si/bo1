<script lang="ts">
	/**
	 * Landing Page - Board of One Closed Beta
	 * Hormozi Framework: Complete implementation with personality
	 * Design Token System: Applied throughout with alive animations
	 */
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import {
		HeroSection,
		MetricsGrid,
		FAQAccordion,
		SampleDecisionModal,
		SampleSelector
	} from '$lib/components/landing';
	import { useSectionObservers } from '$lib/hooks/useIntersectionObserver.svelte';
	import {
		valueBlocks,
		metrics,
		betaBenefits,
		decisionTypesRow1,
		decisionTypesRow2,
		faqs
	} from '$lib/data/landing-page-data';
	import { sampleDecisions } from '$lib/data/samples';
	import type { SampleDecision } from '$lib/data/samples';
	import { apiClient, type FeaturedDecision } from '$lib/api/client';
	import {
		initPageTracking,
		cleanupPageTracking,
		trackWaitlistSubmit,
		trackSignupClick
	} from '$lib/analytics/page-tracker';
	import {
		createOrganizationSchema,
		createSoftwareApplicationSchema,
		createHomepageFAQSchema,
		serializeJsonLd
	} from '$lib/utils/jsonld';

	// Waitlist form state
	let email = $state('');
	let loading = $state(false);
	let submitted = $state(false);
	let error = $state('');

	// Animation state
	let mounted = $state(false);

	// Sample decision modal
	let showSampleModal = $state(false);
	let currentSampleIndex = $state(0);

	// Featured decisions from API
	let featuredDecisions = $state<FeaturedDecision[]>([]);
	let featuredLoading = $state(true);

	// Get current sample and navigation functions
	const currentSample = $derived(sampleDecisions[currentSampleIndex]);

	function showSample(sample: SampleDecision) {
		const index = sampleDecisions.findIndex(s => s.id === sample.id);
		if (index !== -1) {
			currentSampleIndex = index;
		}
		showSampleModal = true;
	}

	function nextSample() {
		if (currentSampleIndex < sampleDecisions.length - 1) {
			currentSampleIndex++;
		}
	}

	function previousSample() {
		if (currentSampleIndex > 0) {
			currentSampleIndex--;
		}
	}

	function closeSampleModal() {
		showSampleModal = false;
	}

	// Section visibility tracking
	const visibility = useSectionObservers([
		'value-blocks',
		'features',
		'metrics-section',
		'beta-invite-section'
	]);

	onMount(async () => {
		mounted = true;
		// Initialize page analytics tracking
		initPageTracking();

		// Fetch featured decisions for homepage
		try {
			const response = await apiClient.getFeaturedDecisions(6);
			featuredDecisions = response.decisions;
		} catch {
			// Silently fail - will show sample decisions as fallback
		} finally {
			featuredLoading = false;
		}
	});

	onDestroy(() => {
		// Cleanup tracking on navigation
		cleanupPageTracking();
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
				// Track waitlist submission
				trackWaitlistSubmit(email);
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
	// JSON-LD structured data
	const organizationJsonLd = serializeJsonLd(createOrganizationSchema());
	const softwareAppJsonLd = serializeJsonLd(createSoftwareApplicationSchema());
	const faqJsonLd = serializeJsonLd(createHomepageFAQSchema([...faqs]));

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
	<title>Board of One - Management-Grade Thinking. No Management Required.</title>
	<meta
		name="description"
		content="A management operating system for founders making real calls. Compress management work, delay management hires, get senior-team leverage without senior-team overhead."
	/>
	<!-- Canonical -->
	<link rel="canonical" href="https://boardof.one/" />
	<!-- Open Graph -->
	<meta property="og:type" content="website" />
	<meta property="og:url" content="https://boardof.one/" />
	<meta property="og:title" content="Board of One - Management-Grade Thinking" />
	<meta property="og:description" content="A management operating system for founders making real calls. Get senior-team leverage without senior-team overhead." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<!-- Twitter -->
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Board of One - Management-Grade Thinking" />
	<meta name="twitter:description" content="A management operating system for founders making real calls. Get senior-team leverage without senior-team overhead." />
	<meta name="twitter:image" content="https://boardof.one/og-image.png" />

	<!-- JSON-LD Structured Data -->
	{@html `<script type="application/ld+json">${organizationJsonLd}</script>`}
	{@html `<script type="application/ld+json">${softwareAppJsonLd}</script>`}
	{@html `<script type="application/ld+json">${faqJsonLd}</script>`}
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
		animation: scroll-left 45s linear infinite;
		will-change: transform;
	}

	.carousel-group-reverse {
		display: flex;
		flex-shrink: 0;
		gap: 0;
		animation: scroll-right 52s linear infinite;
		will-change: transform;
	}

	.carousel-container:hover .carousel-group,
	.carousel-container:hover .carousel-group-reverse {
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

	@keyframes scroll-right {
		0% {
			transform: translateX(-100%);
		}
		100% {
			transform: translateX(0);
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
		onShowSample={() => {
			currentSampleIndex = 0;
			showSampleModal = true;
		}}
	/>

	<MetricsGrid {metrics} visible={visibility.get('metrics-section') ?? false} />

	<!-- Core Features Grid -->
	<section class="py-16 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800">
		<div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="text-center mb-10">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">
					A complete management <span class="text-brand-600 dark:text-brand-400 italic">operating system</span>
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
					Everything a solo founder needs to make decisions like a 10-person team.
				</p>
			</div>

			<div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
				<!-- Data Analysis -->
				<a href="/features/data-analysis" class="group bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
					<div class="w-12 h-12 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mb-4">
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600 dark:text-blue-400">
							<line x1="18" y1="20" x2="18" y2="10" />
							<line x1="12" y1="20" x2="12" y2="4" />
							<line x1="6" y1="20" x2="6" y2="14" />
						</svg>
					</div>
					<h3 class="font-bold text-lg text-neutral-900 dark:text-white mb-2">Data Analysis</h3>
					<p class="text-sm text-neutral-600 dark:text-neutral-400">Upload spreadsheets and data. Get insights that inform better decisions.</p>
					<span class="inline-flex items-center text-brand-600 dark:text-brand-400 text-sm font-medium mt-3 group-hover:underline">
						Learn more →
					</span>
				</a>

				<!-- Mentor Chat -->
				<a href="/features/mentor-chat" class="group bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
					<div class="w-12 h-12 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center mb-4">
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-600 dark:text-purple-400">
							<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
						</svg>
					</div>
					<h3 class="font-bold text-lg text-neutral-900 dark:text-white mb-2">Mentor Chat</h3>
					<p class="text-sm text-neutral-600 dark:text-neutral-400">1:1 conversations with AI mentors who know your business context.</p>
					<span class="inline-flex items-center text-brand-600 dark:text-brand-400 text-sm font-medium mt-3 group-hover:underline">
						Learn more →
					</span>
				</a>

				<!-- SEO Content -->
				<a href="/features/seo-generation" class="group bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
					<div class="w-12 h-12 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center mb-4">
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-green-600 dark:text-green-400">
							<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
							<polyline points="14 2 14 8 20 8" />
							<line x1="16" y1="13" x2="8" y2="13" />
							<line x1="16" y1="17" x2="8" y2="17" />
							<polyline points="10 9 9 9 8 9" />
						</svg>
					</div>
					<h3 class="font-bold text-lg text-neutral-900 dark:text-white mb-2">SEO Content</h3>
					<p class="text-sm text-neutral-600 dark:text-neutral-400">Turn decisions into SEO-optimized content. Build authority while you build.</p>
					<span class="inline-flex items-center text-brand-600 dark:text-brand-400 text-sm font-medium mt-3 group-hover:underline">
						Learn more →
					</span>
				</a>

				<!-- Industry Benchmarks -->
				<a href="/features/competitor-analysis" class="group bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
					<div class="w-12 h-12 rounded-lg bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center mb-4">
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-orange-600 dark:text-orange-400">
							<polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
						</svg>
					</div>
					<h3 class="font-bold text-lg text-neutral-900 dark:text-white mb-2">Industry Benchmarks</h3>
					<p class="text-sm text-neutral-600 dark:text-neutral-400">Compare your metrics against industry standards. Know where you stand.</p>
					<span class="inline-flex items-center text-brand-600 dark:text-brand-400 text-sm font-medium mt-3 group-hover:underline">
						Learn more →
					</span>
				</a>
			</div>
		</div>
	</section>

	<!-- Why This Matters - Management Work Reframe -->
	<section
		class="py-20 bg-neutral-50 dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-800"
	>
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
			<h2
				class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-4 text-center leading-tight"
			>
				<span class="text-neutral-700 dark:text-neutral-300 font-normal"
					>Most founders don't need another advisor.</span
				><br />
				<span class="text-brand-600 dark:text-brand-400 emphasis-word"
					>They need to <span class="italic font-extrabold">compress management work</span>.</span
				>
			</h2>

			<!-- The 6 Management Functions -->
			<div class="mt-12 max-w-3xl mx-auto">
				<p class="text-sm font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-6 text-center">
					What management actually does
				</p>
				<div class="grid grid-cols-2 md:grid-cols-3 gap-4">
					<!-- Function 1: Context aggregation -->
					<div class="group bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 text-center hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 cursor-default">
						<span class="text-brand-600 dark:text-brand-400 text-lg font-bold">1</span>
						<p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1">Context aggregation</p>
						<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 italic group-hover:hidden">What's going on?</p>
						<p class="text-xs text-brand-600 dark:text-brand-400 mt-1 hidden group-hover:block font-medium">Data Analysis + Industry Benchmarks</p>
					</div>
					<!-- Function 2: Option generation -->
					<div class="group bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 text-center hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 cursor-default">
						<span class="text-brand-600 dark:text-brand-400 text-lg font-bold">2</span>
						<p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1">Option generation</p>
						<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 italic group-hover:hidden">What could we do?</p>
						<p class="text-xs text-brand-600 dark:text-brand-400 mt-1 hidden group-hover:block font-medium">Mentor Chat + Deliberation</p>
					</div>
					<!-- Function 3: Risk & downside -->
					<div class="group bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 text-center hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 cursor-default">
						<span class="text-brand-600 dark:text-brand-400 text-lg font-bold">3</span>
						<p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1">Risk & downside pressure</p>
						<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 italic group-hover:hidden">What could break?</p>
						<p class="text-xs text-brand-600 dark:text-brand-400 mt-1 hidden group-hover:block font-medium">Expert Challenge Rounds</p>
					</div>
					<!-- Function 4: Alignment & trade-offs -->
					<div class="group bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 text-center hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 cursor-default">
						<span class="text-brand-600 dark:text-brand-400 text-lg font-bold">4</span>
						<p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1">Alignment & trade-offs</p>
						<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 italic group-hover:hidden">What do we prioritise?</p>
						<p class="text-xs text-brand-600 dark:text-brand-400 mt-1 hidden group-hover:block font-medium">Multi-Perspective Synthesis</p>
					</div>
					<!-- Function 5: Decision documentation -->
					<div class="group bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 text-center hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 cursor-default">
						<span class="text-brand-600 dark:text-brand-400 text-lg font-bold">5</span>
						<p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1">Decision documentation</p>
						<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 italic group-hover:hidden">Why did we choose this?</p>
						<p class="text-xs text-brand-600 dark:text-brand-400 mt-1 hidden group-hover:block font-medium">SEO Content Generation</p>
					</div>
					<!-- Function 6: Follow-through -->
					<div class="group bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 text-center hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 cursor-default">
						<span class="text-brand-600 dark:text-brand-400 text-lg font-bold">6</span>
						<p class="text-sm text-neutral-700 dark:text-neutral-300 mt-1">Follow-through</p>
						<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 italic group-hover:hidden">Course correction</p>
						<p class="text-xs text-brand-600 dark:text-brand-400 mt-1 hidden group-hover:block font-medium">Actions + Kanban + Replanning</p>
					</div>
				</div>
			</div>

			<p class="text-lg font-semibold text-brand-600 dark:text-brand-400 text-center mt-10">
				Most managers don't decide. They prepare decisions.<br />
				<span class="text-neutral-700 dark:text-neutral-300 font-normal">Board of One does that work instantly.</span>
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

			<!-- Infinite horizontal carousel - Two rows -->
			<div class="relative w-full space-y-4">
				<!-- Gradient fade edges -->
				<div
					class="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-white dark:from-neutral-900 to-transparent z-10 pointer-events-none"
				></div>
				<div
					class="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-white dark:from-neutral-900 to-transparent z-10 pointer-events-none"
				></div>

				<!-- Row 1: Scrolling left (forwards) -->
				<div
					class="carousel-container text-lg font-medium text-neutral-700 dark:text-neutral-300"
				>
					<div class="carousel-group">
						{#each decisionTypesRow1 as decision, i (i)}
							<span class="carousel-item">{decision}</span>
						{/each}
					</div>
					<div class="carousel-group" aria-hidden="true">
						{#each decisionTypesRow1 as decision, i (`duplicate-${i}`)}
							<span class="carousel-item">{decision}</span>
						{/each}
					</div>
				</div>

				<!-- Row 2: Scrolling right (backwards) -->
				<div
					class="carousel-container text-lg font-medium text-neutral-600 dark:text-neutral-400"
				>
					<div class="carousel-group-reverse">
						{#each decisionTypesRow2 as decision, i (`row2-${i}`)}
							<span class="carousel-item">{decision}</span>
						{/each}
					</div>
					<div class="carousel-group-reverse" aria-hidden="true">
						{#each decisionTypesRow2 as decision, i (`row2-duplicate-${i}`)}
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

			<!-- Value Blocks / Features -->
			<div id="features" class="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto mt-16">
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

	<!-- Who is it for - Sharpened ICP -->
	<section
		id="who-its-for"
		class="py-24 bg-neutral-50 dark:bg-neutral-800 border-y border-neutral-200 dark:border-neutral-800"
	>
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<!-- Primary ICP Statement -->
			<div class="text-center mb-12">
				<h2
					class="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-neutral-100 mb-6 leading-tight"
				>
					<span class="text-neutral-700 dark:text-neutral-300 font-normal">Built for founders who</span><br />
					<span class="text-brand-600 dark:text-brand-400 emphasis-word"
						>operate at the <span class="italic font-extrabold">next org size</span></span
					>
				</h2>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
					Founders doing £10k–£2m ARR who feel the drag of decisions they shouldn't still be making.
				</p>
			</div>

			<!-- Aspirational One-Liner -->
			<div class="text-center mb-16">
				<p class="text-2xl md:text-3xl font-bold text-brand-600 dark:text-brand-400">
					Run a 10-person company with a 3-person team.
				</p>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
				<!-- Should hire but can't justify -->
				<div
					class="bg-white dark:bg-neutral-900 rounded-lg p-8 border border-neutral-200 dark:border-neutral-700 card-hover border-glow"
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
							<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
							<circle cx="9" cy="7" r="4" />
							<path d="M22 21v-2a4 4 0 0 0-3-3.87" />
							<path d="M16 3.13a4 4 0 0 1 0 7.75" />
						</svg>
					</div>
					<h3 class="font-bold text-xl text-neutral-900 dark:text-neutral-100 mb-3">
						Delay Management Hires
					</h3>
					<ul class="space-y-2 text-neutral-600 dark:text-neutral-400">
						<li class="flex items-start gap-2">
							<span class="text-brand-600 dark:text-brand-400 mt-1">→</span>
							<span>Should hire a Head of X but can't justify £100k yet</span>
						</li>
						<li class="flex items-start gap-2">
							<span class="text-brand-600 dark:text-brand-400 mt-1">→</span>
							<span>Need senior thinking without senior headcount</span>
						</li>
						<li class="flex items-start gap-2">
							<span class="text-brand-600 dark:text-brand-400 mt-1">→</span>
							<span>Get leverage before you get layers</span>
						</li>
					</ul>
				</div>

				<!-- Scaling from 1 → 20 -->
				<div
					class="bg-white dark:bg-neutral-900 rounded-lg p-8 border border-neutral-200 dark:border-neutral-700 card-hover border-glow"
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
							<line x1="12" y1="20" x2="12" y2="10" />
							<line x1="18" y1="20" x2="18" y2="4" />
							<line x1="6" y1="20" x2="6" y2="16" />
						</svg>
					</div>
					<h3 class="font-bold text-xl text-neutral-900 dark:text-neutral-100 mb-3">
						Reduce Coordination Tax
					</h3>
					<ul class="space-y-2 text-neutral-600 dark:text-neutral-400">
						<li class="flex items-start gap-2">
							<span class="text-brand-600 dark:text-brand-400 mt-1">→</span>
							<span>Scaling from 1 → 20 and decisions are stacking up</span>
						</li>
						<li class="flex items-start gap-2">
							<span class="text-brand-600 dark:text-brand-400 mt-1">→</span>
							<span>You're the bottleneck on every strategic call</span>
						</li>
						<li class="flex items-start gap-2">
							<span class="text-brand-600 dark:text-brand-400 mt-1">→</span>
							<span>Compress weeks of back-and-forth into minutes</span>
						</li>
					</ul>
				</div>

				<!-- Lean team operators -->
				<div
					class="bg-white dark:bg-neutral-900 rounded-lg p-8 border border-neutral-200 dark:border-neutral-700 card-hover border-glow"
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
							<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
						</svg>
					</div>
					<h3 class="font-bold text-xl text-neutral-900 dark:text-neutral-100 mb-3">
						Operate Without The Org
					</h3>
					<ul class="space-y-2 text-neutral-600 dark:text-neutral-400">
						<li class="flex items-start gap-2">
							<span class="text-brand-600 dark:text-brand-400 mt-1">→</span>
							<span>Running a lean team by choice, not compromise</span>
						</li>
						<li class="flex items-start gap-2">
							<span class="text-brand-600 dark:text-brand-400 mt-1">→</span>
							<span>Want the output of hierarchy without the overhead</span>
						</li>
						<li class="flex items-start gap-2">
							<span class="text-brand-600 dark:text-brand-400 mt-1">→</span>
							<span>Same headcount, higher leverage</span>
						</li>
					</ul>
				</div>
			</div>
		</div>
	</section>

	<!-- Before/After - Management Stack Framing -->
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
					>From the <span class="italic font-bold">old stack</span> to the</span
				>
				<span class="text-brand-600 dark:text-brand-400 italic font-extrabold emphasis-word"
					>new stack</span
				>
			</h2>
			<div class="grid md:grid-cols-2 gap-12 items-stretch">
				<!-- Old Stack -->
				<div class="relative shake-stuck">
					<div
						class="absolute -inset-0.5 bg-gradient-to-br from-error-300/10 to-warning-300/10 dark:from-error-500/10 dark:to-warning-500/10 rounded-xl blur-sm"
					></div>
					<div
						class="relative bg-white dark:bg-neutral-800 rounded-xl p-8 border-2 border-neutral-300 dark:border-neutral-600 hover:border-neutral-400 dark:hover:border-neutral-500 transition-all duration-300 shadow-md h-full"
					>
						<div
							class="text-xs font-bold text-error-600 dark:text-error-400 mb-6 uppercase tracking-wider flex items-center gap-2"
						>
							<span class="inline-block w-2 h-2 bg-error-500 rounded-full opacity-50"></span>
							Old Stack
						</div>
						<ul class="space-y-3">
							<li class="flex items-center gap-3 text-neutral-600 dark:text-neutral-400">
								<span class="text-neutral-400">✗</span>
								<span>Meetings</span>
							</li>
							<li class="flex items-center gap-3 text-neutral-600 dark:text-neutral-400">
								<span class="text-neutral-400">✗</span>
								<span>Status decks</span>
							</li>
							<li class="flex items-center gap-3 text-neutral-600 dark:text-neutral-400">
								<span class="text-neutral-400">✗</span>
								<span>Opinions</span>
							</li>
							<li class="flex items-center gap-3 text-neutral-600 dark:text-neutral-400">
								<span class="text-neutral-400">✗</span>
								<span>Memory</span>
							</li>
							<li class="flex items-center gap-3 text-neutral-600 dark:text-neutral-400">
								<span class="text-neutral-400">✗</span>
								<span>Politics</span>
							</li>
						</ul>
					</div>
				</div>

				<!-- New Stack -->
				<div class="relative after-card-wrapper nod-clarity">
					<div
						class="absolute -inset-0.5 bg-gradient-to-br from-brand-400/15 to-success-400/10 dark:from-brand-500/20 dark:to-success-500/15 rounded-xl blur-sm"
					></div>
					<div
						class="relative bg-white dark:bg-neutral-800 rounded-xl p-8 border-2 border-brand-200 dark:border-brand-700 hover:border-brand-300 dark:hover:border-brand-600 transition-all duration-300 shadow-md h-full"
					>
						<div
							class="text-xs font-bold text-brand-600 dark:text-brand-400 mb-6 uppercase tracking-wider flex items-center gap-2"
						>
							<span class="inline-block w-2 h-2 bg-success-500 rounded-full"></span>
							New Stack
						</div>
						<ul class="space-y-3">
							<li class="flex items-center gap-3 text-neutral-900 dark:text-neutral-100 font-medium">
								<span class="text-brand-600 dark:text-brand-400">✓</span>
								<span>Structured deliberation</span>
							</li>
							<li class="flex items-center gap-3 text-neutral-900 dark:text-neutral-100 font-medium">
								<span class="text-brand-600 dark:text-brand-400">✓</span>
								<span>Named perspectives with defined biases</span>
							</li>
							<li class="flex items-center gap-3 text-neutral-900 dark:text-neutral-100 font-medium">
								<span class="text-brand-600 dark:text-brand-400">✓</span>
								<span>Evidence capture</span>
							</li>
							<li class="flex items-center gap-3 text-neutral-900 dark:text-neutral-100 font-medium">
								<span class="text-brand-600 dark:text-brand-400">✓</span>
								<span>Decision logs</span>
							</li>
							<li class="flex items-center gap-3 text-neutral-900 dark:text-neutral-100 font-medium">
								<span class="text-brand-600 dark:text-brand-400">✓</span>
								<span>Action tracking + re-planning</span>
							</li>
						</ul>
					</div>
				</div>
			</div>

			<!-- OS Framing -->
			<div class="text-center mt-12">
				<p class="text-lg text-neutral-600 dark:text-neutral-400">
					Board of One is a <span class="font-bold text-brand-600 dark:text-brand-400">management operating system</span>.
				</p>
				<p class="text-neutral-500 dark:text-neutral-500 mt-1">
					Not a tool. Not an assistant. An <span class="font-bold text-brand-600 dark:text-brand-400">OS</span>.
				</p>
			</div>
		</div>
	</section>

	<!-- Beyond Decisions -->
	<section class="py-16 bg-neutral-50 dark:bg-neutral-800 border-y border-neutral-200 dark:border-neutral-700">
		<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
			<h3 class="text-xl md:text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
				The decision is just the start.
			</h3>
			<p class="text-neutral-600 dark:text-neutral-400 mb-2 leading-relaxed">
				Track actions through to completion. Replan when reality shifts.
			</p>
			<p class="text-neutral-600 dark:text-neutral-400 mb-6 leading-relaxed">
				Connect your data. Understand your competition. Feed outcomes back into future decisions.
			</p>
			<p class="text-neutral-900 dark:text-neutral-100 font-medium mb-6">
				A complete operating system — not just a decision tool.
			</p>
			<a
				href="/features"
				class="inline-flex items-center gap-2 text-brand-600 dark:text-brand-400 font-medium hover:text-brand-700 dark:hover:text-brand-300 transition-colors"
			>
				Explore all capabilities
				<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M5 12h14M12 5l7 7-7 7"/>
				</svg>
			</a>
		</div>
	</section>

	<!-- Sample Decision Selector -->
	{#if featuredDecisions.length > 0}
		<SampleSelector decisions={featuredDecisions} />
	{:else}
		<SampleSelector samples={sampleDecisions} onSelectSample={showSample} />
	{/if}

	<!-- Killer One-Liner -->
	<section
		class="py-16 bg-gradient-to-r from-neutral-100 to-neutral-50 dark:from-neutral-800 dark:to-neutral-900 border-y border-neutral-200 dark:border-neutral-700"
	>
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
			<blockquote class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 leading-relaxed">
				"Board of One is what a great management team does —<br class="hidden md:inline" />
				<span class="text-brand-600 dark:text-brand-400 italic">without the management team.</span>"
			</blockquote>
		</div>
	</section>

	<!-- Social Proof -->
	<section
		class="py-16 bg-white dark:bg-neutral-900 border-y border-neutral-200 dark:border-neutral-800"
	>
		<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="grid md:grid-cols-3 gap-8">
				<div class="text-center">
					<p class="text-neutral-700 dark:text-neutral-300 leading-relaxed mb-3">
						"Like having a management team on tap."
					</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">— Solo Founder, SaaS</p>
				</div>
				<div class="text-center">
					<p class="text-neutral-700 dark:text-neutral-300 leading-relaxed mb-3">
						"I was going to hire a consultant. This is faster and 1% of the cost."
					</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">— E-commerce, £800k ARR</p>
				</div>
				<div class="text-center">
					<p class="text-neutral-700 dark:text-neutral-300 leading-relaxed mb-3">
						"Collapsed a week of back-and-forth into one session."
					</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">— Agency Owner</p>
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
					<span class="text-neutral-700 dark:text-neutral-300 font-normal">Delay your next</span>
					<span class="text-brand-600 dark:text-brand-400 italic font-extrabold emphasis-word"
						>management hire</span
					>
				</h2>
				<p class="text-lg text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
					Board of One is in closed beta for operators who make real calls.
				</p>
			</div>

			<div
				class="bg-white dark:bg-neutral-800 rounded-xl p-8 md:p-12 border border-neutral-200 dark:border-neutral-700"
			>
				<h3 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">Beta access includes:</h3>
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
						Rolling invites. First-come, first-served.
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

	<!-- Blog Section -->
	<section class="py-16 bg-neutral-50 dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
			<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
				From <span class="text-brand-600 dark:text-brand-400 italic">The Board Room</span>
			</h2>
			<p class="text-lg text-neutral-600 dark:text-neutral-400 mb-8 max-w-2xl mx-auto">
				Insights on decision-making, startup strategy, and AI-powered advisory for founders building solo.
			</p>
			<Button variant="outline" size="lg" onclick={() => goto('/blog')}>
				Read the Blog →
			</Button>
		</div>
	</section>

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
				Management leverage. Minutes, not meetings.
			</h2>
			<p class="text-lg !text-white mb-8 max-w-xl mx-auto drop-shadow-md">
				For founders making real calls. Request access if you're ready.
			</p>
			<Button
				variant="secondary"
				size="lg"
				onclick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
				class="transform hover:scale-105 transition-transform duration-300"
			>
				Request Early Access
			</Button>
			<p class="text-sm !text-white/95 mt-6 drop-shadow-md">No credit card. Rolling invites.</p>
		</div>
	</section>

	<Footer />
</div>

<SampleDecisionModal
	show={showSampleModal}
	sample={currentSample}
	onClose={closeSampleModal}
	onPrevious={currentSampleIndex > 0 ? previousSample : undefined}
	onNext={currentSampleIndex < sampleDecisions.length - 1 ? nextSample : undefined}
	showNavigation={true}
/>
