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
		slug: 'board-of-one-vs-chatgpt',
		title: 'Board of One vs ChatGPT',
		description: 'Why would you pay for Board of One when ChatGPT is cheaper? Understand the difference between generic AI and purpose-built business decision support.',
		datePublished: '2025-01-15',
		dateModified: '2025-01-20'
	};

	const faqs = [
		{
			question: 'Can\'t I just give ChatGPT my business context?',
			answer: 'You can—every single time. ChatGPT doesn\'t remember context between sessions (unless you\'re on Teams/Enterprise). So you\'ll spend the first 5-10 minutes of every conversation re-establishing who you are, what your business does, and what your constraints are. Board of One stores this permanently and references it automatically.'
		},
		{
			question: 'What about Custom GPTs?',
			answer: 'Custom GPTs help with instructions and some context, but they\'re still limited. They can\'t store detailed business metrics, track your decision history, or provide structured multi-perspective deliberation. They\'re better than vanilla ChatGPT, but still fundamentally different from a purpose-built business decision tool.'
		},
		{
			question: 'Is the output quality really that different?',
			answer: 'Yes, for business decisions. ChatGPT optimizes for helpfulness across all tasks—coding, writing, research, conversation. Board of One is purpose-built for founder decision-making. The prompting, persona design, deliberation structure, and output format are all optimized for this specific use case. Generic tools give generic results.'
		},
		{
			question: 'Can I use ChatGPT for quick questions and Board of One for big decisions?',
			answer: 'Absolutely. ChatGPT is great for research, writing, and quick questions. Board of One is for decisions that matter—where you need multi-perspective analysis, context-aware recommendations, and documented reasoning. Many founders use both, for different purposes.'
		},
		{
			question: 'What about Claude, Gemini, or other AI assistants?',
			answer: 'The same principles apply. General-purpose AI assistants are great at many things but not optimized for any one thing. Board of One is specifically designed for founder decision-making—the structure, the personas, the context management, the documentation. It\'s the difference between a Swiss Army knife and a chef\'s knife.'
		},
		{
			question: 'Won\'t ChatGPT eventually do everything Board of One does?',
			answer: 'Maybe, but probably not soon. General-purpose AI optimizes for breadth. Purpose-built tools optimize for depth. Even if ChatGPT can technically do everything, a tool designed specifically for business decisions will do it better—better prompting, better structure, better context management, better output format. That gap is unlikely to close quickly.'
		}
	];

	const breadcrumbSchema = createCompareBreadcrumbSchema(pageConfig);
	const articleSchema = createComparePageSchema(pageConfig);
	const faqSchema = createFeatureFAQSchema(faqs);

	const comparisonData = [
		{ aspect: 'Cost', chatgpt: '$20/month (Plus)', boardOfOne: 'Comparable' },
		{ aspect: 'Context retention', chatgpt: 'Per-session only', boardOfOne: 'Permanent, always loaded' },
		{ aspect: 'Perspectives', chatgpt: 'Single voice', boardOfOne: 'Multi-expert deliberation' },
		{ aspect: 'Business context', chatgpt: 'Re-enter every time', boardOfOne: 'Stored and referenced' },
		{ aspect: 'Decision structure', chatgpt: 'Freeform conversation', boardOfOne: 'Structured deliberation' },
		{ aspect: 'Documentation', chatgpt: 'Copy/paste manually', boardOfOne: 'Automatic decision logs' },
		{ aspect: 'Decision history', chatgpt: 'None', boardOfOne: 'Searchable archive' }
	];
</script>

<svelte:head>
	<title>Board of One vs ChatGPT - Why Purpose-Built Beats Generic AI</title>
	<meta name="description" content="ChatGPT is $20/month. Why pay more for Board of One? Learn why context-aware, structured deliberation beats generic AI for business decisions." />
	<link rel="canonical" href="https://boardof.one/compare/board-of-one-vs-chatgpt" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/compare/board-of-one-vs-chatgpt" />
	<meta property="og:title" content="Board of One vs ChatGPT - Why Purpose-Built Beats Generic AI" />
	<meta property="og:description" content="Why context-aware, structured deliberation beats generic AI for business decisions." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Board of One vs ChatGPT - Why Purpose-Built Beats Generic AI" />
	<meta name="twitter:description" content="Why context-aware, structured deliberation beats generic AI for business decisions." />
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
					Board of One vs ChatGPT
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					"Can't I just use ChatGPT?" It's a fair question. Here's why purpose-built beats generic for business decisions.
				</p>
			</div>
		</section>

		<!-- The Core Difference -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The core difference: generic vs. purpose-built
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						ChatGPT is excellent at many things: writing, coding, research, conversation. It's a Swiss Army knife—versatile, but not optimized for any single task.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One is a chef's knife—designed for one purpose (business decisions) and exceptional at it. The prompting, structure, context management, and output format are all optimized for helping founders make better decisions.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						The difference isn't just features—it's the quality and relevance of the output when you're making decisions that actually matter.
					</p>
				</div>
			</div>
		</section>

		<!-- Quick Comparison Table -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					Feature comparison
				</h2>
				<div class="overflow-x-auto">
					<table class="w-full">
						<thead>
							<tr class="border-b border-neutral-200 dark:border-neutral-700">
								<th class="text-left py-4 pr-4 font-medium text-neutral-500 dark:text-neutral-400"></th>
								<th class="text-left py-4 px-4 font-medium text-neutral-900 dark:text-neutral-100">ChatGPT</th>
								<th class="text-left py-4 pl-4 font-medium text-brand-600 dark:text-brand-400">Board of One</th>
							</tr>
						</thead>
						<tbody>
							{#each comparisonData as row}
								<tr class="border-b border-neutral-200 dark:border-neutral-700">
									<td class="py-4 pr-4 font-medium text-neutral-700 dark:text-neutral-300">{row.aspect}</td>
									<td class="py-4 px-4 text-neutral-600 dark:text-neutral-400">{row.chatgpt}</td>
									<td class="py-4 pl-4 text-neutral-600 dark:text-neutral-400">{row.boardOfOne}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		</section>

		<!-- The Context Problem -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The context problem
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-4">ChatGPT conversation</h3>
						<div class="space-y-3 text-sm text-neutral-600 dark:text-neutral-400">
							<p class="italic">"I run a B2B SaaS doing £500k ARR, bootstrapped, 3 employees. We're considering raising prices but worried about churn. Our current pricing is..."</p>
							<p class="text-xs text-neutral-500">(5 minutes later, you finally get to your question)</p>
							<p class="text-xs text-neutral-500">(Next session, repeat the entire context)</p>
						</div>
					</div>
					<div class="bg-brand-50 dark:bg-brand-900/20 rounded-xl p-6 border border-brand-200 dark:border-brand-800">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-4">Board of One conversation</h3>
						<div class="space-y-3 text-sm text-neutral-600 dark:text-neutral-400">
							<p class="italic">"Should we raise prices?"</p>
							<p class="text-xs text-brand-600 dark:text-brand-400">(System already knows: £500k ARR, bootstrapped, 3 employees, current pricing, margins, competitive positioning, past decisions...)</p>
							<p class="text-xs text-brand-600 dark:text-brand-400">(Every session, context is automatically loaded)</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Multi-Perspective Difference -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Single voice vs. multi-perspective
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none mb-8">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						ChatGPT gives you one voice—helpful, but limited. It tries to balance all considerations, which often means it doesn't push hard on any of them.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One gives you 3-5 expert personas who actively debate. Finance pushes on the numbers. Marketing considers positioning. Operations flags execution risk. They challenge each other's assumptions, surfacing tensions that a single voice smooths over.
					</p>
				</div>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">ChatGPT response</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400 italic">
							"There are several factors to consider when raising prices. On one hand... On the other hand... It depends on your specific situation..."
						</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Board of One deliberation</h3>
						<p class="text-sm text-neutral-600 dark:text-neutral-400 italic">
							"Finance: Your margins demand a price increase. Marketing: But your positioning is value-based... Operations: Can support handle the churn calls? Finance: The math still works even with 15% churn..."
						</p>
					</div>
				</div>
			</div>
		</section>

		<!-- When to Use Each -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					When to use each
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-4">Use ChatGPT for</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-neutral-400">→</span>Quick research and information gathering</li>
							<li class="flex items-start gap-2"><span class="text-neutral-400">→</span>Writing and editing</li>
							<li class="flex items-start gap-2"><span class="text-neutral-400">→</span>Coding and technical questions</li>
							<li class="flex items-start gap-2"><span class="text-neutral-400">→</span>General brainstorming</li>
							<li class="flex items-start gap-2"><span class="text-neutral-400">→</span>One-off questions that don't need context</li>
						</ul>
					</div>
					<div class="bg-brand-50 dark:bg-brand-900/20 rounded-xl p-6 border border-brand-200 dark:border-brand-800">
						<h3 class="font-bold text-brand-700 dark:text-brand-300 mb-4">Use Board of One for</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Strategic decisions with real stakes</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Decisions that need your business context</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Multi-perspective analysis</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Decisions you need to document and defend</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Building a library of decision frameworks</li>
						</ul>
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

		<!-- CTA -->
		<section class="py-16 md:py-24 bg-gradient-to-r from-brand-600 to-brand-700 dark:from-brand-700 dark:to-brand-800">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-3xl md:text-4xl font-bold text-white mb-4">
					Purpose-built for decisions
				</h2>
				<p class="text-lg text-brand-100 mb-8">
					See the difference context-aware, structured deliberation makes.
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
