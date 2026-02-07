<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import {
		createUseCasePageSchema,
		createUseCaseBreadcrumbSchema,
		createFeatureFAQSchema,
		serializeJsonLd,
		type UseCasePageConfig
	} from '$lib/utils/jsonld';

	const pageConfig: UseCasePageConfig = {
		slug: 'advisor-alternative',
		title: 'On-Demand Expert Guidance',
		description: 'Skip the expensive advisors and sporadic availability. Board of One gives you expertise when you need it, not when they\'re free.',
		datePublished: '2025-01-15',
		dateModified: '2025-01-20'
	};

	const faqs = [
		{
			question: 'Can AI really replace human advisors?',
			answer: 'Not entirely—and that\'s not the goal. Human advisors bring relationships, introductions, and pattern-matching from direct experience. What Board of One replaces is the strategic thinking part: frameworks, analysis, and recommendations. The stuff that happens between your quarterly advisor calls. For many founders, that\'s 80% of what they needed anyway.'
		},
		{
			question: 'What about the relationship and networking value of advisors?',
			answer: 'Advisors who provide real relationship value—introductions, references, credibility—are worth keeping. But many advisory relationships are primarily about getting strategic input, and that input comes quarterly at best. Board of One handles the thinking; save your equity for advisors who open doors.'
		},
		{
			question: 'How does this compare to the cost of advisors?',
			answer: 'Advisors typically receive 0.25-1% equity for monthly or quarterly calls, plus potential cash retainers of £500-2,000/month. For a company eventually worth £10M, that 0.5% advisor equity costs £50,000. Board of One provides unlimited access to strategic guidance for a fraction of that, without equity dilution.'
		},
		{
			question: 'My advisor has 20 years of industry experience. Can AI match that?',
			answer: 'Not the pattern-matching from lived experience—that\'s valuable and irreplaceable. But Board of One can provide broader perspective (multiple viewpoints, not just one person\'s lens), deeper consistency (same quality every time, not dependent on their mood or schedule), and immediate availability. Many experienced advisors are great at "I\'ve seen this before" and less great at systematic analysis.'
		},
		{
			question: 'When should I still use human advisors?',
			answer: 'For introductions and networking. For industry-specific pattern matching ("I\'ve seen this exact situation 10 times"). For board-level credibility with investors. For emotional support and mentorship. For anything requiring real relationships. These are human strengths. For strategic analysis and decision frameworks—that\'s where Board of One shines.'
		},
		{
			question: 'How quickly can I get guidance compared to waiting for an advisor call?',
			answer: 'Immediately. No scheduling, no waiting for their availability, no "let\'s discuss next month." When you\'re facing a decision at 10pm on a Sunday, Board of One is there. When you need to think through something before a Monday meeting, you can do it now.'
		}
	];

	const breadcrumbSchema = createUseCaseBreadcrumbSchema(pageConfig);
	const articleSchema = createUseCasePageSchema(pageConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>Advisor Alternative - On-Demand Expert Guidance for Founders | Board of One</title>
	<meta name="description" content="Advisors are expensive, busy, and only available quarterly. Board of One gives you strategic guidance on demand—no equity, no scheduling, no waiting." />
	<link rel="canonical" href="https://boardof.one/use-cases/advisor-alternative" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/use-cases/advisor-alternative" />
	<meta property="og:title" content="Advisor Alternative - On-Demand Expert Guidance for Founders" />
	<meta property="og:description" content="Advisors are expensive and busy. Get strategic guidance on demand—no equity, no waiting." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Advisor Alternative - On-Demand Expert Guidance for Founders" />
	<meta name="twitter:description" content="Advisors are expensive and busy. Get strategic guidance on demand—no equity, no waiting." />
	<meta name="twitter:image" content="https://boardof.one/og-image.png" />
	{@html `<script type="application/ld+json">${serializeJsonLd(breadcrumbSchema)}</script>`}
	{@html `<script type="application/ld+json">${serializeJsonLd(articleSchema)}</script>`}
	{@html `<script type="application/ld+json">${serializeJsonLd(faqSchema)}</script>`}
</svelte:head>

<div class="min-h-screen flex flex-col bg-white dark:bg-neutral-900">
	<Header />

	<main class="flex-1">
		<!-- Hero -->
		<section class="py-16 md:py-24 bg-gradient-to-b from-brand-50 to-white dark:from-neutral-800 dark:to-neutral-900">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<a href="/use-cases" class="inline-flex items-center gap-2 text-brand-600 dark:text-brand-400 text-sm font-medium mb-6 hover:text-brand-700 dark:hover:text-brand-300">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
					All Use Cases
				</a>
				<div class="flex items-center gap-3 mb-4">
					<div class="w-12 h-12 rounded-xl bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Use Case</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					On-Demand Expert Guidance
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Advisors cost equity and are available quarterly. You need help now, not "let's schedule something for next month."
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The problem: expensive, busy, and misaligned
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Traditional advisors want 0.25-1% equity plus cash retainers. They're available for a monthly or quarterly call—if they're not traveling, sick, or just too busy with their portfolio of 15 other companies.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						You don't need help on their schedule. You need help when you're facing a decision. At 10pm on Sunday. Before the board meeting on Monday. Right now, while the opportunity is hot.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						And honestly? Many advisor calls are spent getting them back up to speed on your context. By the time they understand the situation, the call is over. Next month: repeat.
					</p>
				</div>
			</div>
		</section>

		<!-- The Solution -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The Board of One solution
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none mb-10">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Board of One gives you expert guidance on demand. No scheduling, no equity, no getting them up to speed. Your business context is always loaded. Multiple expert perspectives are always available. The guidance you need, when you need it.
					</p>
				</div>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-4 flex items-center gap-2">
							Traditional Advisors
						</h3>
						<ul class="space-y-3 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-error-500">✗</span>0.25-1% equity + cash retainer</li>
							<li class="flex items-start gap-2"><span class="text-error-500">✗</span>Monthly or quarterly availability</li>
							<li class="flex items-start gap-2"><span class="text-error-500">✗</span>Needs context re-sync every call</li>
							<li class="flex items-start gap-2"><span class="text-error-500">✗</span>One perspective (their background)</li>
							<li class="flex items-start gap-2"><span class="text-error-500">✗</span>Scheduling friction and delays</li>
							<li class="flex items-start gap-2"><span class="text-error-500">✗</span>Quality varies by their mood/energy</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-4 flex items-center gap-2">
							Board of One
						</h3>
						<ul class="space-y-3 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-success-500">✓</span>Fixed monthly cost, no equity</li>
							<li class="flex items-start gap-2"><span class="text-success-500">✓</span>Available 24/7, instantly</li>
							<li class="flex items-start gap-2"><span class="text-success-500">✓</span>Context always loaded</li>
							<li class="flex items-start gap-2"><span class="text-success-500">✓</span>Multiple expert perspectives</li>
							<li class="flex items-start gap-2"><span class="text-success-500">✓</span>No scheduling, immediate access</li>
							<li class="flex items-start gap-2"><span class="text-success-500">✓</span>Consistent quality every time</li>
						</ul>
					</div>
				</div>
			</div>
		</section>

		<!-- Cost Comparison -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					The real cost of advisors
				</h2>
				<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-8 border border-neutral-200 dark:border-neutral-700">
					<div class="grid md:grid-cols-3 gap-8">
						<div class="text-center">
							<div class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">0.5%</div>
							<div class="text-sm text-neutral-600 dark:text-neutral-400">Typical advisor equity</div>
						</div>
						<div class="text-center">
							<div class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">£50,000</div>
							<div class="text-sm text-neutral-600 dark:text-neutral-400">Value at £10M exit</div>
						</div>
						<div class="text-center">
							<div class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">12 calls/year</div>
							<div class="text-sm text-neutral-600 dark:text-neutral-400">Typical advisor time</div>
						</div>
					</div>
					<p class="text-center text-neutral-600 dark:text-neutral-400 mt-6 text-sm">
						That's £4,000+ per hour of advice at a £10M exit. Plus cash retainers of £500-2,000/month.
					</p>
				</div>
			</div>
		</section>

		<!-- Who This Is For -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					Who this is for
				</h2>
				<div class="grid md:grid-cols-3 gap-6">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Stage</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Pre-seed to Series A. When equity is precious and advisors are expensive relative to your resources.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Situation</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">You've considered advisors but balked at the equity cost. Or you have advisors but can't get time with them when you need it.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Need</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Strategic guidance more than networking. You need help thinking through decisions, not introductions to VCs.</p>
					</div>
				</div>
			</div>
		</section>

		<!-- When to Use Both -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					When human advisors still make sense
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Board of One doesn't replace everything advisors provide. Keep advisors who:
					</p>
					<ul class="mt-4 space-y-3 text-lg text-neutral-600 dark:text-neutral-400">
						<li><strong>Open doors</strong>—introductions to investors, customers, partners</li>
						<li><strong>Provide credibility</strong>—their name on your board signals quality</li>
						<li><strong>Have seen your exact situation</strong>—specific pattern-matching from lived experience</li>
						<li><strong>Offer mentorship</strong>—emotional support, career guidance, personal development</li>
					</ul>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						For strategic analysis, decision frameworks, and thinking through options—that's where Board of One excels. Save your equity for advisors who provide irreplaceable human value.
					</p>
				</div>
			</div>
		</section>

		<!-- FAQ Section -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					Frequently asked questions
				</h2>
				<div class="space-y-6">
					{#each faqs as faq}
						<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">{faq.question}</h3>
							<p class="text-neutral-600 dark:text-neutral-400">{faq.answer}</p>
						</div>
					{/each}
				</div>
			</div>
		</section>

		<!-- Related Use Cases -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-6 text-center">
					Related use cases
				</h2>
				<div class="grid md:grid-cols-2 gap-4 mb-8">
					<a href="/use-cases/strategic-decisions" class="block bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Making Strategic Decisions Solo</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Big decisions without a board</p>
					</a>
					<a href="/use-cases/delay-management-hires" class="block bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Delay Your Next Management Hire</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Get management thinking without the headcount</p>
					</a>
				</div>
				<div class="text-center">
					<Button variant="brand" size="lg" onclick={() => window.location.href = '/'}>
						Request Early Access
					</Button>
				</div>
			</div>
		</section>
	</main>

	<Footer />
</div>
