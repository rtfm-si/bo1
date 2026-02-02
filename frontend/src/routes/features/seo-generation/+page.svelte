<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
</script>

<svelte:head>
	<title>SEO Generation - Board of One</title>
	<meta name="description" content="Understand your search visibility and marketing positioning. Generate SEO-optimized content that attracts the right customers to your business." />
	<link rel="canonical" href="https://boardof.one/features/seo-generation" />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Growth</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					SEO Generation
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Understand your search visibility and generate content that attracts the right customers—without hiring an SEO specialist.
				</p>
			</div>
		</section>

		<!-- Why It Matters -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Why SEO matters for solopreneurs
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						For solopreneurs, organic search is often the most cost-effective customer acquisition channel. But SEO is complex—keyword research, content optimization, technical audits—and you don't have time to become an expert.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One's SEO generation capability analyzes your business positioning and helps you create content that ranks. We identify keyword opportunities, generate optimized content briefs, and help you understand where you stand in search results—all informed by your specific business context.
					</p>
				</div>
			</div>
		</section>

		<!-- How It Works -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					How it works
				</h2>
				<div class="space-y-8">
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">1</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Analyze your positioning</h3>
							<p class="text-neutral-600 dark:text-neutral-400">We understand your business, target market, and competitors to identify relevant keyword opportunities.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">2</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Generate content briefs</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Get detailed outlines for blog posts, landing pages, and other content—optimized for the keywords that matter to your business.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">3</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Track and improve</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Monitor your search visibility over time and get recommendations for improving underperforming content.</p>
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
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Keyword opportunities</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Discover keywords your ideal customers are searching for—matched to your business positioning and competitive landscape.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Content briefs</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Detailed outlines for articles and pages, including headings, talking points, and SEO best practices.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Meta content</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Title tags, meta descriptions, and social previews optimized for click-through rates.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Blog topic suggestions</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">A pipeline of content ideas that align with your expertise and what your audience is searching for.</p>
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
					SEO generation is informed by your <a href="/features/tailored-to-you" class="text-brand-600 dark:text-brand-400 underline">business context</a> and <a href="/features/competitor-analysis" class="text-brand-600 dark:text-brand-400 underline">competitor analysis</a>. Use <a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">deliberation sessions</a> to decide on content strategy priorities.
				</p>
				<Button variant="brand" size="lg" onclick={() => window.location.href = '/'}>
					Request Early Access
				</Button>
			</div>
		</section>
	</main>

	<Footer />
</div>
