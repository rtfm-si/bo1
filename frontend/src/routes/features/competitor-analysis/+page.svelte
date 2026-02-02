<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
</script>

<svelte:head>
	<title>Competitor Analysis & Benchmarking - Board of One</title>
	<meta name="description" content="Understand what competitors are doing and how you compare. Track market movements, identify threats and opportunities, and benchmark your metrics." />
	<link rel="canonical" href="https://boardof.one/features/competitor-analysis" />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Context Aggregation</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Competitor Analysis & Benchmarking
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Understand what competitors are doing and how you compare. Track market movements, identify threats, and benchmark your performance.
				</p>
			</div>
		</section>

		<!-- Why It Matters -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Why competitive intelligence matters for solopreneurs
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						As a solopreneur, you can't afford to be blindsided by competitor moves. You don't have a strategy team monitoring the market—but you still need to know when a competitor launches a new feature, changes their pricing, or pivots their positioning.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One's competitor analysis helps you stay informed without spending hours on research. Track specific competitors, understand their positioning, and benchmark your metrics against industry standards—all integrated into your decision-making process.
					</p>
				</div>
			</div>
		</section>

		<!-- What You Get -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					What you get
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Competitor profiles</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm mb-3">Track specific competitors and understand their positioning, pricing, features, and go-to-market strategy.</p>
						<ul class="space-y-1 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Positioning analysis</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Feature comparison</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Pricing intelligence</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Market movement tracking</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm mb-3">Stay informed about changes in your competitive landscape without constant manual research.</p>
						<ul class="space-y-1 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>New competitor detection</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Feature launches</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Pricing changes</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Threat & opportunity identification</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm mb-3">Understand where you're vulnerable and where you have advantages.</p>
						<ul class="space-y-1 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Competitive threats</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Market gaps</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Differentiation opportunities</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Metric benchmarking</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm mb-3">Compare your performance against industry standards and peer companies.</p>
						<ul class="space-y-1 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Industry benchmarks</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Peer comparison</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">+</span>Performance gaps</li>
						</ul>
					</div>
				</div>
			</div>
		</section>

		<!-- How It's Used -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					How competitive intelligence informs decisions
				</h2>
				<div class="space-y-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Pricing decisions</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">"Should I raise my prices?" becomes an informed discussion when you know what competitors charge, how your features compare, and what the market will bear.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Feature prioritization</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">"What should I build next?" gets clearer when you understand what competitors offer, what's table stakes vs. differentiation, and where gaps exist.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Positioning refinement</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">"How should I position my product?" requires understanding how competitors position themselves and where there's room for differentiation.</p>
					</div>
				</div>
			</div>
		</section>

		<!-- Part of the System -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
					Part of a cohesive system
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-2xl mx-auto">
					Competitor intelligence is filtered through your <a href="/features/tailored-to-you" class="text-brand-600 dark:text-brand-400 underline">business context</a>, enriches <a href="/features/data-analysis" class="text-brand-600 dark:text-brand-400 underline">data analysis</a> with benchmarks, and informs <a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">strategic decisions</a>.
				</p>
				<Button variant="brand" size="lg" onclick={() => window.location.href = '/'}>
					Request Early Access
				</Button>
			</div>
		</section>
	</main>

	<Footer />
</div>
