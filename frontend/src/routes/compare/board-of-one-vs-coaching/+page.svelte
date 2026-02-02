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
		slug: 'board-of-one-vs-coaching',
		title: 'Board of One vs Executive Coaching',
		description: 'Compare Board of One to executive coaching. Understand when each approach works best for founder decision-making.',
		datePublished: '2025-01-15',
		dateModified: '2025-01-20'
	};

	const faqs = [
		{
			question: 'Can AI really replace a human coach?',
			answer: 'Not for everything. Coaches excel at emotional support, accountability, and helping you understand yourself better. What Board of One replaces is the strategic thinking and decision-making support—frameworks, analysis, and recommendations. If you need someone to help you process feelings about a failed hire, that\'s a coach. If you need to decide whether to hire at all, that\'s Board of One.'
		},
		{
			question: 'What about the accountability a coach provides?',
			answer: 'Board of One documents decisions and generates action items, creating a natural accountability mechanism. But it doesn\'t call you to check in or hold you emotionally accountable. If external accountability is your primary need, a coach might be better. Most founders find that documented decisions and clear next steps provide sufficient self-accountability.'
		},
		{
			question: 'Is coaching worth £500-2,000 per session?',
			answer: 'Depends on what you get from it. If coaching genuinely transforms how you think and operate, the ROI can be significant. But many founders find they primarily use coaching for strategic thinking—which Board of One provides at a fraction of the cost. Evaluate what you actually get from sessions before deciding.'
		},
		{
			question: 'Can I use both?',
			answer: 'Absolutely. Many founders use Board of One for day-to-day strategic decisions and keep a coach for periodic deep dives on personal development, leadership challenges, or emotional processing. They serve different functions. Using Board of One for the frequent stuff can make occasional coaching more focused and valuable.'
		},
		{
			question: 'My coach knows my business well. Does Board of One?',
			answer: 'Board of One stores your business context permanently—your metrics, positioning, constraints, and strategic priorities. It doesn\'t forget between sessions. A coach who sees you monthly might spend 15 minutes getting back up to speed; Board of One never needs that. For strategic context, it\'s actually better. For personal context (your stress levels, family situation, etc.), a human coach wins.'
		},
		{
			question: 'How do I decide which is right for me?',
			answer: 'Ask yourself: What do I actually need from coaching? If it\'s primarily strategic thinking and decision support—Board of One. If it\'s personal development, emotional processing, or accountability—coaching. If it\'s both—maybe both, with Board of One handling the frequent strategic needs and coaching handling the deeper personal work.'
		}
	];

	const breadcrumbSchema = createCompareBreadcrumbSchema(pageConfig);
	const articleSchema = createComparePageSchema(pageConfig);
	const faqSchema = createFeatureFAQSchema(faqs);

	const comparisonData = [
		{ aspect: 'Cost', coaching: '£500-2,000 per session', boardOfOne: 'Fixed monthly subscription' },
		{ aspect: 'Availability', coaching: 'Weekly or bi-weekly sessions', boardOfOne: '24/7, instant access' },
		{ aspect: 'Perspectives', coaching: 'One person\'s viewpoint', boardOfOne: 'Multiple expert personas' },
		{ aspect: 'Documentation', coaching: 'You take notes (maybe)', boardOfOne: 'Full decision logs automatically' },
		{ aspect: 'Context retention', coaching: 'Rebuilds each session', boardOfOne: 'Always loaded, never forgets' },
		{ aspect: 'Emotional support', coaching: 'Strong', boardOfOne: 'Limited' },
		{ aspect: 'Accountability', coaching: 'Human follow-up', boardOfOne: 'Documented actions' }
	];
</script>

<svelte:head>
	<title>Board of One vs Executive Coaching - Which Is Right for Founders?</title>
	<meta name="description" content="Compare Board of One to executive coaching for founders. See costs, availability, and when each approach works best for your decision-making needs." />
	<link rel="canonical" href="https://boardof.one/compare/board-of-one-vs-coaching" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/compare/board-of-one-vs-coaching" />
	<meta property="og:title" content="Board of One vs Executive Coaching - Which Is Right for Founders?" />
	<meta property="og:description" content="Compare Board of One to executive coaching for founders. When does each work best?" />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Board of One vs Executive Coaching - Which Is Right for Founders?" />
	<meta name="twitter:description" content="Compare Board of One to executive coaching for founders. When does each work best?" />
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
					Board of One vs Executive Coaching
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Executive coaching costs £500-2,000 per session. Is it worth it, and when does Board of One make more sense?
				</p>
			</div>
		</section>

		<!-- Quick Comparison Table -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					Quick comparison
				</h2>
				<div class="overflow-x-auto">
					<table class="w-full">
						<thead>
							<tr class="border-b border-neutral-200 dark:border-neutral-700">
								<th class="text-left py-4 pr-4 font-medium text-neutral-500 dark:text-neutral-400"></th>
								<th class="text-left py-4 px-4 font-medium text-neutral-900 dark:text-neutral-100">Executive Coaching</th>
								<th class="text-left py-4 pl-4 font-medium text-brand-600 dark:text-brand-400">Board of One</th>
							</tr>
						</thead>
						<tbody>
							{#each comparisonData as row}
								<tr class="border-b border-neutral-100 dark:border-neutral-800">
									<td class="py-4 pr-4 font-medium text-neutral-700 dark:text-neutral-300">{row.aspect}</td>
									<td class="py-4 px-4 text-neutral-600 dark:text-neutral-400">{row.coaching}</td>
									<td class="py-4 pl-4 text-neutral-600 dark:text-neutral-400">{row.boardOfOne}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		</section>

		<!-- When to Choose Board of One -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					When to choose Board of One
				</h2>
				<div class="space-y-4">
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You primarily need strategic thinking and decision frameworks</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You want guidance available immediately, not next Tuesday</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You value multiple perspectives over a single viewpoint</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You want decisions documented automatically</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">Cost matters—you can't justify £1,000+/session</p>
					</div>
				</div>
			</div>
		</section>

		<!-- When to Choose Coaching -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					When to choose coaching
				</h2>
				<div class="space-y-4">
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You need emotional support and processing</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You value external accountability from a human</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You're working through personal leadership challenges</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You want a long-term relationship with someone who knows your full story</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You're focused on personal development, not just business decisions</p>
					</div>
				</div>
			</div>
		</section>

		<!-- Can You Use Both -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Can you use both?
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Yes, and many founders do. They serve different purposes:
					</p>
					<ul class="mt-4 space-y-2 text-lg text-neutral-600 dark:text-neutral-400">
						<li><strong>Board of One</strong> for frequent strategic decisions—pricing, prioritization, hiring framework</li>
						<li><strong>Coaching</strong> for periodic deep dives—leadership development, personal challenges, career direction</li>
					</ul>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Using Board of One for the everyday strategic stuff makes your coaching time more focused and valuable. You're not spending £500/hour deciding whether to raise prices—you're spending it on the deeper work that only a human relationship can provide.
					</p>
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

		<!-- CTA -->
		<section class="py-16 md:py-24 bg-gradient-to-r from-brand-600 to-brand-700 dark:from-brand-700 dark:to-brand-800">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-3xl md:text-4xl font-bold text-white mb-4">
					Ready to try Board of One?
				</h2>
				<p class="text-lg text-brand-100 mb-8">
					See how it compares to your current coaching or advisory relationships.
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
