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
		slug: 'founder-bottleneck',
		title: 'Break the Founder Bottleneck',
		description: 'Stop being the blocker on every decision. Board of One helps you create frameworks and processes that let you delegate with confidence.',
		datePublished: '2025-01-15',
		dateModified: '2025-01-20'
	};

	const faqs = [
		{
			question: 'How does Board of One help me delegate decisions?',
			answer: 'By making your decision-making process explicit and documented. When you deliberate on a decision, Board of One captures the frameworks, criteria, and reasoning you use. These become reusable templates. Instead of someone asking "what would the founder do?", they can reference documented decision logic and make the call themselves.'
		},
		{
			question: 'What if I make different decisions than the system suggests?',
			answer: 'That\'s valuable data. When you override a recommendation, you\'re teaching the system (and yourself) about implicit criteria that weren\'t captured. Over time, this surfaces your actual decision-making patterns—often revealing logic you didn\'t consciously articulate. The goal isn\'t to replace your judgment, but to externalize and scale it.'
		},
		{
			question: 'I\'m afraid of losing control by delegating',
			answer: 'The bottleneck usually isn\'t about control—it\'s about trust and information asymmetry. When decisions are documented with clear reasoning, you can review them asynchronously instead of being involved synchronously. You maintain oversight without being the blocker. And when something goes wrong, you have documentation to learn from.'
		},
		{
			question: 'Won\'t this just create more work documenting everything?',
			answer: 'Board of One does the documentation automatically during the deliberation process. You think through the decision as you normally would, but the output is structured and searchable. The documentation is a byproduct of decision-making, not extra work. And the time saved by not being consulted on every similar decision far exceeds the time invested.'
		},
		{
			question: 'What kinds of decisions can be "delegated" this way?',
			answer: 'Start with decisions that are frequent, have clear criteria, and where the downside of a suboptimal choice is manageable. Pricing exceptions, feature prioritization within guidelines, vendor selection under a threshold, hiring for defined roles. Keep strategic bets and high-stakes irreversible decisions with yourself—but those are rarer than you think.'
		},
		{
			question: 'How long until I see the bottleneck improve?',
			answer: 'You\'ll feel it within a few weeks. The first time someone makes a decision by referencing a previous deliberation instead of scheduling a meeting with you—that\'s the moment. The compounding effect comes over months as your decision library grows and patterns emerge. Most founders report reclaiming 5-10 hours per week within the first month.'
		}
	];

	const breadcrumbSchema = createUseCaseBreadcrumbSchema(pageConfig);
	const articleSchema = createUseCasePageSchema(pageConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>Break the Founder Bottleneck - Delegate Decisions With Confidence | Board of One</title>
	<meta name="description" content="Every decision waits for you? Board of One helps founders externalize decision-making frameworks so teams can move without constant consultation." />
	<link rel="canonical" href="https://boardof.one/use-cases/founder-bottleneck" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/use-cases/founder-bottleneck" />
	<meta property="og:title" content="Break the Founder Bottleneck - Delegate Decisions With Confidence" />
	<meta property="og:description" content="Every decision waits for you? Externalize your decision-making so teams can move." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Break the Founder Bottleneck - Delegate Decisions With Confidence" />
	<meta name="twitter:description" content="Every decision waits for you? Externalize your decision-making so teams can move." />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Use Case</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Break the Founder Bottleneck
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Every decision waits for you. Every call needs your input. You can't clone yourself—but you can externalize how you think, so others can make decisions without you.
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The problem: you're the single point of failure
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						You built this company. You know the context better than anyone. That's why every decision flows through you—because you can see implications others miss. But now you're the bottleneck.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Your calendar is packed with "quick questions." Your inbox is full of decisions waiting for your approval. Your team is blocked while you're in back-to-back meetings. The things only you can do—the strategic work, the vision—get squeezed out.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						The frustrating part? Most of these decisions don't actually need you. They need the <em>way you think</em>—your frameworks, your criteria, your judgment applied to the situation. But that's locked in your head, so they wait.
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
						Board of One helps you externalize your decision-making. When you deliberate on decisions, the system captures the frameworks, criteria, and reasoning you use. These become documented patterns that others can reference.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Instead of "let me check with the founder," it becomes "let me check the decision framework." Your judgment scales because it's no longer locked in your head.
					</p>
				</div>
				<div class="space-y-6">
					<div class="flex gap-4">
						<div class="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-bold">1</div>
						<div>
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-1">Deliberate on decisions as you normally would</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Describe the situation, get multi-perspective analysis, and make your call. Board of One captures the entire process.</p>
						</div>
					</div>
					<div class="flex gap-4">
						<div class="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-bold">2</div>
						<div>
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-1">Build a library of decision patterns</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Over time, similar decisions reveal your implicit frameworks. Pricing exceptions, feature prioritization, vendor selection—patterns emerge.</p>
						</div>
					</div>
					<div class="flex gap-4">
						<div class="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-bold">3</div>
						<div>
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-1">Enable others to decide without you</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Team members can reference past decisions and frameworks. Similar situation? Check how it was handled before. You review asynchronously, not synchronously.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Who This Is For -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					Who this is for
				</h2>
				<div class="grid md:grid-cols-3 gap-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Stage</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Any stage where you have a team that needs decisions from you. Solo founders don't have this problem—yet.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Situation</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Your calendar is full of "quick questions." Teams are blocked waiting for you. Strategic work keeps getting pushed.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Mindset</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">You want to delegate but struggle to let go. You need confidence that decisions will be made well without you.</p>
					</div>
				</div>
			</div>
		</section>

		<!-- The Symptoms -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					Signs you're the bottleneck
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-red-600 dark:text-red-400"><path d="M18 6L6 18M6 6l12 12"/></svg>
						</div>
						<p class="text-neutral-600 dark:text-neutral-400">"Can I get 5 minutes?" is your most-heard phrase</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-red-600 dark:text-red-400"><path d="M18 6L6 18M6 6l12 12"/></svg>
						</div>
						<p class="text-neutral-600 dark:text-neutral-400">Your inbox has 50+ messages needing your input</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-red-600 dark:text-red-400"><path d="M18 6L6 18M6 6l12 12"/></svg>
						</div>
						<p class="text-neutral-600 dark:text-neutral-400">Projects stall when you're traveling or sick</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-red-600 dark:text-red-400"><path d="M18 6L6 18M6 6l12 12"/></svg>
						</div>
						<p class="text-neutral-600 dark:text-neutral-400">You know how decisions should be made but can't articulate it</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-red-600 dark:text-red-400"><path d="M18 6L6 18M6 6l12 12"/></svg>
						</div>
						<p class="text-neutral-600 dark:text-neutral-400">Strategic thinking only happens on weekends or late nights</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-red-600 dark:text-red-400"><path d="M18 6L6 18M6 6l12 12"/></svg>
						</div>
						<p class="text-neutral-600 dark:text-neutral-400">You've hired good people but still make most decisions</p>
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
					<a href="/use-cases/delay-management-hires" class="block bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Delay Your Next Management Hire</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Get management thinking without the headcount</p>
					</a>
					<a href="/use-cases/strategic-decisions" class="block bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 text-sm mb-1">Making Strategic Decisions Solo</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Big decisions without a board</p>
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
