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
		slug: 'delay-management-hires',
		title: 'Delay Your Next Management Hire',
		description: 'Get management-level thinking without the £100k+ headcount. Board of One gives you the strategic capability you need before you can afford the person.',
		datePublished: '2025-01-15',
		dateModified: '2025-01-20'
	};

	const faqs = [
		{
			question: 'How can software replace a Head of Marketing/Sales/Product?',
			answer: 'It doesn\'t replace them entirely—it replaces the strategic thinking and framework development you\'d get from them. When you\'re at £500k ARR, you don\'t need someone managing a team of 10. You need someone helping you think through positioning, channel strategy, and prioritization. Board of One provides that thinking, documented and actionable, until you\'re ready to hire someone to execute at scale.'
		},
		{
			question: 'What stage companies benefit most from this?',
			answer: 'Typically £200k-£2M ARR. Early enough that a £100k+ hire would be a significant portion of your burn, but mature enough that you\'re facing decisions that need management-level thinking. You\'re past the "just ship it" phase but not yet at the "we need a leadership team" phase.'
		},
		{
			question: 'Won\'t I eventually need to hire these people anyway?',
			answer: 'Yes—and you\'ll hire them better. Board of One helps you develop clear frameworks, documented decisions, and strategic clarity. When you do hire, you\'ll know exactly what you need, have materials to onboard them, and can evaluate candidates against real criteria rather than vague "senior experience."'
		},
		{
			question: 'How is this different from just asking ChatGPT for advice?',
			answer: 'ChatGPT gives generic advice without context. Board of One knows your business model, your metrics, your competitive positioning, and your constraints. When you ask about pricing strategy, it references your current margins and target market. When you discuss channel prioritization, it considers your CAC and runway. Context transforms generic advice into actionable guidance.'
		},
		{
			question: 'What kinds of "Head of X" thinking does Board of One provide?',
			answer: 'Strategic frameworks for marketing (positioning, messaging, channel strategy), sales (pricing, process, qualification), product (prioritization, roadmapping, user research synthesis), operations (process design, efficiency), and finance (forecasting, scenario planning, metrics frameworks). Not execution—thinking and planning.'
		},
		{
			question: 'How much time does this actually save?',
			answer: 'Founders typically spend 5-10 hours per week in strategic thinking mode—reading, researching, debating options internally. Board of One compresses this by giving you structured frameworks, multi-perspective analysis, and clear recommendations in minutes instead of hours. More importantly, it surfaces considerations you\'d otherwise miss.'
		}
	];

	const breadcrumbSchema = createUseCaseBreadcrumbSchema(pageConfig);
	const articleSchema = createUseCasePageSchema(pageConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>Delay Management Hires - Get Senior Thinking Without Headcount | Board of One</title>
	<meta name="description" content="Can't justify a £100k+ Head of Marketing hire? Get management-level strategic thinking now, hire better later. Board of One helps founders delay expensive hires." />
	<link rel="canonical" href="https://boardof.one/use-cases/delay-management-hires" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/use-cases/delay-management-hires" />
	<meta property="og:title" content="Delay Management Hires - Get Senior Thinking Without Headcount" />
	<meta property="og:description" content="Can't justify a £100k+ Head of Marketing hire? Get management-level strategic thinking now." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Delay Management Hires - Get Senior Thinking Without Headcount" />
	<meta name="twitter:description" content="Can't justify a £100k+ Head of Marketing hire? Get management-level strategic thinking now." />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Use Case</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Delay Your Next Management Hire
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					You need a Head of Marketing. Or Sales. Or Product. But at £100k+ fully loaded, you can't justify it yet. What if you could get the thinking without the headcount?
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The problem: you need the role, not the person
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						At your stage, you don't need someone managing a marketing team of 10. You need someone who can think through positioning, develop channel strategy, and help you prioritize what actually matters. You need the <em>capability</em>, not the org chart entry.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						But good senior people cost £80-150k+ fully loaded. For a company doing £500k-£1M in ARR, that's a massive commitment. And frankly, most of what you'd pay them for isn't execution—it's strategic thinking and decision-making frameworks. The stuff that happens in their heads.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						So you either hire prematurely (and burn runway), hire underqualified (and get underqualified thinking), or muddle through yourself (and miss things you don't know you're missing).
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
						Board of One gives you management-level strategic thinking on demand. Not generic advice—specific frameworks, recommendations, and analysis grounded in your actual business context.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Need to develop a pricing strategy? Get multi-perspective analysis that considers your margins, market, and competitive positioning. Trying to prioritize product features? Get frameworks that weigh customer feedback, strategic fit, and resource constraints.
					</p>
				</div>
				<div class="space-y-6">
					<div class="flex gap-4">
						<div class="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-bold">1</div>
						<div>
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-1">Describe the decision or challenge</h3>
							<p class="text-neutral-600 dark:text-neutral-400">"Should we go upmarket to enterprise or double down on SMB?" or "How should we structure our pricing tiers?"</p>
						</div>
					</div>
					<div class="flex gap-4">
						<div class="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-bold">2</div>
						<div>
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-1">Get multi-perspective analysis</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Expert personas debate the decision—marketing, finance, operations, product—each bringing their lens to your specific situation.</p>
						</div>
					</div>
					<div class="flex gap-4">
						<div class="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-bold">3</div>
						<div>
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-1">Receive documented recommendations</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Clear next steps, reasoning documented, trade-offs explicit. Not just what to do, but why—so you can defend and adapt the decision.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Who This Is For -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					Who this is for
				</h2>
				<div class="grid md:grid-cols-3 gap-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Stage</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">£200k-£2M ARR. Past the "just ship it" phase, but before the "we need a leadership team" phase.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Situation</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">You're making decisions that need senior thinking, but can't justify senior salaries yet.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Constraint</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Runway-conscious. Every hire needs to be justified. You want to delay until you're truly ready.</p>
					</div>
				</div>
			</div>
		</section>

		<!-- What You Get -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					What you get instead of a hire
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Marketing strategy thinking</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Positioning and messaging frameworks</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Channel prioritization and budget allocation</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Competitive differentiation strategy</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Content and demand gen planning</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Sales strategy thinking</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Pricing strategy and packaging</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Sales process and qualification criteria</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Segment targeting and expansion strategy</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Win/loss analysis and competitive response</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Product strategy thinking</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Feature prioritization frameworks</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Roadmap sequencing and trade-offs</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>User research synthesis and insights</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Platform vs. feature decisions</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Operations & finance thinking</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Process design and efficiency</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Financial modeling and scenario planning</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Metrics frameworks and KPIs</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Resource allocation and budgeting</li>
						</ul>
					</div>
				</div>
			</div>
		</section>

		<!-- FAQ Section -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					Frequently asked questions
				</h2>
				<div class="space-y-6">
					{#each faqs as faq}
						<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">{faq.question}</h3>
							<p class="text-neutral-600 dark:text-neutral-400">{faq.answer}</p>
						</div>
					{/each}
				</div>
			</div>
		</section>

		<!-- Related Use Cases -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-6 text-center">
					Related use cases
				</h2>
				<div class="grid md:grid-cols-2 gap-4 mb-8">
					<a href="/use-cases/founder-bottleneck" class="block bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Break the Founder Bottleneck</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Stop being the blocker on every decision</p>
					</a>
					<a href="/use-cases/operating-without-org" class="block bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Operating Without an Org Chart</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Run lean by choice, not necessity</p>
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
