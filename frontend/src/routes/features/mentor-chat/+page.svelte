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
		slug: 'mentor-chat',
		title: 'Mentor Chat',
		description: 'On-demand 1:1 conversations with AI mentors who know your business context. Brainstorm, explore ideas, and get guidance when you need it.',
		category: 'Option Generation',
		datePublished: '2024-01-15',
		dateModified: '2024-12-01'
	};

	const faqs = [
		{
			question: 'What types of mentors are available?',
			answer: 'Board of One offers mentors across strategic, financial, operational, marketing, and product domains. You can choose a Strategic Advisor for big-picture thinking, a Financial Analyst for number-crunching questions, a Growth Marketer for acquisition strategy, an Operations Expert for execution challenges, or a Product Thinker for feature decisions. Each brings a distinct perspective shaped by their domain expertise.'
		},
		{
			question: 'How is mentor chat different from ChatGPT?',
			answer: 'The key difference is context. ChatGPT doesn\'t know your business, your metrics, your constraints, or your past decisions. Board of One mentors do. When you ask about pricing, a mentor can reference your actual margins and competitor pricing. When you discuss hiring, they know your runway and current workload. This context makes guidance actionable rather than generic.'
		},
		{
			question: 'When should I use mentor chat vs. a full deliberation?',
			answer: 'Use mentor chat for exploration, brainstorming, and quick sanity checks. It\'s a 1:1 conversation with a single perspective. Use full deliberation when you need a decision: 3-5 experts debating your options with structured synthesis. Think of mentor chat as the hallway conversation before the boardroom meeting.'
		},
		{
			question: 'Does the mentor remember my previous conversations?',
			answer: 'Yes. Each mentor conversation is saved and the mentor can reference past discussions within your session. Your business context is always available, so mentors know your situation even in new conversations. This creates continuity—you\'re building a relationship, not starting from scratch each time.'
		},
		{
			question: 'Can I switch mentors mid-conversation?',
			answer: 'Yes. If you start talking strategy and realize you need financial analysis, you can switch mentors within the same session. The new mentor will have access to the conversation context so you don\'t need to re-explain your question. This makes it easy to get multiple perspectives without starting over.'
		},
		{
			question: 'How does the mentor know about my business?',
			answer: 'Mentors access the business context you\'ve stored in Board of One: your business model, target market, key metrics, competitive positioning, strategic priorities, and constraints. They also see relevant data insights and past decisions. The more context you provide, the more relevant their guidance becomes.'
		},
		{
			question: 'Is mentor chat available 24/7?',
			answer: 'Yes. One of the key benefits for solopreneurs is access to expert thinking whenever you need it. 11pm before a big pitch? Sunday morning strategy session? Your mentors are available. No scheduling, no waiting, no timezone coordination.'
		},
		{
			question: 'Can I escalate a mentor conversation to a full deliberation?',
			answer: 'Absolutely. If your mentor chat surfaces a decision that needs deeper analysis, you can escalate directly to a full deliberation. The conversation context transfers, so the expert panel understands what you\'ve already explored. This creates a natural flow from ideation to decision.'
		}
	];

	const breadcrumbSchema = createFeatureBreadcrumbSchema(featureConfig);
	const articleSchema = createFeaturePageSchema(featureConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>AI Mentor Chat for Business Decisions - Board of One</title>
	<meta name="description" content="On-demand 1:1 conversations with AI mentors who know your business context. Get expert guidance at 11pm, explore ideas, and brainstorm strategy—no scheduling required." />
	<link rel="canonical" href="https://boardof.one/features/mentor-chat" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/features/mentor-chat" />
	<meta property="og:title" content="AI Mentor Chat for Business Decisions - Board of One" />
	<meta property="og:description" content="Expert guidance whenever you need it. No scheduling, no waiting." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="AI Mentor Chat for Business Decisions - Board of One" />
	<meta name="twitter:description" content="Expert guidance whenever you need it. No scheduling, no waiting." />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Option Generation</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Mentor Chat
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					11pm before a big decision? Your mentor is available. On-demand conversations with AI experts who already know your business—no scheduling, no waiting, no explaining from scratch.
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The problem: thinking alone
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Running a business solo means you're often the only person thinking about your problems. There's no co-founder to bounce ideas off at 10pm. No advisor available when you need to sanity-check an approach. No sounding board when you're weighing options.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						You can hire consultants, but they're expensive and require scheduling. You can ask friends, but they don't know your business deeply enough. You can use generic AI tools, but explaining your situation from scratch every time is exhausting—and the advice is still generic.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						What you need is someone who knows your business, is available whenever, and can think through problems with you. Not someone who makes decisions for you—someone who helps you think better.
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
						Mentor chat gives you access to expert perspectives whenever you need them. Choose from different mentor archetypes—strategic, financial, operational, growth—and have exploratory conversations that help you think through challenges.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						The key difference: these mentors already know your business. They've read your context, seen your metrics, understood your constraints. You can skip the setup and get straight to the problem. "I'm thinking about raising prices"—and the mentor already knows your current pricing, margins, and competitive landscape.
					</p>
				</div>
				<div class="space-y-8">
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">1</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Choose your mentor</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Select from expert archetypes: Strategic Advisor, Financial Analyst, Growth Marketer, Operations Expert, Product Thinker, and more. Each brings a distinct lens to your problem.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">2</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Context-aware conversation</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Your mentor already knows your business context, metrics, and past decisions. No explaining from scratch. Dive straight into the problem you're wrestling with.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">3</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Brainstorm and explore</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Talk through ideas, get challenged on assumptions, explore options in a free-form conversation. When you're ready to decide, escalate to a full deliberation.</p>
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
						Yes, you can talk to ChatGPT. But ChatGPT doesn't know your business model, your runway, your target customer, or your competitive positioning. Every conversation starts from zero. And the advice you get is necessarily generic—it has to work for any business, which means it's optimized for none.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One mentors are different. They operate with full awareness of your context. When a Financial Analyst mentor discusses your pricing, they know your margins. When a Growth Marketer explores channel strategy, they know your current CAC. This context transforms generic advice into specific, actionable guidance.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Think of it as the difference between asking a stranger for directions versus asking someone who knows where you're starting from and where you need to go.
					</p>
				</div>
			</div>
		</section>

		<!-- Example Use Cases -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					When to use mentor chat
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Early-stage ideation</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">When you're not ready for a full decision session but need to explore a topic. "I'm thinking about launching a second product line—help me think through this." Perfect for testing ideas before committing resources.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Quick sanity checks</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">"Am I missing something obvious here?" Get a fast second opinion before you commit to a direction. Sometimes you just need someone to confirm your thinking—or challenge it.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Specialized expertise</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Need financial modeling help? Pricing strategy input? Marketing channel analysis? Pick a mentor with the right expertise for your question. Access specialized thinking without hiring specialists.</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Processing outcomes</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">After a decision plays out, debrief with a mentor. "This didn't go as planned—help me understand what I missed." Learn from results and improve your decision-making process.</p>
					</div>
				</div>
			</div>
		</section>

		<!-- Mentor vs Deliberation -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Mentor chat vs. full deliberation
				</h2>
				<div class="grid md:grid-cols-2 gap-8">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-brand-600 dark:text-brand-400 mb-3">Mentor Chat</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>1:1 conversation with one expert</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Exploratory, open-ended discussion</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Quick brainstorming and ideation</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Single perspective, deep dive</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Best for: exploration, sanity checks, specialized questions</li>
						</ul>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-brand-600 dark:text-brand-400 mb-3">Full Deliberation</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>3-5 expert perspectives debating</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Structured multi-round analysis</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Comprehensive option evaluation</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Synthesized recommendation with actions</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Best for: decisions, trade-offs, commitments</li>
						</ul>
					</div>
				</div>
				<p class="text-neutral-600 dark:text-neutral-400 text-center mt-6 font-medium">
					Use mentor chat to explore. Use <a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">deliberation</a> to decide.
				</p>
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
					Part of a cohesive system
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-8 max-w-2xl mx-auto text-center">
					Mentor conversations don't exist in isolation. They're connected to everything else in Board of One.
				</p>
				<div class="grid md:grid-cols-3 gap-6 mb-8">
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Context-Aware</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Mentors draw from your <a href="/features/tailored-to-you" class="text-brand-600 dark:text-brand-400 underline">business context</a> and <a href="/features/data-analysis" class="text-brand-600 dark:text-brand-400 underline">data insights</a> automatically.</p>
					</div>
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Escalation Path</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">When exploration surfaces a decision, escalate to a full <a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">deliberation session</a>.</p>
					</div>
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Market Awareness</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Mentors can reference your <a href="/features/competitor-analysis" class="text-brand-600 dark:text-brand-400 underline">competitive landscape</a> when relevant.</p>
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
