<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { createOrganizationSchema, serializeJsonLd } from '$lib/utils/jsonld';

	const organizationSchema = createOrganizationSchema();

	const comparisons = [
		{
			slug: 'board-of-one-vs-coaching',
			title: 'Board of One vs Executive Coaching',
			alternative: 'Executive Coaching',
			cost: '£500-2,000/session',
			boAdvantage: '24/7 availability, multiple perspectives, full documentation',
			icon: 'user'
		},
		{
			slug: 'board-of-one-vs-advisory-board',
			title: 'Board of One vs Advisory Board',
			alternative: 'Advisory Board',
			cost: '0.5-2% equity + scheduling',
			boAdvantage: 'No equity dilution, instant access, always available',
			icon: 'users'
		},
		{
			slug: 'board-of-one-vs-chatgpt',
			title: 'Board of One vs ChatGPT',
			alternative: 'ChatGPT / Generic AI',
			cost: '$20/month',
			boAdvantage: 'Context-aware, structured deliberation, multi-expert analysis',
			icon: 'message-square'
		},
		{
			slug: 'board-of-one-vs-consultants',
			title: 'Board of One vs Consultants',
			alternative: 'Management Consultants',
			cost: '£1,000-5,000/day',
			boAdvantage: 'Fraction of cost, always available, no project minimums',
			icon: 'briefcase'
		},
		{
			slug: 'board-of-one-vs-masterminds',
			title: 'Board of One vs Masterminds',
			alternative: 'Mastermind Groups',
			cost: '$5,000-50,000/year',
			boAdvantage: 'Private, instant, no scheduling, judgment-free',
			icon: 'users'
		}
	];

	const iconPaths: Record<string, string> = {
		user: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
		users: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
		'message-square': 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
		briefcase: 'M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2zM16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16'
	};
</script>

<svelte:head>
	<title>Compare Board of One - Coaching, Advisors, Consultants & AI</title>
	<meta name="description" content="See how Board of One compares to executive coaching, advisory boards, consultants, and ChatGPT. Find the right solution for your stage and budget." />
	<link rel="canonical" href="https://boardof.one/compare" />
	<meta property="og:type" content="website" />
	<meta property="og:url" content="https://boardof.one/compare" />
	<meta property="og:title" content="Compare Board of One - Coaching, Advisors, Consultants & AI" />
	<meta property="og:description" content="See how Board of One compares to executive coaching, advisory boards, consultants, and ChatGPT." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Compare Board of One - Coaching, Advisors, Consultants & AI" />
	<meta name="twitter:description" content="See how Board of One compares to executive coaching, advisory boards, consultants, and ChatGPT." />
	<meta name="twitter:image" content="https://boardof.one/og-image.png" />
	{@html `<script type="application/ld+json">${serializeJsonLd(organizationSchema)}</script>`}
</svelte:head>

<div class="min-h-screen flex flex-col bg-white dark:bg-neutral-900">
	<Header />

	<main class="flex-1">
		<!-- Hero -->
		<section class="py-16 md:py-24 bg-gradient-to-b from-brand-50 to-white dark:from-neutral-800 dark:to-neutral-900">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					How does Board of One<br />
					<span class="text-brand-600 dark:text-brand-400 italic">compare?</span>
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
					Understand where Board of One fits relative to coaching, advisors, consultants, and AI tools.
				</p>
			</div>
		</section>

		<!-- Comparison Grid -->
		<section class="py-16 md:py-24">
			<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
				<div class="space-y-6">
					{#each comparisons as comparison}
						<a href="/compare/{comparison.slug}" class="group block bg-neutral-50 dark:bg-neutral-800 rounded-2xl p-6 md:p-8 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-all hover:shadow-lg">
							<div class="flex flex-col md:flex-row md:items-center gap-6">
								<div class="flex items-center gap-4 flex-1">
									<div class="w-12 h-12 rounded-xl bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
										<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400">
											<path d={iconPaths[comparison.icon]} />
										</svg>
									</div>
									<div>
										<span class="text-xs font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Comparison</span>
										<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
											{comparison.title}
										</h2>
									</div>
								</div>
								<div class="flex flex-col md:flex-row gap-4 md:gap-8 md:items-center">
									<div class="text-center md:text-right">
										<p class="text-xs text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{comparison.alternative} costs</p>
										<p class="text-lg font-bold text-neutral-700 dark:text-neutral-300">{comparison.cost}</p>
									</div>
									<div class="hidden md:block w-px h-12 bg-neutral-200 dark:bg-neutral-700"></div>
									<div class="md:w-64">
										<p class="text-xs text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Board of One advantage</p>
										<p class="text-sm text-neutral-600 dark:text-neutral-400">{comparison.boAdvantage}</p>
									</div>
								</div>
								<div class="flex-shrink-0">
									<span class="inline-flex items-center gap-1 text-sm font-medium text-brand-600 dark:text-brand-400 group-hover:gap-2 transition-all">
										Compare
										<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
									</span>
								</div>
							</div>
						</a>
					{/each}
				</div>
			</div>
		</section>

		<!-- Summary -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800 border-y border-neutral-200 dark:border-neutral-700">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The bottom line
				</h2>
				<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
					Board of One isn't trying to replace everything. Executive coaches are valuable. Advisors provide real relationships. Consultants bring deep expertise. But if you need management-level thinking <em>right now</em>, at a fraction of the cost, with no scheduling—that's where Board of One fits.
				</p>
			</div>
		</section>

		<!-- CTA -->
		<section class="py-16 md:py-24 bg-gradient-to-r from-brand-600 to-brand-700 dark:from-brand-700 dark:to-brand-800">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-3xl md:text-4xl font-bold text-white mb-4">
					Ready to see how it works?
				</h2>
				<p class="text-lg text-brand-100 mb-8">
					Request early access and experience the difference.
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
