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
		slug: 'board-of-one-vs-masterminds',
		title: 'Board of One vs Mastermind Groups',
		description: 'Compare Board of One to mastermind groups and peer networks. Understand when peer support beats AI support, and vice versa.',
		datePublished: '2025-01-15',
		dateModified: '2025-01-20'
	};

	const faqs = [
		{
			question: 'Don\'t I need human connection with other founders?',
			answer: 'Yes, probably. Board of One doesn\'t replace the emotional support and camaraderie of peer relationships. What it replaces is the strategic input you get from masterminds—the decision-making help. Many founders find they want both: a community for connection and support, and Board of One for immediate, private strategic guidance.'
		},
		{
			question: 'Masterminds give me real-world experience from peers',
			answer: 'They do—that\'s valuable. But mastermind experience is limited to who\'s in the room. Board of One provides multiple expert perspectives (finance, marketing, operations, product) on every decision. You might get one founder with marketing experience in your mastermind; Board of One gives you a marketing perspective every time, plus four others.'
		},
		{
			question: 'What about the accountability masterminds provide?',
			answer: 'Mastermind accountability comes from social pressure and relationship. Board of One accountability comes from documented decisions and clear action items. Different mechanisms, similar outcome. If you thrive on social accountability, keep the mastermind. If you just need clear next steps, Board of One handles that.'
		},
		{
			question: 'I don\'t want to share sensitive business details in a group',
			answer: 'That\'s a real limitation of masterminds. Even with NDAs, you might hesitate to share financial details, strategic concerns, or personnel issues with peers who could be competitors. Board of One is completely private—share anything without worrying about who might hear.'
		},
		{
			question: 'Masterminds help with things beyond business decisions',
			answer: 'True—mental health, work-life balance, family pressures, the emotional journey of entrepreneurship. Board of One doesn\'t help with these. For holistic founder support, a good peer group is valuable. For decision-making specifically, Board of One is more focused and available.'
		},
		{
			question: 'Can I use Board of One to prepare for mastermind meetings?',
			answer: 'Absolutely. Many founders use Board of One to think through decisions before bringing them to their mastermind. You arrive with clearer framing, having already considered multiple angles. The mastermind discussion becomes more focused and valuable because you\'ve done the preliminary analysis.'
		}
	];

	const breadcrumbSchema = createCompareBreadcrumbSchema(pageConfig);
	const articleSchema = createComparePageSchema(pageConfig);
	const faqSchema = createFeatureFAQSchema(faqs);

	const comparisonData = [
		{ aspect: 'Cost', masterminds: '$5,000-50,000/year', boardOfOne: 'Fixed monthly subscription' },
		{ aspect: 'Availability', masterminds: 'Monthly meetings + async', boardOfOne: '24/7, instant' },
		{ aspect: 'Perspectives', masterminds: 'Limited to group members', boardOfOne: 'Multiple expert personas' },
		{ aspect: 'Privacy', masterminds: 'Shared with group (6-12 people)', boardOfOne: 'Completely private' },
		{ aspect: 'Scheduling', masterminds: 'Fixed meeting times', boardOfOne: 'On-demand, no scheduling' },
		{ aspect: 'Emotional support', masterminds: 'Strong peer relationships', boardOfOne: 'Limited' },
		{ aspect: 'Documentation', masterminds: 'Informal notes', boardOfOne: 'Full decision logs' }
	];
</script>

<svelte:head>
	<title>Board of One vs Mastermind Groups - Private Strategic Support for Founders</title>
	<meta name="description" content="Mastermind groups cost $5,000-50,000/year and require scheduling. Board of One provides instant, private strategic support. Compare the trade-offs." />
	<link rel="canonical" href="https://boardof.one/compare/board-of-one-vs-masterminds" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/compare/board-of-one-vs-masterminds" />
	<meta property="og:title" content="Board of One vs Mastermind Groups - Private Strategic Support" />
	<meta property="og:description" content="Instant, private strategic support vs. scheduled group meetings. Compare the trade-offs." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Board of One vs Mastermind Groups - Private Strategic Support" />
	<meta name="twitter:description" content="Instant, private strategic support vs. scheduled group meetings. Compare the trade-offs." />
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
					Board of One vs Mastermind Groups
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Mastermind groups provide peer support and community. Board of One provides instant, private strategic guidance. Which do you need?
				</p>
			</div>
		</section>

		<!-- The Trade-off -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Different problems, different solutions
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Mastermind groups solve two problems: loneliness (the emotional isolation of being a founder) and strategic thinking (getting outside perspectives on decisions).
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One only solves one: strategic thinking. If you need community, connection, and emotional support from peers who understand—a mastermind or peer group might be right for you.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						But if your primary need is getting help with specific decisions, having to schedule meetings, share with a group, and work within someone else's agenda might not be the best fit.
					</p>
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
								<th class="text-left py-4 px-4 font-medium text-neutral-900 dark:text-neutral-100">Mastermind Groups</th>
								<th class="text-left py-4 pl-4 font-medium text-brand-600 dark:text-brand-400">Board of One</th>
							</tr>
						</thead>
						<tbody>
							{#each comparisonData as row}
								<tr class="border-b border-neutral-200 dark:border-neutral-700">
									<td class="py-4 pr-4 font-medium text-neutral-700 dark:text-neutral-300">{row.aspect}</td>
									<td class="py-4 px-4 text-neutral-600 dark:text-neutral-400">{row.masterminds}</td>
									<td class="py-4 pl-4 text-neutral-600 dark:text-neutral-400">{row.boardOfOne}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		</section>

		<!-- The Privacy Advantage -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The privacy advantage
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-4">Things you might hesitate to share in a mastermind</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-red-500">→</span>Exact revenue and financial details</li>
							<li class="flex items-start gap-2"><span class="text-red-500">→</span>Issues with specific team members</li>
							<li class="flex items-start gap-2"><span class="text-red-500">→</span>Concerns about a competitor in the room</li>
							<li class="flex items-start gap-2"><span class="text-red-500">→</span>Doubts about your own ability</li>
							<li class="flex items-start gap-2"><span class="text-red-500">→</span>Strategic moves you don't want leaked</li>
						</ul>
					</div>
					<div class="bg-brand-50 dark:bg-brand-900/20 rounded-xl p-6 border border-brand-200 dark:border-brand-800">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-4">With Board of One, share anything</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">✓</span>Complete financial transparency</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">✓</span>Honest assessment of team challenges</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">✓</span>Competitive concerns without filters</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">✓</span>Your real fears and uncertainties</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">✓</span>Strategic plans in full detail</li>
						</ul>
					</div>
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
						<p class="text-neutral-700 dark:text-neutral-300">You need help now, not at next month's meeting</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You have sensitive information you don't want to share with peers</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You want multiple expert perspectives, not just peer experience</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">Scheduling conflicts make regular meetings difficult</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-brand-600 dark:text-brand-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You want documented decisions, not just conversation</p>
					</div>
				</div>
			</div>
		</section>

		<!-- When to Choose Masterminds -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-8">
					When to choose mastermind groups
				</h2>
				<div class="space-y-4">
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You're lonely and want connection with peers who understand</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">Social accountability motivates you</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You value war stories and pattern-matching from similar founders</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">You want potential partnerships and referrals from peers</p>
					</div>
					<div class="flex gap-3">
						<div class="flex-shrink-0 w-6 h-6 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-neutral-600 dark:text-neutral-400"><polyline points="20 6 9 17 4 12"/></svg>
						</div>
						<p class="text-neutral-700 dark:text-neutral-300">The emotional journey of entrepreneurship is your biggest challenge</p>
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
						Absolutely. Many founders benefit from:
					</p>
					<ul class="mt-4 space-y-2 text-lg text-neutral-600 dark:text-neutral-400">
						<li><strong>Board of One</strong> for day-to-day decisions and private strategic thinking</li>
						<li><strong>Mastermind</strong> for peer connection, accountability, and emotional support</li>
					</ul>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Using Board of One between mastermind meetings means you arrive at meetings with clearer thinking—having already processed decisions privately. The mastermind time becomes more valuable because it's focused on what peers uniquely provide: connection and experience-sharing.
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
					Private, instant strategic support
				</h2>
				<p class="text-lg text-brand-100 mb-8">
					Get help with decisions without waiting for the next meeting.
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
