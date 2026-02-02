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
		slug: 'board-of-one-vs-advisory-board',
		title: 'Board of One vs Advisory Board',
		description: 'Compare Board of One to a traditional advisory board. Understand the trade-offs between equity, access, and quality of guidance.',
		datePublished: '2025-01-15',
		dateModified: '2025-01-20'
	};

	const faqs = [
		{
			question: 'Do I really need advisors if I have Board of One?',
			answer: 'Depends on what you need from advisors. If it\'s strategic thinking and analysis—Board of One handles that. If it\'s introductions to investors, industry credibility, or specific pattern-matching from lived experience—that\'s where human advisors still excel. Many founders find they need fewer advisors, not zero advisors.'
		},
		{
			question: 'How much equity do advisors typically get?',
			answer: 'Typically 0.25-1% for a formal advisor, vesting over 2 years with monthly or quarterly meetings. At a £10M exit, that 0.5% is £50,000. At £100M, it\'s £500,000. Plus many advisors also expect cash retainers of £500-2,000/month. The equity cost alone often exceeds what you\'d spend on Board of One for years.'
		},
		{
			question: 'But my advisor has industry connections I need',
			answer: 'That\'s a valid reason to have an advisor. Board of One doesn\'t replace relationship value—introductions, references, and network access. What it replaces is the strategic thinking component. If your advisor\'s primary value is their network, keep them. If it\'s their strategic input, evaluate whether you\'re getting good value.'
		},
		{
			question: 'What about the credibility advisors provide?',
			answer: 'Having notable names on your advisory board can signal quality to investors and customers. This is real value that Board of One can\'t provide. But be honest: is that credibility worth the equity? And are the advisors actually providing strategic value, or just their name? Often one or two high-profile advisors for credibility + Board of One for actual guidance is the optimal mix.'
		},
		{
			question: 'How do I get multiple perspectives without multiple advisors?',
			answer: 'Board of One provides multi-perspective analysis by design—finance, marketing, operations, product viewpoints all weighing in on decisions. Getting that breadth from human advisors would require 4-5 people, each taking equity. Board of One gives you the equivalent of a full advisory board at a fraction of the cost.'
		},
		{
			question: 'Can advisors and Board of One work together?',
			answer: 'Absolutely. Use Board of One for frequent decisions and day-to-day strategic thinking. Reserve advisor meetings for high-stakes decisions where their specific experience matters, or for leveraging their network. This makes your limited advisor time more impactful—you\'re not spending it on routine decisions.'
		}
	];

	const breadcrumbSchema = createCompareBreadcrumbSchema(pageConfig);
	const articleSchema = createComparePageSchema(pageConfig);
	const faqSchema = createFeatureFAQSchema(faqs);

	const comparisonData = [
		{ aspect: 'Cost', advisory: '0.25-1% equity + cash retainer', boardOfOne: 'Fixed monthly subscription' },
		{ aspect: 'Availability', advisory: 'Monthly/quarterly meetings', boardOfOne: '24/7, instant access' },
		{ aspect: 'Perspectives', advisory: '1 per advisor (need multiple)', boardOfOne: 'Multiple built-in' },
		{ aspect: 'Context retention', advisory: 'Needs re-sync each meeting', boardOfOne: 'Always loaded' },
		{ aspect: 'Network value', advisory: 'Introductions & credibility', boardOfOne: 'None' },
		{ aspect: 'Documentation', advisory: 'Rarely documented', boardOfOne: 'Full decision logs' },
		{ aspect: 'Commitment', advisory: 'Equity vests over 2 years', boardOfOne: 'Cancel anytime' }
	];
</script>

<svelte:head>
	<title>Board of One vs Advisory Board - Equity-Free Alternative for Founders</title>
	<meta name="description" content="Compare Board of One to advisory boards. Get strategic guidance without giving up equity or scheduling monthly meetings. See the real trade-offs." />
	<link rel="canonical" href="https://boardof.one/compare/board-of-one-vs-advisory-board" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/compare/board-of-one-vs-advisory-board" />
	<meta property="og:title" content="Board of One vs Advisory Board - Equity-Free Alternative for Founders" />
	<meta property="og:description" content="Get strategic guidance without giving up equity or scheduling monthly meetings." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Board of One vs Advisory Board - Equity-Free Alternative for Founders" />
	<meta name="twitter:description" content="Get strategic guidance without giving up equity or scheduling monthly meetings." />
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
					Board of One vs Advisory Board
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Advisory boards cost equity and are available monthly. Is there a better way to get strategic guidance without diluting your cap table?
				</p>
			</div>
		</section>

		<!-- The Real Cost -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					The real cost of advisory boards
				</h2>
				<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-8 border border-neutral-200 dark:border-neutral-700">
					<div class="grid md:grid-cols-4 gap-6 text-center">
						<div>
							<div class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">0.5%</div>
							<div class="text-sm text-neutral-600 dark:text-neutral-400">Typical advisor equity</div>
						</div>
						<div>
							<div class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">£50k</div>
							<div class="text-sm text-neutral-600 dark:text-neutral-400">At £10M exit</div>
						</div>
						<div>
							<div class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">£500k</div>
							<div class="text-sm text-neutral-600 dark:text-neutral-400">At £100M exit</div>
						</div>
						<div>
							<div class="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">12</div>
							<div class="text-sm text-neutral-600 dark:text-neutral-400">Hours/year typical access</div>
						</div>
					</div>
				</div>
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
								<th class="text-left py-4 px-4 font-medium text-neutral-900 dark:text-neutral-100">Advisory Board</th>
								<th class="text-left py-4 pl-4 font-medium text-brand-600 dark:text-brand-400">Board of One</th>
							</tr>
						</thead>
						<tbody>
							{#each comparisonData as row}
								<tr class="border-b border-neutral-200 dark:border-neutral-700">
									<td class="py-4 pr-4 font-medium text-neutral-700 dark:text-neutral-300">{row.aspect}</td>
									<td class="py-4 px-4 text-neutral-600 dark:text-neutral-400">{row.advisory}</td>
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
						<p class="text-neutral-700 dark:text-neutral-300">You primarily need strategic thinking, not networking</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">Equity preservation matters—every point counts</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You need guidance now, not at next month's meeting</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You want multiple perspectives without hiring multiple advisors</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You value documented decisions over verbal advice</p>
					</div>
				</div>
			</div>
		</section>

		<!-- When to Choose Advisory Board -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					When to choose an advisory board
				</h2>
				<div class="space-y-4">
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You need introductions to investors, customers, or partners</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">Their name on your site adds credibility</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">They've seen your exact situation many times before</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You want a long-term relationship and mentorship</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">The equity cost is worth it for the relationship value</p>
					</div>
				</div>
			</div>
		</section>

		<!-- The Smart Combination -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The smart combination
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Many founders are rethinking how they use advisors:
					</p>
					<ul class="mt-4 space-y-2 text-lg text-neutral-600 dark:text-neutral-400">
						<li><strong>1-2 advisors</strong> for network/credibility (where relationship value is irreplaceable)</li>
						<li><strong>Board of One</strong> for everything else (daily strategic thinking, decision frameworks)</li>
					</ul>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						This gives you the best of both worlds: human relationships where they matter, AI-powered strategic support for everything else. And you keep more of your cap table.
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
					Keep your equity
				</h2>
				<p class="text-lg text-brand-100 mb-8">
					Get strategic guidance without diluting your cap table.
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
