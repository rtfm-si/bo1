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
		slug: 'seo-generation',
		title: 'SEO Generation',
		description: 'Understand your search visibility and generate content that attracts the right customers—without hiring an SEO specialist.',
		category: 'Growth',
		datePublished: '2024-01-15',
		dateModified: '2024-12-01'
	};

	const faqs = [
		{
			question: 'How does Board of One identify keyword opportunities?',
			answer: 'Board of One analyzes your business positioning, target market, and competitive landscape to identify keywords that align with what your ideal customers are searching for. We look at search volume, competition difficulty, and relevance to your offerings—then prioritize opportunities where you can realistically rank and where the traffic would actually convert.'
		},
		{
			question: 'What\'s included in a content brief?',
			answer: 'Each content brief includes a target keyword, search intent analysis, recommended title and meta description, heading structure (H2s and H3s), key points to cover, questions to answer, internal linking suggestions, and word count recommendations. Essentially, everything you need to write a comprehensive, SEO-optimized piece—or hand off to a writer.'
		},
		{
			question: 'How is this different from other SEO tools?',
			answer: 'Most SEO tools give you raw data: keyword volumes, difficulty scores, backlink counts. Board of One gives you strategy. We know your business model, your positioning, your competitors—so we can recommend keywords that make sense for your specific situation. Not just "this keyword has volume" but "this keyword aligns with your positioning against competitors X and Y."'
		},
		{
			question: 'Do I need SEO knowledge to use this?',
			answer: 'No. Board of One translates SEO complexity into actionable recommendations. You don\'t need to understand domain authority, search intent categories, or technical SEO. We tell you what to write, why it matters, and how to structure it. If you want to learn, we explain the reasoning—but it\'s not required to get results.'
		},
		{
			question: 'How does competitor analysis inform SEO recommendations?',
			answer: 'We analyze what keywords your competitors rank for, identify gaps where they\'re weak, and find opportunities where you can differentiate. If a competitor dominates generic terms but ignores long-tail queries, we\'ll prioritize those. If they\'ve missed a content angle your expertise supports, we\'ll flag it. Competitive intelligence makes your SEO strategy smarter.'
		},
		{
			question: 'Can I track my search rankings over time?',
			answer: 'Yes. Board of One tracks your ranking positions for target keywords and shows movement over time. You can see which content is gaining traction, which keywords are improving, and where you need to invest more. This feedback loop helps you refine your strategy based on what\'s actually working.'
		},
		{
			question: 'What types of content does Board of One help create?',
			answer: 'We generate briefs for blog posts, landing pages, product pages, comparison pages, FAQ content, and pillar content. The format depends on the keyword intent—informational queries get educational content, transactional queries get conversion-focused pages. We match the content type to what searchers actually want.'
		},
		{
			question: 'How often should I publish new content?',
			answer: 'Quality matters more than quantity. For most solopreneurs, 2-4 well-researched, comprehensive pieces per month outperform daily thin content. Board of One helps you prioritize high-impact topics so you get maximum results from each piece. Consistency matters, but sustainable consistency—not burnout.'
		}
	];

	const breadcrumbSchema = createFeatureBreadcrumbSchema(featureConfig);
	const articleSchema = createFeaturePageSchema(featureConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>SEO Content Generation for Solopreneurs - Board of One</title>
	<meta name="description" content="SEO expertise without the SEO expert price tag. Generate keyword strategies and content briefs informed by your positioning and competitors." />
	<link rel="canonical" href="https://boardof.one/features/seo-generation" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/features/seo-generation" />
	<meta property="og:title" content="SEO Content Generation for Solopreneurs - Board of One" />
	<meta property="og:description" content="SEO expertise without the SEO expert price tag." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="SEO Content Generation for Solopreneurs - Board of One" />
	<meta name="twitter:description" content="SEO expertise without the SEO expert price tag." />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Growth</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					SEO Generation
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					SEO expertise without the SEO expert price tag. Generate keyword strategies and content briefs informed by your positioning and competitors—not generic best practices.
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The problem: SEO is complex and expensive
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						For solopreneurs, organic search is often the most cost-effective customer acquisition channel. You don't need to pay for every click. Content compounds over time. And it attracts people actively searching for solutions you provide.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						But SEO is complex. Keyword research, competitive analysis, content optimization, technical audits, link building—it's a full-time job. You can hire an agency for $3-10k/month, or spend hours learning it yourself. Neither option works well when you're running everything alone.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						What you need is the strategic insight of an SEO expert without the overhead—someone who understands your business, your positioning, and your competitive landscape.
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
						Board of One's SEO generation capability analyzes your business positioning and helps you create content that ranks. We identify keyword opportunities, generate optimized content briefs, and help you understand where you stand in search results—all informed by your specific business context.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						This isn't generic keyword data. We know your target market, your competitors, your unique value proposition. So we can recommend keywords that align with your positioning and content that reinforces your differentiation.
					</p>
				</div>
				<div class="space-y-8">
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">1</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Analyze your positioning</h3>
							<p class="text-neutral-600 dark:text-neutral-400">We understand your business, target market, and competitors to identify relevant keyword opportunities. Not just high-volume terms, but terms that match your expertise and attract your ideal customers.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">2</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Generate content briefs</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Get detailed outlines for blog posts, landing pages, and other content—optimized for the keywords that matter to your business. Complete with structure, talking points, and SEO best practices.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">3</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Track and improve</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Monitor your search visibility over time and get recommendations for improving underperforming content. See what's working and double down on it.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Why Different -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Why this is different
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Most SEO tools give you data: keyword volumes, difficulty scores, SERP features. Useful, but you still need to interpret it and develop strategy. That interpretation requires understanding your business—something generic tools can't do.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One gives you strategy. We know your positioning, your competitors, your target customer. So instead of "this keyword has 5,000 monthly searches," we tell you "this keyword aligns with your differentiation against Competitor X, has achievable difficulty for your domain authority, and matches the intent of customers who convert well for you."
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						That's the difference between a tool and an advisor. We're not just giving you raw materials—we're giving you a plan.
					</p>
				</div>
			</div>
		</section>

		<!-- What You Get -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					What you get
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Keyword opportunities</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Discover keywords your ideal customers are searching for—matched to your business positioning and competitive landscape. Prioritized by impact, not just volume.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Content briefs</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Detailed outlines for articles and pages, including headings, talking points, questions to answer, and SEO best practices. Ready for you to write or hand off.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Meta content</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Title tags, meta descriptions, and social previews optimized for click-through rates. The small details that make a big difference in search visibility.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Content calendar</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">A pipeline of content ideas that align with your expertise and what your audience is searching for. Sustainable publishing without constant ideation.</p>
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
					SEO generation isn't standalone. It's informed by and connected to your entire Board of One system.
				</p>
				<div class="grid md:grid-cols-3 gap-6 mb-8">
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Context-Informed</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">SEO recommendations are based on your <a href="/features/tailored-to-you" class="text-brand-600 dark:text-brand-400 underline">business context</a>—your positioning, market, and goals.</p>
					</div>
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Competitive Edge</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm"><a href="/features/competitor-analysis" class="text-brand-600 dark:text-brand-400 underline">Competitor intelligence</a> reveals keyword gaps and content opportunities they've missed.</p>
					</div>
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Strategic Decisions</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Use <a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">deliberation sessions</a> to decide on content strategy priorities and resource allocation.</p>
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
