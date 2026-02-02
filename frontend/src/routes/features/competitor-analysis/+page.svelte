<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import {
		createFeaturePageSchema,
		createFeatureBreadcrumbSchema,
		createFeatureFAQSchema,
		serializeJsonLd,
		type FeaturePageConfig
	} from '$lib/utils/jsonld';

	const featureConfig: FeaturePageConfig = {
		slug: 'competitor-analysis',
		title: 'Competitor Analysis & Benchmarking',
		description: 'Understand what competitors are doing and how you compare. Track market movements, identify threats and opportunities, and benchmark your metrics.',
		category: 'Context Aggregation',
		datePublished: '2024-01-15',
		dateModified: '2024-12-01'
	};

	const faqs = [
		{
			question: 'How does Board of One gather competitor intelligence?',
			answer: 'Board of One analyzes publicly available information about your competitors: their websites, pricing pages, product features, content strategy, and market positioning. We also incorporate any information you provide from your own research—customer feedback about competitors, sales call notes, industry reports. The combination gives you a comprehensive picture without manual monitoring.'
		},
		{
			question: 'What information can I track about competitors?',
			answer: 'You can track competitor positioning and messaging, pricing and packaging structures, feature sets and product capabilities, content and SEO strategy, go-to-market approach, and significant changes over time. We focus on strategically relevant information—what helps you compete better, not just trivia about competitors.'
		},
		{
			question: 'How often is competitor data updated?',
			answer: 'We monitor for significant changes continuously and update competitor profiles when meaningful shifts occur—pricing changes, new feature launches, repositioning efforts. You don\'t need to remember to check; Board of One surfaces important changes when they happen and references current competitive information in your deliberations.'
		},
		{
			question: 'Can I add custom competitors to track?',
			answer: 'Yes. You define which competitors matter for your business. Add direct competitors, adjacent players, potential future threats—whoever you need to keep tabs on. You can also categorize competitors (direct, indirect, aspirational) and prioritize which ones you care most about.'
		},
		{
			question: 'How do benchmarks work?',
			answer: 'Benchmarks compare your metrics against relevant standards—industry averages, competitor estimates, or goals you set. When you upload data, Board of One contextualizes it: "Your CAC is 20% below the SaaS average" or "Your conversion rate lags Competitor X by about 15%." This context helps you understand whether your numbers are good, bad, or average.'
		},
		{
			question: 'How does this inform my strategic decisions?',
			answer: 'Competitive intelligence automatically enriches your deliberations. Discussing pricing? We reference competitor pricing strategies. Evaluating features to build? We show what competitors offer and where gaps exist. Planning positioning? We highlight differentiation opportunities. The intelligence isn\'t siloed—it flows into every relevant decision.'
		},
		{
			question: 'What if I have limited information about competitors?',
			answer: 'Start with what you know. Even basic information—their website, pricing page, key messaging—provides valuable context. Board of One can analyze publicly available information to fill gaps. Over time, as you learn more through sales calls, customer feedback, and market research, add that intelligence to build a richer picture.'
		},
		{
			question: 'How is this different from competitive intelligence tools?',
			answer: 'Most competitive intelligence tools give you data in a separate dashboard that you need to remember to check and manually connect to decisions. Board of One integrates competitive context directly into your decision-making process. When you deliberate on strategy, competitor intelligence is already there—not in a separate tab you forgot to open.'
		}
	];

	const breadcrumbSchema = createFeatureBreadcrumbSchema(featureConfig);
	const articleSchema = createFeaturePageSchema(featureConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>Competitor Analysis & Benchmarking - Board of One</title>
	<meta name="description" content="Never be blindsided by competitor moves. Track competitors, benchmark your metrics, and integrate competitive intelligence directly into your decision-making." />
	<link rel="canonical" href="https://boardof.one/features/competitor-analysis" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/features/competitor-analysis" />
	<meta property="og:title" content="Competitor Analysis & Benchmarking - Board of One" />
	<meta property="og:description" content="Never be blindsided by competitor moves. Competitive intelligence that flows into your decisions." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Competitor Analysis & Benchmarking - Board of One" />
	<meta name="twitter:description" content="Never be blindsided by competitor moves. Competitive intelligence that flows into your decisions." />
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
				<a href="/features" class="inline-flex items-center gap-2 text-brand-600 dark:text-brand-400 text-sm font-medium mb-6 hover:text-brand-700 dark:hover:text-brand-300">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
					All Features
				</a>
				<div class="flex items-center gap-3 mb-4">
					<div class="w-12 h-12 rounded-xl bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Context Aggregation</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Competitor Analysis & Benchmarking
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Never be blindsided by competitor moves. Understand what competitors are doing, how you compare, and where opportunities exist—without spending hours on manual research.
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The problem: competitors you're not watching
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						As a solopreneur, you can't afford to be blindsided by competitor moves. You don't have a strategy team monitoring the market. You don't have competitive intelligence analysts tracking pricing changes. But you still need to know when a competitor launches a new feature, undercuts your pricing, or pivots their positioning.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Manual monitoring is exhausting. Checking competitor websites, following their social media, reading industry news—it takes time you don't have. And even when you do the research, connecting that intelligence to your actual decisions is another step you often skip.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						The result? You make decisions in a competitive vacuum. You price without knowing what others charge. You build features without knowing what's table stakes vs. differentiation. You position without understanding how competitors are positioning.
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
						Board of One's competitor analysis helps you stay informed without spending hours on research. Track specific competitors, understand their positioning, and benchmark your metrics against industry standards—all integrated into your decision-making process.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						The key difference: competitive intelligence isn't isolated in a dashboard you forget to check. It's woven into every relevant decision. When you deliberate on pricing, competitor pricing is right there. When you evaluate features, you see what competitors offer. The intelligence flows to where you need it.
					</p>
				</div>
			</div>
		</section>

		<!-- What You Get -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					What you get
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Competitor profiles</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm mb-3">Track specific competitors and understand their positioning, pricing, features, and go-to-market strategy.</p>
						<ul class="space-y-1 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Positioning and messaging analysis</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Feature comparison matrices</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Pricing and packaging intelligence</li>
						</ul>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Market movement tracking</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm mb-3">Stay informed about changes in your competitive landscape without constant manual research.</p>
						<ul class="space-y-1 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>New competitor detection</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Feature and pricing changes</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Repositioning alerts</li>
						</ul>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Threat & opportunity identification</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm mb-3">Understand where you're vulnerable and where you have advantages.</p>
						<ul class="space-y-1 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Competitive threat assessment</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Market gap identification</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Differentiation opportunities</li>
						</ul>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Metric benchmarking</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm mb-3">Compare your performance against industry standards and peer companies.</p>
						<ul class="space-y-1 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Industry benchmarks by metric</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Peer company comparisons</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Performance gap analysis</li>
						</ul>
					</div>
				</div>
			</div>
		</section>

		<!-- How It's Used -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					How competitive intelligence informs decisions
				</h2>
				<div class="space-y-6">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Pricing decisions</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">"Should I raise my prices?" becomes an informed discussion when you know what competitors charge, how your features compare, what the market will bear, and where you can justify premium pricing.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Feature prioritization</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">"What should I build next?" gets clearer when you understand what competitors offer, what's table stakes vs. differentiation, and where feature gaps create opportunities.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Positioning refinement</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">"How should I position my product?" requires understanding how competitors position themselves, where messaging overlaps, and where there's room for clear differentiation.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Market entry</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">"Should I enter this new segment?" benefits from knowing who already serves it, how entrenched they are, and whether your differentiation translates to that market.</p>
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

		<!-- Part of the System -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4 text-center">
					Part of a cohesive system
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-8 max-w-2xl mx-auto text-center">
					Competitor intelligence doesn't live in isolation. It's connected to your entire decision-making system.
				</p>
				<div class="grid md:grid-cols-3 gap-6 mb-8">
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Context-Filtered</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Competitive analysis is filtered through your <a href="/features/tailored-to-you" class="text-brand-600 dark:text-brand-400 underline">business context</a>—focusing on what matters for your positioning.</p>
					</div>
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Enriches Data</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Benchmarks add context to your <a href="/features/data-analysis" class="text-brand-600 dark:text-brand-400 underline">data analysis</a>—"Is this metric good or bad?"</p>
					</div>
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Informs Decisions</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Competitive intelligence flows into <a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">deliberations</a> automatically.</p>
					</div>
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
