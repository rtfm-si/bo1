<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
</script>

<svelte:head>
	<title>Decisions & Replanning - Board of One</title>
	<meta name="description" content="Structured deliberations with multiple expert perspectives. Get comprehensive analysis of your options, clear recommendations, and the ability to revisit decisions when circumstances change." />
	<link rel="canonical" href="https://boardof.one/features/decisions-replanning" />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Core Decision Engine</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Decisions & Replanning
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Structured deliberations with multiple expert perspectives. Get comprehensive analysis, clear recommendations, and revisit decisions when circumstances change.
				</p>
			</div>
		</section>

		<!-- Why It Matters -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Why structured decisions matter for solopreneurs
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						The hardest part of running a business alone isn't doing the work—it's making decisions without a team to pressure-test your thinking. You can't hire a CFO, CMO, and COO to weigh in on every strategic question. Yet these decisions shape everything that follows.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One's deliberation sessions give you what every CEO has: a room full of experts debating your options. Multiple AI personas with different expertise areas analyze your decision, debate the trade-offs, and synthesize their perspectives into a clear recommendation—one you can understand, challenge, and act on.
					</p>
				</div>
			</div>
		</section>

		<!-- How It Works -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					How deliberations work
				</h2>
				<div class="space-y-8">
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">1</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Frame your decision</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Describe the decision you're facing. "Should I raise my prices?" "Which market should I enter first?" "Should I hire a contractor or build it myself?"</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">2</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Experts deliberate</h3>
							<p class="text-neutral-600 dark:text-neutral-400">3-5 expert personas—selected based on your decision type—analyze the problem, debate options across multiple rounds, and challenge each other's assumptions.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">3</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Get a synthesized recommendation</h3>
							<p class="text-neutral-600 dark:text-neutral-400">The system synthesizes all perspectives into a clear recommendation with supporting reasoning, dissenting views, and concrete next actions.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">4</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Act and revisit</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Execute your decision with clear actions. When circumstances change, reopen the deliberation to reassess with new information.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- What You Get -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					What you get
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Multi-perspective analysis</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Expert personas from finance, strategy, operations, and marketing examine your decision from all angles.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Structured debate</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Watch experts challenge each other's assumptions and reasoning across multiple deliberation rounds.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Clear recommendations</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Get a synthesized recommendation with confidence levels, supporting evidence, and dissenting perspectives.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Concrete actions</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Every decision generates specific next steps that flow directly into your project management system.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Decision history</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Every deliberation is recorded. Look back at why you made a decision, what you considered, and what you knew at the time.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Replanning capability</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Circumstances changed? Reopen any past decision, add new context, and get updated recommendations.</p>
					</div>
				</div>
			</div>
		</section>

		<!-- Expert Personas -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Expert personas for every decision type
				</h2>
				<div class="grid md:grid-cols-3 gap-4">
					<div class="bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Strategic Advisor</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Long-term positioning, market strategy, competitive dynamics</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Financial Analyst</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">ROI analysis, cash flow, unit economics, financial risk</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Operations Expert</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Implementation feasibility, resource constraints, execution risk</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Growth Marketer</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Customer acquisition, positioning, messaging, market timing</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Product Thinker</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">User needs, feature prioritization, product-market fit</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Devil's Advocate</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">Challenges assumptions, surfaces blind spots, stress-tests reasoning</p>
					</div>
				</div>
			</div>
		</section>

		<!-- Part of the System -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
					The heart of Board of One
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-2xl mx-auto">
					Deliberations are powered by your <a href="/features/tailored-to-you" class="text-brand-600 dark:text-brand-400 underline">business context</a>, enriched by <a href="/features/data-analysis" class="text-brand-600 dark:text-brand-400 underline">data insights</a> and <a href="/features/competitor-analysis" class="text-brand-600 dark:text-brand-400 underline">competitive intelligence</a>. Decisions generate actions that flow into <a href="/features/project-management" class="text-brand-600 dark:text-brand-400 underline">project management</a>.
				</p>
				<Button variant="brand" size="lg" onclick={() => window.location.href = '/'}>
					Request Early Access
				</Button>
			</div>
		</section>
	</main>

	<Footer />
</div>
