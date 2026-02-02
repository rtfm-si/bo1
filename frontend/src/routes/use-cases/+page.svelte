<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { createOrganizationSchema, serializeJsonLd } from '$lib/utils/jsonld';

	const organizationSchema = createOrganizationSchema();

	const useCases = [
		{
			slug: 'delay-management-hires',
			title: 'Delay Your Next Management Hire',
			description: 'Get management-level thinking without the £100k+ headcount. Build the capability before building the org chart.',
			problem: 'Need senior perspective but can\'t justify the salary yet',
			icon: 'users'
		},
		{
			slug: 'founder-bottleneck',
			title: 'Break the Founder Bottleneck',
			description: 'Stop being the blocker on every decision. Create frameworks that let you delegate with confidence.',
			problem: 'Every decision waits for you, but you can\'t clone yourself',
			icon: 'unlock'
		},
		{
			slug: 'operating-without-org',
			title: 'Operating Without an Org Chart',
			description: 'Run lean by choice, not necessity. Get full management capability without building a management team.',
			problem: 'Staying lean but still need sophisticated decision-making',
			icon: 'briefcase'
		},
		{
			slug: 'strategic-decisions',
			title: 'Making Strategic Decisions Solo',
			description: 'Big decisions without a board. Get multi-perspective analysis for the calls that shape your company.',
			problem: 'No board, no co-founder, but facing board-level decisions',
			icon: 'compass'
		},
		{
			slug: 'advisor-alternative',
			title: 'On-Demand Expert Guidance',
			description: 'Skip the expensive advisors and sporadic availability. Get expertise when you need it, not when they\'re free.',
			problem: 'Advisors are expensive, slow, and rarely available',
			icon: 'message-circle'
		}
	];

	const iconPaths: Record<string, string> = {
		users: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
		unlock: 'M19 11H5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2zM7 11V7a5 5 0 0 1 9.9-1',
		briefcase: 'M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2zM16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16',
		compass: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM16.24 7.76l-2.12 6.36-6.36 2.12 2.12-6.36 6.36-2.12z',
		'message-circle': 'M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z'
	};
</script>

<svelte:head>
	<title>Use Cases - Board of One</title>
	<meta name="description" content="Discover how Board of One helps founders delay management hires, break bottlenecks, and make strategic decisions without a full executive team." />
	<link rel="canonical" href="https://boardof.one/use-cases" />
	<meta property="og:type" content="website" />
	<meta property="og:url" content="https://boardof.one/use-cases" />
	<meta property="og:title" content="Use Cases - Board of One" />
	<meta property="og:description" content="How founders use Board of One to get management-level thinking without management-level headcount." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Use Cases - Board of One" />
	<meta name="twitter:description" content="How founders use Board of One to get management-level thinking without management-level headcount." />
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
					When founders use<br />
					<span class="text-brand-600 dark:text-brand-400 italic">Board of One</span>
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
					Real situations where Board of One replaces expensive hires, busy advisors, and solo guesswork.
				</p>
			</div>
		</section>

		<!-- Use Cases Grid -->
		<section class="py-16 md:py-24">
			<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
				<div class="grid md:grid-cols-2 gap-8">
					{#each useCases as useCase}
						<a href="/use-cases/{useCase.slug}" class="group block bg-neutral-50 dark:bg-neutral-800 rounded-2xl p-8 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-all hover:shadow-lg">
							<div class="flex items-start gap-4 mb-4">
								<div class="w-12 h-12 rounded-xl bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
									<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400">
										<path d={iconPaths[useCase.icon]} />
									</svg>
								</div>
								<div>
									<span class="text-xs font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Use Case</span>
									<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
										{useCase.title}
									</h2>
								</div>
							</div>
							<p class="text-neutral-600 dark:text-neutral-400 mb-4">
								{useCase.description}
							</p>
							<p class="text-sm text-neutral-500 dark:text-neutral-500 italic">
								"{useCase.problem}"
							</p>
							<div class="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand-600 dark:text-brand-400 group-hover:gap-2 transition-all">
								Learn more
								<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
							</div>
						</a>
					{/each}
				</div>
			</div>
		</section>

		<!-- CTA -->
		<section class="py-16 md:py-24 bg-gradient-to-r from-brand-600 to-brand-700 dark:from-brand-700 dark:to-brand-800">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-3xl md:text-4xl font-bold text-white mb-4">
					Which situation fits you?
				</h2>
				<p class="text-lg text-brand-100 mb-8">
					Request early access and start getting management-level guidance.
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
