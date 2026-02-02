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
		slug: 'decisions-replanning',
		title: 'Decisions & Replanning',
		description: 'Structured deliberations with multiple expert perspectives. Get comprehensive analysis of your options, clear recommendations, and the ability to revisit decisions when circumstances change.',
		category: 'Core Decision Engine',
		datePublished: '2024-01-15',
		dateModified: '2024-12-01'
	};

	const faqs = [
		{
			question: 'How many expert perspectives are in each deliberation?',
			answer: 'Typically 3-5 expert personas participate in each deliberation, selected based on the type of decision you\'re making. A pricing decision might involve a Financial Analyst, Growth Marketer, and Strategic Advisor. A product decision might include a Product Thinker, Operations Expert, and Customer Advocate. Each brings a distinct lens to the analysis.'
		},
		{
			question: 'What types of decisions is this best for?',
			answer: 'Board of One deliberations work best for strategic decisions with trade-offs: pricing changes, market entry, hiring vs. outsourcing, feature prioritization, positioning pivots, channel strategy. Not for trivial choices or pure execution tasks. If you find yourself thinking "I wish I could get a few smart perspectives on this," it\'s probably right for a deliberation.'
		},
		{
			question: 'How long does a deliberation session take?',
			answer: 'A full deliberation typically processes in 2-3 minutes—fast enough to run during a working session. The output includes expert positions, debate across multiple rounds, points of agreement and disagreement, a synthesized recommendation, and concrete next actions. You can review at your own pace.'
		},
		{
			question: 'Can I pause and resume a deliberation?',
			answer: 'Yes. You can save a deliberation at any point and return later. All context is preserved. This is useful if you want to review the expert positions before seeing the synthesis, or if you need to gather more information mid-deliberation. Your session state is always available.'
		},
		{
			question: 'What happens if experts disagree?',
			answer: 'Disagreement is valuable. The synthesis highlights where experts align (high confidence) and where they diverge (areas of uncertainty). Dissenting views are preserved in the output—if the Financial Analyst recommends against something the Strategic Advisor supports, you see both positions and the reasoning. This lets you make an informed choice about whose perspective to weight more heavily.'
		},
		{
			question: 'When should I trigger a replanning session?',
			answer: 'Trigger replanning when circumstances change meaningfully: new data contradicts original assumptions, a key constraint has changed (runway extended, competitor moved), an action has been stuck too long, or outcomes aren\'t matching expectations. Replanning revisits your original decision with new context rather than starting from scratch.'
		},
		{
			question: 'How is this different from asking ChatGPT?',
			answer: 'Three key differences: (1) Context—ChatGPT doesn\'t know your business, metrics, or constraints. Board of One does. (2) Structure—ChatGPT gives you a single response. Board of One gives you multiple expert perspectives debating in rounds. (3) Action—ChatGPT stops at advice. Board of One generates specific actions that flow into project management.'
		},
		{
			question: 'Can I influence which experts participate?',
			answer: 'Yes. Board of One automatically selects relevant experts based on your decision type, but you can adjust the panel. Add a legal perspective for compliance decisions. Remove the growth marketer for internal operations questions. The system learns your preferences over time.'
		}
	];

	const breadcrumbSchema = createFeatureBreadcrumbSchema(featureConfig);
	const articleSchema = createFeaturePageSchema(featureConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>AI Boardroom Decisions for Solopreneurs - Board of One</title>
	<meta name="description" content="Every CEO has a boardroom. Now you do too. Multi-expert deliberations with structured debate, clear recommendations, and the ability to revisit when reality changes." />
	<link rel="canonical" href="https://boardof.one/features/decisions-replanning" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/features/decisions-replanning" />
	<meta property="og:title" content="AI Boardroom Decisions for Solopreneurs - Board of One" />
	<meta property="og:description" content="Every CEO has a boardroom. Now you do too." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="AI Boardroom Decisions for Solopreneurs - Board of One" />
	<meta name="twitter:description" content="Every CEO has a boardroom. Now you do too." />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Core Decision Engine</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Decisions & Replanning
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Every CEO has a boardroom. Now you do too. Multi-expert deliberations with structured debate, clear recommendations, and the ability to revisit decisions when circumstances change.
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The problem: making hard calls alone
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						The hardest part of running a business alone isn't doing the work—it's making decisions without a team to pressure-test your thinking. You can't hire a CFO, CMO, and COO to weigh in on every strategic question. Yet these decisions shape everything that follows.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Should you raise prices? Enter a new market? Build this feature or that one? Hire now or wait? Each choice has trade-offs. Each could go either way. And you're making these calls alone, without the debate and challenge that leads to better decisions.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Worse, once you commit, circumstances change. New information emerges. The market shifts. But revisiting decisions feels expensive, so you often continue on an outdated path longer than you should.
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
						Board of One's deliberation sessions give you what every CEO has: a room full of experts debating your options. Multiple AI personas with different expertise areas analyze your decision, debate the trade-offs across multiple rounds, and synthesize their perspectives into a clear recommendation—one you can understand, challenge, and act on.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						And when circumstances change—which they always do—replanning lets you revisit any decision with new context. Not starting from scratch, but building on the original analysis. The system remembers what you considered, what you decided, and why.
					</p>
				</div>
				<div class="space-y-8">
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">1</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Frame your decision</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Describe the decision you're facing. "Should I raise my prices?" "Which market should I enter first?" "Should I hire a contractor or build it myself?" The clearer the question, the more focused the analysis.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">2</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Experts deliberate</h3>
							<p class="text-neutral-600 dark:text-neutral-400">3-5 expert personas—selected based on your decision type—analyze the problem. They debate options across multiple rounds, challenge each other's assumptions, and surface trade-offs you might not have considered.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">3</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Get a synthesized recommendation</h3>
							<p class="text-neutral-600 dark:text-neutral-400">The system synthesizes all perspectives into a clear recommendation with supporting reasoning, dissenting views, confidence levels, and concrete next actions. You understand not just what to do, but why.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">4</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Act and revisit</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Execute your decision with clear actions that flow into project management. When circumstances change, reopen the deliberation to reassess with new information. Replanning is expected, not failure.</p>
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
						Generic AI gives you a single perspective—whatever the model thinks is the "best" answer. That's not how good decisions get made. Good decisions emerge from debate, challenge, and the collision of different viewpoints.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One deliberations surface tension. The Financial Analyst worries about cash flow while the Growth Marketer pushes for investment. The Operations Expert flags execution risks while the Strategic Advisor advocates for ambition. These tensions aren't noise—they're signal. They're the trade-offs you need to navigate.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						And unlike a one-shot AI response, Board of One remembers. Your decision history is preserved. When you need to revisit a choice, all the context is there. This isn't ephemeral chat—it's a persistent record of your strategic thinking.
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
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Multi-perspective analysis</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Expert personas from finance, strategy, operations, and marketing examine your decision from all angles. Different biases surface different considerations.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Structured debate</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Watch experts challenge each other's assumptions and reasoning across multiple rounds. See where they agree and where they diverge.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Clear recommendations</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Get a synthesized recommendation with confidence levels, supporting evidence, and dissenting perspectives preserved for your consideration.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Concrete actions</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Every decision generates specific next steps that flow directly into your project management system. Thinking connects to doing.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Decision history</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Every deliberation is recorded. Look back at why you made a decision, what you considered, and what you knew at the time.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Replanning capability</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Circumstances changed? Reopen any past decision, add new context, and get updated recommendations. Replanning is a feature, not a failure.</p>
					</div>
				</div>
			</div>
		</section>

		<!-- Expert Personas -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Expert personas for every decision type
				</h2>
				<div class="grid md:grid-cols-3 gap-4">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Strategic Advisor</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Long-term positioning, market strategy, competitive dynamics, defensibility</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Financial Analyst</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">ROI analysis, cash flow, unit economics, financial risk assessment</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Operations Expert</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Implementation feasibility, resource constraints, execution risk</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Growth Marketer</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Customer acquisition, positioning, messaging, market timing</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Product Thinker</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">User needs, feature prioritization, product-market fit</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Devil's Advocate</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Challenges assumptions, surfaces blind spots, stress-tests reasoning</p>
					</div>
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

		<!-- Part of the System -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4 text-center">
					The heart of Board of One
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-8 max-w-2xl mx-auto text-center">
					Everything flows through decisions. Every other capability exists to make your deliberations better.
				</p>
				<div class="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
					<a href="/features/tailored-to-you" class="block bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Business Context</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Powers every deliberation with your reality</p>
					</a>
					<a href="/features/data-analysis" class="block bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Data Analysis</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Grounds decisions in your actual metrics</p>
					</a>
					<a href="/features/competitor-analysis" class="block bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Competitor Intel</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Informs competitive considerations</p>
					</a>
					<a href="/features/project-management" class="block bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Project Management</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Receives actions for follow-through</p>
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
