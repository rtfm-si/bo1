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
		slug: 'strategic-decisions',
		title: 'Making Strategic Decisions Solo',
		description: 'Big decisions without a board. Board of One provides multi-perspective deliberation for the calls that shape your company.',
		datePublished: '2025-01-15',
		dateModified: '2025-01-20'
	};

	const faqs = [
		{
			question: 'What qualifies as a "strategic decision"?',
			answer: 'Decisions that are hard to reverse, have long-term implications, or significantly affect your company\'s trajectory. Pricing model changes, market expansion, major pivots, fundraising vs. bootstrapping, partnership deals, key hires. The decisions where you wish you had a board to consult—but don\'t.'
		},
		{
			question: 'How is this different from just thinking it through myself?',
			answer: 'You can\'t argue with yourself effectively. You\'ll confirm your own biases, overlook perspectives you\'re not trained in, and miss considerations you don\'t know exist. Board of One brings multiple expert viewpoints—finance, operations, marketing, product—each with different biases and concerns. It\'s structured disagreement, not an echo chamber.'
		},
		{
			question: 'Can AI really help with decisions this important?',
			answer: 'The AI isn\'t deciding for you—it\'s helping you think through the decision systematically. It surfaces considerations, challenges assumptions, and documents trade-offs. The decision remains yours. What changes is the quality of thinking that goes into it. Many founders report catching blind spots they would have missed entirely.'
		},
		{
			question: 'What if the recommendation is wrong?',
			answer: 'Every recommendation comes with documented reasoning and explicit trade-offs. You can see why it was suggested and what assumptions it\'s based on. If those assumptions don\'t match your reality, you can override with confidence. The goal isn\'t to be right—it\'s to help you make a more informed decision.'
		},
		{
			question: 'How do I know when to use Board of One vs. just deciding?',
			answer: 'Use it for decisions where the cost of being wrong is high or the decision is hard to reverse. A weekly marketing budget tweak? Just decide. A fundamental pricing model change? That\'s worth deliberating. If you find yourself wishing you had someone to talk through it with—that\'s the signal.'
		},
		{
			question: 'Do I need to prepare anything before a strategic deliberation?',
			answer: 'Having your business context already set up helps a lot—your metrics, positioning, constraints. Beyond that, clarity on the decision you\'re facing and any constraints you know about. The deliberation process will surface additional considerations you might not have thought to include.'
		}
	];

	const breadcrumbSchema = createUseCaseBreadcrumbSchema(pageConfig);
	const articleSchema = createUseCasePageSchema(pageConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>Strategic Decisions Without a Board - Multi-Perspective Analysis | Board of One</title>
	<meta name="description" content="Making board-level decisions without a board? Board of One provides multi-perspective deliberation for solo founders facing strategic choices." />
	<link rel="canonical" href="https://boardof.one/use-cases/strategic-decisions" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/use-cases/strategic-decisions" />
	<meta property="og:title" content="Strategic Decisions Without a Board - Multi-Perspective Analysis" />
	<meta property="og:description" content="Making board-level decisions without a board? Get multi-perspective deliberation." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Strategic Decisions Without a Board - Multi-Perspective Analysis" />
	<meta name="twitter:description" content="Making board-level decisions without a board? Get multi-perspective deliberation." />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Use Case</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Making Strategic Decisions Solo
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					No board, no co-founder, no executive team—but you're still facing decisions that will shape your company's future. You need structured thinking, not just intuition.
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The problem: big decisions, no sounding board
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Should you raise prices or go for volume? Bootstrap or take funding? Expand to a new market or double down? Partner with a competitor or compete head-on? These decisions shape your company—and you're making them alone.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Most strategic frameworks assume you have a leadership team to debate with, a board to challenge your thinking, or at least a co-founder to argue with. When you're solo, you're debating yourself—which is just confirming your own biases with extra steps.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						The stakes are too high for gut decisions. But you don't have the support structure that companies use to make these calls well.
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
						Board of One provides structured, multi-perspective deliberation for strategic decisions. Instead of debating yourself, you get 3-5 expert personas—each with different expertise, biases, and concerns—analyzing your decision systematically.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Finance challenges the optimistic projections. Operations asks about execution risk. Marketing considers positioning implications. Product thinks about customer impact. They debate each other, not just validate your thinking.
					</p>
				</div>
				<div class="space-y-6">
					<div class="flex gap-4">
						<div class="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-bold">1</div>
						<div>
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-1">Frame the decision</h3>
							<p class="text-neutral-600 dark:text-neutral-400">"Should we raise our prices by 30% and risk losing price-sensitive customers, or keep prices low and compete on volume?"</p>
						</div>
					</div>
					<div class="flex gap-4">
						<div class="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-bold">2</div>
						<div>
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-1">Get multi-perspective analysis</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Expert personas analyze the decision from their unique angles—finance, marketing, operations, product. Each surfaces different considerations and risks.</p>
						</div>
					</div>
					<div class="flex gap-4">
						<div class="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-bold">3</div>
						<div>
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-1">Watch them challenge each other</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Perspectives debate, challenge assumptions, and pressure-test recommendations. Finance might push back on Marketing's optimistic projections. Operations might flag execution risks.</p>
						</div>
					</div>
					<div class="flex gap-4">
						<div class="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-bold">4</div>
						<div>
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-1">Receive a synthesized recommendation</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Clear recommendation with documented reasoning, explicit trade-offs, and actionable next steps. You decide—but with better information.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Examples -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					Strategic decisions Board of One helps with
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Pricing & Packaging</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Raise prices or hold the line</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Free tier vs. paid only</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Annual vs. monthly pricing</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Tier structure and feature allocation</li>
						</ul>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Market & Positioning</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Expand to new market or deepen current</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Go upmarket or down</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Geographic expansion</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Vertical specialization vs. horizontal</li>
						</ul>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Funding & Growth</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Bootstrap vs. raise</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Growth rate vs. profitability</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Revenue-based financing</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Exit timing and strategy</li>
						</ul>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Partnerships & Competition</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Partner or compete</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Channel strategy</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Integration priorities</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Acquisition opportunities</li>
						</ul>
					</div>
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
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Any. Strategic decisions don't wait for Series A. If you're facing choices that will shape your company, you're the right stage.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Situation</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Solo founder, or leading without a co-founder/board/executive team. Making big decisions without a structured sounding board.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Mindset</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">You value structured thinking over gut feel. You want your decisions to be defensible, not just intuitive.</p>
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
