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
		slug: 'operating-without-org',
		title: 'Operating Without an Org Chart',
		description: 'Run lean by choice, not necessity. Board of One gives you full management capability without building a management team.',
		datePublished: '2025-01-15',
		dateModified: '2025-01-20'
	};

	const faqs = [
		{
			question: 'Why would someone choose to stay lean?',
			answer: 'Many successful founders prefer staying lean: higher per-capita economics, faster decision-making, less management overhead, more flexibility. Basecamp, Mailchimp (pre-acquisition), and countless profitable businesses chose this path. Staying lean isn\'t failure to grow—it\'s a legitimate strategy. The challenge is getting management-quality thinking without management-quantity people.'
		},
		{
			question: 'How is this different from being understaffed?',
			answer: 'Understaffing means you can\'t execute what you need to. Operating lean means you\'ve designed your business to require fewer people. The difference is capability vs. capacity. Board of One addresses capability—the strategic thinking, frameworks, and decision-making that would otherwise require senior hires. Capacity is a different problem.'
		},
		{
			question: 'What management functions does Board of One replace?',
			answer: 'Strategic thinking, not execution. When you need to develop a pricing strategy, evaluate a market opportunity, or decide between competing priorities—that\'s Board of One. When you need someone to run campaigns, manage accounts, or ship features—that\'s hiring. The management "thinking" layer is what we replace, not the management "doing" layer.'
		},
		{
			question: 'Can I really run a multi-million dollar business without executives?',
			answer: 'Many do. The question is whether you have the management capabilities, not the management titles. A solo founder with great systems, clear thinking, and good advisors can outperform a company with a bloated org chart. Board of One provides the structured thinking—you still need to execute well and hire appropriately for execution capacity.'
		},
		{
			question: 'When does this approach stop working?',
			answer: 'When you need execution capacity, not capability. If you can\'t personally oversee all the work that needs doing, you need people. Board of One doesn\'t solve the "there\'s too much work" problem—it solves the "I need senior-level thinking on this decision" problem. Most businesses hit execution constraints before capability constraints.'
		},
		{
			question: 'How do I know if I\'m staying lean vs just underfunding growth?',
			answer: 'Staying lean works when you\'re profitable and have chosen to optimize for margins over growth rate. If you\'re burning money and can\'t hire because of funding, that\'s different. Board of One helps in both cases, but it\'s not a substitute for having adequate resources to execute your actual strategy.'
		}
	];

	const breadcrumbSchema = createUseCaseBreadcrumbSchema(pageConfig);
	const articleSchema = createUseCasePageSchema(pageConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>Operating Without an Org Chart - Lean Startup Management | Board of One</title>
	<meta name="description" content="Stay lean by choice, not necessity. Board of One gives founders management-level capability without management-level headcount. Run a sophisticated business without a big team." />
	<link rel="canonical" href="https://boardof.one/use-cases/operating-without-org" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/use-cases/operating-without-org" />
	<meta property="og:title" content="Operating Without an Org Chart - Lean Startup Management" />
	<meta property="og:description" content="Stay lean by choice. Get management capability without the org chart." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Operating Without an Org Chart - Lean Startup Management" />
	<meta name="twitter:description" content="Stay lean by choice. Get management capability without the org chart." />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Use Case</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Operating Without an Org Chart
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					You've chosen to stay lean. Not because you can't grow—because you don't want to manage a big team. But strategic decisions still need sophisticated thinking.
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The challenge: capability vs. capacity
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						You're not understaffed—you've designed your business to run lean. Higher margins, faster decisions, less bureaucracy. But every business advice article assumes you have a leadership team. Every framework assumes departments to coordinate.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						The decisions you face are still management-caliber decisions. Pricing strategy, market positioning, feature prioritization, resource allocation—these require sophisticated thinking. And you're doing them all yourself, without the support structure that bigger companies have.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						The question isn't whether you need help—it's how to get that help without building the org you specifically avoided.
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
						Board of One gives you the management <em>capability</em> without the management <em>headcount</em>. When you need to think through a strategic decision, you get multi-perspective analysis from expert personas. When you need a framework, you get one tailored to your context.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Stay lean. Get the thinking. Skip the org chart.
					</p>
				</div>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3 flex items-center gap-2">
							<span class="text-brand-600">✓</span> What you get
						</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li>Strategic thinking on demand</li>
							<li>Multi-perspective analysis</li>
							<li>Decision frameworks tailored to your business</li>
							<li>Documented reasoning and recommendations</li>
							<li>24/7 availability, no scheduling</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3 flex items-center gap-2">
							<span class="text-error-500">✗</span> What you skip
						</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li>Six-figure salaries</li>
							<li>Management overhead</li>
							<li>Coordination costs</li>
							<li>Hiring and retention challenges</li>
							<li>The politics of bigger teams</li>
						</ul>
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
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Profitable businesses of any size that have chosen to optimize for margins over growth rate.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Situation</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Running a multi-person team (or solo) and want to keep it that way. Not avoiding growth—avoiding bloat.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Philosophy</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Believe smaller teams move faster. Want leverage without headcount. Value efficiency over empire-building.</p>
					</div>
				</div>
			</div>
		</section>

		<!-- The Lean Advantage -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					Why lean wins
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="space-y-4">
						<div class="flex gap-3">
							<div class="flex-shrink-0 w-6 h-6 rounded-full bg-success-100 dark:bg-success-900/30 flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-success-600 dark:text-success-400"><polyline points="20 6 9 17 4 12"/></svg>
							</div>
							<p class="text-neutral-700 dark:text-neutral-300">Higher revenue per employee</p>
						</div>
						<div class="flex gap-3">
							<div class="flex-shrink-0 w-6 h-6 rounded-full bg-success-100 dark:bg-success-900/30 flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-success-600 dark:text-success-400"><polyline points="20 6 9 17 4 12"/></svg>
							</div>
							<p class="text-neutral-700 dark:text-neutral-300">Faster decision-making</p>
						</div>
						<div class="flex gap-3">
							<div class="flex-shrink-0 w-6 h-6 rounded-full bg-success-100 dark:bg-success-900/30 flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-success-600 dark:text-success-400"><polyline points="20 6 9 17 4 12"/></svg>
							</div>
							<p class="text-neutral-700 dark:text-neutral-300">Less coordination overhead</p>
						</div>
					</div>
					<div class="space-y-4">
						<div class="flex gap-3">
							<div class="flex-shrink-0 w-6 h-6 rounded-full bg-success-100 dark:bg-success-900/30 flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-success-600 dark:text-success-400"><polyline points="20 6 9 17 4 12"/></svg>
							</div>
							<p class="text-neutral-700 dark:text-neutral-300">More flexibility to pivot</p>
						</div>
						<div class="flex gap-3">
							<div class="flex-shrink-0 w-6 h-6 rounded-full bg-success-100 dark:bg-success-900/30 flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-success-600 dark:text-success-400"><polyline points="20 6 9 17 4 12"/></svg>
							</div>
							<p class="text-neutral-700 dark:text-neutral-300">Better margins</p>
						</div>
						<div class="flex gap-3">
							<div class="flex-shrink-0 w-6 h-6 rounded-full bg-success-100 dark:bg-success-900/30 flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-success-600 dark:text-success-400"><polyline points="20 6 9 17 4 12"/></svg>
							</div>
							<p class="text-neutral-700 dark:text-neutral-300">Less politics and process</p>
						</div>
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
					<a href="/use-cases/delay-management-hires" class="block bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Delay Your Next Management Hire</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Get management thinking without the headcount</p>
					</a>
					<a href="/use-cases/advisor-alternative" class="block bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">On-Demand Expert Guidance</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Skip expensive advisors with sporadic availability</p>
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
