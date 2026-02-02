<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
</script>

<svelte:head>
	<title>Tailored to YOUR Business - Board of One</title>
	<meta name="description" content="Your business context informs every decision. Store your strategy, metrics, and constraints once—and watch every deliberation become more relevant." />
	<link rel="canonical" href="https://boardof.one/features/tailored-to-you" />
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
					Store your business context once. Watch every decision session become more relevant, every mentor conversation more informed.
				</p>
			</div>
		</section>

		<!-- Why It Matters -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Why context matters for solopreneurs
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Generic advice is useless. "You should raise prices" means nothing without knowing your market, your margins, and your customers' price sensitivity. Every piece of guidance you get should be filtered through the reality of <em>your</em> business.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One lets you capture your business context—your model, your metrics, your constraints, your strategic priorities—and automatically references it in every interaction. No more explaining your situation from scratch. No more getting advice that doesn't fit your reality.
					</p>
				</div>
			</div>
		</section>

		<!-- What You Store -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					What context you can store
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Business fundamentals</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Business model and revenue streams</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Target market and ideal customer</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Key products or services</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Competitive positioning</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Metrics and constraints</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Current revenue and growth rate</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Key financial metrics (margins, CAC, LTV)</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Resource constraints (time, budget, team)</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Timeline and runway</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">Strategic priorities</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Current focus areas and goals</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>What success looks like</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>What you're explicitly NOT doing</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Key risks and concerns</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">History and learnings</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Past decisions and outcomes</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>What's worked and what hasn't</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Lessons learned</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Evolving understanding of your market</li>
						</ul>
					</div>
				</div>
			</div>
		</section>

		<!-- How It's Used -->
		<section class="py-16 md:py-20">
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
							<p class="text-neutral-600 dark:text-neutral-400">Expert perspectives reference your context automatically. A pricing decision considers your margins. A hiring decision considers your runway.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
						</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Mentor conversations</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Mentors already know your business. You can dive straight into the problem without explaining your whole situation first.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
						</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Analysis and insights</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Competitor analysis and benchmarking is filtered through your specific positioning. SEO recommendations target keywords relevant to your market.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Context Evolves -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
					Your context evolves with your business
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6">
					Update your context as your business grows. Add new metrics as they become relevant. Remove constraints you've overcome. Your business isn't static—neither is Board of One's understanding of it.
				</p>
				<p class="text-neutral-700 dark:text-neutral-300 font-medium">
					The more context you provide, the better your recommendations become.
				</p>
			</div>
		</section>

		<!-- Part of the System -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
					The foundation of everything else
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-2xl mx-auto">
					Your business context powers <a href="/features/data-analysis" class="text-brand-600 dark:text-brand-400 underline">data analysis</a>, <a href="/features/mentor-chat" class="text-brand-600 dark:text-brand-400 underline">mentor chat</a>, <a href="/features/seo-generation" class="text-brand-600 dark:text-brand-400 underline">SEO generation</a>, and every <a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">decision session</a> you run.
				</p>
				<Button variant="brand" size="lg" onclick={() => window.location.href = '/'}>
					Request Early Access
				</Button>
			</div>
		</section>
	</main>

	<Footer />
</div>
