<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import {
		createComparePageSchema,
		createCompareBreadcrumbSchema,
		createFeatureFAQSchema,
		serializeJsonLd,
		type ComparePageConfig
	} from '$lib/utils/jsonld';

	const pageConfig: ComparePageConfig = {
		slug: 'board-of-one-vs-consultants',
		title: 'Board of One vs Management Consultants',
		description: 'Compare Board of One to hiring management consultants like McKinsey, BCG, or boutique firms. Understand cost, speed, and quality trade-offs.',
		datePublished: '2025-01-15',
		dateModified: '2025-01-20'
	};

	const faqs = [
		{
			question: 'Can AI really replace McKinsey?',
			answer: 'Not for everything. Top consultants bring deep industry expertise, research capabilities, political capital (their brand carries weight), and hands-on implementation support. What Board of One replaces is the strategic thinking and framework development—the stuff you\'re paying £1,000+/day for someone to do. For most founder decisions, that\'s what you actually need.'
		},
		{
			question: 'What about the research consultants do?',
			answer: 'Consultants excel at deep market research, customer interviews, and competitive intelligence gathering. Board of One doesn\'t replace primary research. What it replaces is the analysis and recommendation layer—taking what you know and turning it into frameworks and decisions. If you need 50 customer interviews, hire a consultant. If you need to decide what to do with the insights you already have, that\'s Board of One.'
		},
		{
			question: 'My investors want to see a McKinsey deck',
			answer: 'That\'s a credibility play, not a quality play. If your investors specifically want the McKinsey brand on a deck, that\'s a different value proposition than getting good strategic advice. Be honest about what you\'re buying—if it\'s credibility, pay for it. If it\'s thinking, you might not need to.'
		},
		{
			question: 'What kinds of projects make sense for consultants vs. Board of One?',
			answer: 'Consultants: Due diligence for major acquisitions, market entry studies requiring primary research, organizational restructuring with political sensitivity, anything requiring their brand credibility. Board of One: Day-to-day strategic decisions, pricing and positioning, feature prioritization, operational improvements, anything you need to decide quickly and repeatedly.'
		},
		{
			question: 'How does the output quality compare?',
			answer: 'For strategic frameworks and decision support, Board of One\'s output is comparable to good consultant work—sometimes better because it\'s faster and more iterative. For deep research and politically sensitive recommendations, consultants have advantages. For speed and cost, Board of One wins decisively. The question is what you actually need.'
		},
		{
			question: 'What about boutique consultants who are cheaper?',
			answer: 'Boutique consultants (£500-1,000/day) are more accessible, but the economics are still challenging for most founders. A week of boutique consulting costs £2,500-5,000. That\'s months of Board of One access. And you still have scheduling constraints, context rebuilding, and project minimums to contend with.'
		}
	];

	const breadcrumbSchema = createCompareBreadcrumbSchema(pageConfig);
	const articleSchema = createComparePageSchema(pageConfig);
	const faqSchema = createFeatureFAQSchema(faqs);

	const comparisonData = [
		{ aspect: 'Cost', consultants: '£1,000-5,000/day', boardOfOne: 'Fixed monthly subscription' },
		{ aspect: 'Minimum engagement', consultants: '2-4 weeks typical', boardOfOne: 'No minimum' },
		{ aspect: 'Availability', consultants: 'Project-based, scheduled', boardOfOne: '24/7, instant' },
		{ aspect: 'Context ramp-up', consultants: '1-2 weeks to understand you', boardOfOne: 'Instant (always loaded)' },
		{ aspect: 'Output format', consultants: 'Polished decks after weeks', boardOfOne: 'Immediate, iterative' },
		{ aspect: 'Research depth', consultants: 'Deep primary research', boardOfOne: 'Works with your data' },
		{ aspect: 'Brand credibility', consultants: 'High (McKinsey/BCG name)', boardOfOne: 'None' }
	];
</script>

<svelte:head>
	<title>Board of One vs Consultants - Affordable Strategic Guidance for Founders</title>
	<meta name="description" content="Management consultants cost £1,000-5,000/day. Board of One provides strategic frameworks and decision support at a fraction of the cost. See the trade-offs." />
	<link rel="canonical" href="https://boardof.one/compare/board-of-one-vs-consultants" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/compare/board-of-one-vs-consultants" />
	<meta property="og:title" content="Board of One vs Consultants - Affordable Strategic Guidance for Founders" />
	<meta property="og:description" content="Consultants cost £1,000-5,000/day. Get strategic frameworks at a fraction of the cost." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Board of One vs Consultants - Affordable Strategic Guidance for Founders" />
	<meta name="twitter:description" content="Consultants cost £1,000-5,000/day. Get strategic frameworks at a fraction of the cost." />
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
				<a href="/compare" class="inline-flex items-center gap-2 text-brand-600 dark:text-brand-400 text-sm font-medium mb-6 hover:text-brand-700 dark:hover:text-brand-300">
					<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
					All Comparisons
				</a>
				<div class="flex items-center gap-3 mb-4">
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Comparison</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Board of One vs Consultants
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					McKinsey charges £5,000+/day. Boutique firms charge £1,000+. What if you could get strategic frameworks without the consulting invoice?
				</p>
			</div>
		</section>

		<!-- The Reality Check -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The reality of consulting costs
				</h2>
				<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-8 border border-neutral-200 dark:border-neutral-700">
					<div class="grid md:grid-cols-3 gap-6 text-center">
						<div>
							<div class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">£5,000+</div>
							<div class="text-sm text-neutral-600 dark:text-neutral-400">Big 3 (McKinsey, BCG, Bain) per day</div>
						</div>
						<div>
							<div class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">£1-2k</div>
							<div class="text-sm text-neutral-600 dark:text-neutral-400">Boutique consultants per day</div>
						</div>
						<div>
							<div class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">£50k+</div>
							<div class="text-sm text-neutral-600 dark:text-neutral-400">Typical minimum engagement</div>
						</div>
					</div>
				</div>
				<p class="text-neutral-600 dark:text-neutral-400 mt-6">
					For most founders, consulting is simply out of reach—or requires betting a significant portion of runway on a single project.
				</p>
			</div>
		</section>

		<!-- Quick Comparison Table -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					Quick comparison
				</h2>
				<div class="overflow-x-auto">
					<table class="w-full">
						<thead>
							<tr class="border-b border-neutral-200 dark:border-neutral-700">
								<th class="text-left py-4 pr-4 font-medium text-neutral-500 dark:text-neutral-400"></th>
								<th class="text-left py-4 px-4 font-medium text-neutral-900 dark:text-neutral-100">Consultants</th>
								<th class="text-left py-4 pl-4 font-medium text-brand-600 dark:text-brand-400">Board of One</th>
							</tr>
						</thead>
						<tbody>
							{#each comparisonData as row}
								<tr class="border-b border-neutral-200 dark:border-neutral-700">
									<td class="py-4 pr-4 font-medium text-neutral-700 dark:text-neutral-300">{row.aspect}</td>
									<td class="py-4 px-4 text-neutral-600 dark:text-neutral-400">{row.consultants}</td>
									<td class="py-4 pl-4 text-neutral-600 dark:text-neutral-400">{row.boardOfOne}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		</section>

		<!-- When to Choose Board of One -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					When to choose Board of One
				</h2>
				<div class="space-y-4">
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You need strategic frameworks, not primary research</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">Speed matters—you can't wait weeks for a deck</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You have frequent decisions, not one big project</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">Budget matters—£50k+ minimum is out of reach</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You want to iterate quickly, not wait for polished deliverables</p>
					</div>
				</div>
			</div>
		</section>

		<!-- When to Choose Consultants -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					When to choose consultants
				</h2>
				<div class="space-y-4">
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You need deep primary research (50+ customer interviews)</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">Their brand name matters (investor credibility, board politics)</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">It's a bet-the-company decision (major acquisition, market entry)</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You need implementation support, not just strategy</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">Budget isn't a constraint and timeline isn't urgent</p>
					</div>
				</div>
			</div>
		</section>

		<!-- The 80/20 -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The 80/20 reality
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Most of what founders need from consultants is strategic thinking—frameworks, analysis, recommendations. That's the 80% that Board of One handles.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						The other 20%—deep research, brand credibility, implementation support—is where consultants still have an edge. But you're paying for the full 100% even when you only need 20%.
					</p>
					<p class="text-lg text-neutral-700 dark:text-neutral-300 leading-relaxed mt-4 font-medium">
						Use Board of One for the 80%. Save consultants for the rare occasions you truly need them.
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

		<!-- CTA -->
		<section class="py-16 md:py-24 bg-gradient-to-r from-brand-600 to-brand-700 dark:from-brand-700 dark:to-brand-800">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-3xl md:text-4xl font-bold text-white mb-4">
					Strategic guidance without the invoice
				</h2>
				<p class="text-lg text-brand-100 mb-8">
					Get consulting-quality frameworks at a fraction of the cost.
				</p>
				<Button
					variant="secondary"
					size="lg"
					onclick={() => window.location.href = '/'}
				>
					Request Early Access
				</Button>
			</div>
		</section>
	</main>

	<Footer />
</div>
