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
		slug: 'tailored-to-you',
		title: 'Tailored to YOUR Business',
		description: 'Your business context informs every decision. Store your strategy, metrics, and constraints once—and watch every deliberation become more relevant.',
		category: 'Foundation',
		datePublished: '2024-01-15',
		dateModified: '2024-12-01'
	};

	const faqs = [
		{
			question: 'What business context should I provide?',
			answer: 'Start with the essentials: your business model, target market, key products/services, and current strategic priorities. Then add metrics like revenue, growth rate, key costs, and constraints like timeline or budget. The more context you provide, the more relevant recommendations become. You can always add more over time.'
		},
		{
			question: 'How is my context used in deliberations?',
			answer: 'Expert personas automatically reference your context when analyzing decisions. Discussing pricing? They know your current margins and competitive positioning. Evaluating a hire? They know your runway and current workload. This context isn\'t just background—it actively shapes the recommendations you receive.'
		},
		{
			question: 'Is my business information secure?',
			answer: 'Yes. Your business context is encrypted at rest and in transit, isolated to your account, and never shared with other users. We don\'t use your data to train AI models. You maintain full control and can delete your data at any time. Security is foundational to how we operate.'
		},
		{
			question: 'How do I update my context as my business evolves?',
			answer: 'Your context is fully editable at any time. Add new metrics as they become relevant, update your strategic priorities when they shift, remove constraints you\'ve overcome. We recommend reviewing your context quarterly or after major changes to ensure Board of One has an accurate picture.'
		},
		{
			question: 'Why does context make recommendations better?',
			answer: 'Generic advice fails because it has to work for everyone—which means it\'s optimized for no one. "You should raise prices" means nothing without knowing your market, margins, and customer price sensitivity. Context transforms generic guidance into specific, actionable recommendations for your situation.'
		},
		{
			question: 'What happens if I don\'t provide context?',
			answer: 'Board of One will still work, but recommendations will be less specific. Mentors and deliberations will ask clarifying questions instead of referencing known information. You\'ll get value, but less of it. For best results, invest 15-20 minutes upfront to capture your key context.'
		},
		{
			question: 'Can I have multiple business contexts?',
			answer: 'Yes. If you run multiple businesses or have distinct product lines that require different strategic thinking, you can maintain separate contexts. Each deliberation and mentor chat can reference the appropriate context for that conversation.'
		},
		{
			question: 'What if my situation is complex or unusual?',
			answer: 'That\'s exactly when context matters most. Generic advice breaks down for complex situations. Board of One lets you capture nuances: "We\'re bootstrapped by choice, not necessity" or "Our target customer is technically sophisticated but not technical." These details shape recommendations in ways that matter.'
		}
	];

	const breadcrumbSchema = createFeatureBreadcrumbSchema(featureConfig);
	const articleSchema = createFeaturePageSchema(featureConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>Business Context for AI Decisions - Board of One</title>
	<meta name="description" content="Generic advice is useless. Every recommendation should know your reality. Store your business context once and watch every AI interaction become more relevant." />
	<link rel="canonical" href="https://boardof.one/features/tailored-to-you" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/features/tailored-to-you" />
	<meta property="og:title" content="Business Context for AI Decisions - Board of One" />
	<meta property="og:description" content="Generic advice is useless. Store your context once, get relevant recommendations always." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Business Context for AI Decisions - Board of One" />
	<meta name="twitter:description" content="Generic advice is useless. Store your context once, get relevant recommendations always." />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Foundation</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Tailored to YOUR Business
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Generic advice is useless. Every recommendation Board of One gives you should know your reality—your model, your metrics, your constraints. Store it once, benefit everywhere.
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The problem: advice without context
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						"You should raise your prices." "Focus on one thing." "Hire when it hurts." You've heard this advice a thousand times. It's not wrong—it's just incomplete. Without knowing your specific situation, generic advice is impossible to act on.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Should you raise prices? Depends on your margins, your competitors, your customers' price sensitivity. Focus on one thing? Depends on what's working, what's not, and what your runway looks like. Every piece of guidance needs to be filtered through the reality of <em>your</em> business.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						That's why you spend so much time in conversations explaining your situation. Every advisor, every tool, every AI chatbot—you're starting from scratch, giving the same context over and over, hoping they'll understand enough to give useful guidance.
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
						Board of One lets you capture your business context once and automatically references it in every interaction. Your business model, target market, key metrics, competitive positioning, strategic priorities, constraints—all stored and available when you need guidance.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						No more explaining your situation from scratch. No more getting advice that doesn't fit your reality. When you ask about pricing, the system knows your margins. When you discuss hiring, it knows your runway. When you evaluate channels, it knows your current CAC.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						This context is the foundation of everything else. It's what makes Board of One's guidance specific rather than generic, actionable rather than theoretical.
					</p>
				</div>
			</div>
		</section>

		<!-- What You Store -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					What context you can store
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Business fundamentals</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Business model and revenue streams</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Target market and ideal customer profile</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Key products or services offered</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Competitive positioning and differentiation</li>
						</ul>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Metrics and constraints</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Current revenue and growth rate</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Key financial metrics (margins, CAC, LTV)</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Resource constraints (time, budget, team)</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Timeline and runway considerations</li>
						</ul>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Strategic priorities</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Current focus areas and goals</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>What success looks like for you</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>What you're explicitly NOT doing</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Key risks and concerns on your mind</li>
						</ul>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">History and learnings</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Past decisions and their outcomes</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>What's worked and what hasn't</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Lessons learned along the way</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Evolving understanding of your market</li>
						</ul>
					</div>
				</div>
			</div>
		</section>

		<!-- How It's Used -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					How your context gets used
				</h2>
				<div class="space-y-8">
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
						</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Decision deliberations</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Expert perspectives reference your context automatically. A pricing decision considers your margins and competitive landscape. A hiring decision considers your runway and growth rate. Every recommendation is grounded in your reality.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
						</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Mentor conversations</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Mentors already know your business. You can skip the setup and dive straight into the problem. "I'm thinking about entering the enterprise market"—and the mentor already knows you're currently SMB-focused and bootstrapped.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
						</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Analysis and insights</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Competitor analysis and benchmarking is filtered through your specific positioning. SEO recommendations target keywords relevant to your market. Data analysis highlights metrics that matter for your business model.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Context Evolves -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Your context evolves with your business
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Your business isn't static—neither is Board of One's understanding of it. Update your context as your business grows. Add new metrics as they become relevant. Update your strategic priorities when they shift. Remove constraints you've overcome.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						We recommend reviewing your context quarterly or after major changes. A funding round changes your constraints. A new product changes your positioning. A pivot changes your target market. Keep Board of One current and it keeps your recommendations current.
					</p>
					<p class="text-lg text-neutral-700 dark:text-neutral-300 leading-relaxed mt-4 font-medium">
						The more context you provide, the better your recommendations become.
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

		<!-- Part of the System -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4 text-center">
					The foundation of everything else
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-8 max-w-2xl mx-auto text-center">
					Your business context powers every other capability in Board of One.
				</p>
				<div class="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
					<a href="/features/data-analysis" class="block bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Data Analysis</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Your metrics become part of your context</p>
					</a>
					<a href="/features/mentor-chat" class="block bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Mentor Chat</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Mentors know your business before you ask</p>
					</a>
					<a href="/features/seo-generation" class="block bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">SEO Generation</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Keywords aligned with your positioning</p>
					</a>
					<a href="/features/decisions-replanning" class="block bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Decisions</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Every deliberation references your reality</p>
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
