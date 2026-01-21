<script lang="ts">
	/**
	 * Pricing Page - Public page showing tier comparison
	 */
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import PricingTable from '$lib/components/pricing/PricingTable.svelte';
	import MeetingBundles from '$lib/components/pricing/MeetingBundles.svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import { PRICING_FAQ } from '$lib/data/pricing';
	import { ChevronDown } from 'lucide-svelte';

	let expandedFaq = $state<number | null>(null);

	function toggleFaq(index: number) {
		expandedFaq = expandedFaq === index ? null : index;
	}
</script>

<svelte:head>
	<title>Pricing - Board of One</title>
	<meta
		name="description"
		content="Simple, transparent pricing for Board of One. Choose the plan that fits your decision-making needs."
	/>
	<link rel="canonical" href="https://boardof.one/pricing" />
	<meta property="og:type" content="website" />
	<meta property="og:url" content="https://boardof.one/pricing" />
	<meta property="og:title" content="Pricing - Board of One" />
	<meta property="og:description" content="Simple, transparent pricing for Board of One. Choose the plan that fits your decision-making needs." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Pricing - Board of One" />
	<meta name="twitter:description" content="Simple, transparent pricing. Choose the plan that fits your decision-making needs." />
	<meta name="twitter:image" content="https://boardof.one/og-image.png" />
</svelte:head>

<div class="min-h-screen flex flex-col bg-neutral-50 dark:bg-neutral-900">
	<Header showCTA={true} />

	<main class="flex-1">
		<!-- Hero Section -->
		<section class="py-16 sm:py-24 bg-white dark:bg-neutral-900">
			<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h1 class="text-4xl sm:text-5xl font-bold text-neutral-900 dark:text-neutral-100">
					Simple, transparent pricing
				</h1>
				<p class="mt-4 text-lg sm:text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
					Start free and upgrade as you grow. All plans include our core AI-powered deliberation
					features.
				</p>
			</div>
		</section>

		<!-- Pricing Table -->
		<section class="py-12 sm:py-16 bg-neutral-50 dark:bg-neutral-800/50">
			<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
				<PricingTable />
			</div>
		</section>

		<!-- Meeting Bundles -->
		<section class="py-12 sm:py-16 bg-white dark:bg-neutral-900">
			<div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
				<MeetingBundles />
			</div>
		</section>

		<!-- Features Highlight -->
		<section class="py-12 sm:py-16 bg-white dark:bg-neutral-900">
			<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl sm:text-3xl font-bold text-center text-neutral-900 dark:text-neutral-100 mb-8">
					All plans include
				</h2>
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
					<div class="p-6 rounded-lg bg-neutral-50 dark:bg-neutral-800">
						<h3 class="font-semibold text-neutral-900 dark:text-neutral-100">AI-Powered Deliberation</h3>
						<p class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
							Get multiple expert perspectives on any business decision with our multi-agent AI system.
						</p>
					</div>
					<div class="p-6 rounded-lg bg-neutral-50 dark:bg-neutral-800">
						<h3 class="font-semibold text-neutral-900 dark:text-neutral-100">Data Integration</h3>
						<p class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
							Connect your data from CSV files or Google Sheets to inform decisions with real metrics.
						</p>
					</div>
					<div class="p-6 rounded-lg bg-neutral-50 dark:bg-neutral-800">
						<h3 class="font-semibold text-neutral-900 dark:text-neutral-100">Action Tracking</h3>
						<p class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
							Turn decisions into actions with built-in task management and progress tracking.
						</p>
					</div>
					<div class="p-6 rounded-lg bg-neutral-50 dark:bg-neutral-800">
						<h3 class="font-semibold text-neutral-900 dark:text-neutral-100">Business Context</h3>
						<p class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
							Store and evolve your business context so every deliberation builds on previous insights.
						</p>
					</div>
					<div class="p-6 rounded-lg bg-neutral-50 dark:bg-neutral-800">
						<h3 class="font-semibold text-neutral-900 dark:text-neutral-100">Export & Share</h3>
						<p class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
							Export meeting results as JSON or Markdown, and share summaries via secure links.
						</p>
					</div>
					<div class="p-6 rounded-lg bg-neutral-50 dark:bg-neutral-800">
						<h3 class="font-semibold text-neutral-900 dark:text-neutral-100">GDPR Compliant</h3>
						<p class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
							Your data is protected with industry-standard security and full GDPR compliance.
						</p>
					</div>
				</div>
			</div>
		</section>

		<!-- FAQ Section -->
		<section class="py-12 sm:py-16 bg-neutral-50 dark:bg-neutral-800/50">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl sm:text-3xl font-bold text-center text-neutral-900 dark:text-neutral-100 mb-8">
					Frequently asked questions
				</h2>
				<div class="space-y-4">
					{#each PRICING_FAQ as faq, index}
						<BoCard padding="none">
							<button
								class="w-full px-6 py-4 flex items-center justify-between text-left focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 dark:focus:ring-offset-neutral-900 rounded-lg"
								onclick={() => toggleFaq(index)}
								aria-expanded={expandedFaq === index}
							>
								<span class="font-medium text-neutral-900 dark:text-neutral-100 pr-4">
									{faq.question}
								</span>
								<ChevronDown
									class="w-5 h-5 text-neutral-500 shrink-0 transition-transform {expandedFaq === index
										? 'rotate-180'
										: ''}"
								/>
							</button>
							{#if expandedFaq === index}
								<div class="px-6 pb-4 text-neutral-600 dark:text-neutral-400">
									{faq.answer}
								</div>
							{/if}
						</BoCard>
					{/each}
				</div>
			</div>
		</section>

		<!-- CTA Section -->
		<section class="py-16 sm:py-24 bg-brand-600 dark:bg-brand-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-3xl sm:text-4xl font-bold text-white">
					Ready to make better decisions?
				</h2>
				<p class="mt-4 text-lg text-brand-100">
					Start free today. No credit card required.
				</p>
				<div class="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
					<a
						href="/waitlist"
						class="inline-flex items-center justify-center px-6 py-3 text-base font-medium text-brand-600 bg-white rounded-lg shadow hover:bg-brand-50 transition-colors"
					>
						Get Started Free
					</a>
					<a
						href="mailto:hello@boardofone.com"
						class="inline-flex items-center justify-center px-6 py-3 text-base font-medium text-white border border-white/30 rounded-lg hover:bg-white/10 transition-colors"
					>
						Contact Sales
					</a>
				</div>
			</div>
		</section>
	</main>

	<Footer />
</div>
