<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
</script>

<svelte:head>
	<title>Data Analysis - Board of One</title>
	<meta name="description" content="Ground your decisions in real metrics. Connect spreadsheets, CSVs, or Google Sheets and let Board of One extract insights automatically." />
	<link rel="canonical" href="https://boardof.one/features/data-analysis" />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Context Aggregation</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Data Analysis
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Ground your decisions in real metrics. Connect your data sources and let Board of One extract insights that inform every deliberation.
				</p>
			</div>
		</section>

		<!-- Why It Matters -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Why data-informed decisions matter for solopreneurs
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						As a solopreneur, you don't have a data team to crunch numbers or an analyst to spot trends. Yet every strategic decision you make—pricing, channels, product direction—should be grounded in what your data actually says.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One's data analysis capability means you can upload a spreadsheet and immediately ask strategic questions about it. The system identifies patterns, anomalies, and trends—then feeds those insights directly into your deliberations.
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
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Connect your data</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Upload CSVs, connect Google Sheets, or paste data directly. Your data stays private and secure.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">2</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Automatic insight extraction</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Board of One analyzes your data to identify trends, anomalies, and patterns you might miss.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">3</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Data-informed deliberation</h3>
							<p class="text-neutral-600 dark:text-neutral-400">When you run a decision session, your data insights are automatically referenced by expert perspectives.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Example Use Cases -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					Example use cases
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Revenue analysis</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Upload your sales data to understand which products drive growth, identify seasonal patterns, and spot declining segments before they become problems.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Customer cohort analysis</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Understand retention by signup date, identify your best customer segments, and make data-backed decisions about who to target.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Marketing spend analysis</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Connect your ad spend data to understand CAC by channel, identify diminishing returns, and optimize budget allocation.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Operational metrics</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Track support ticket trends, delivery times, or any operational KPI—then use insights to inform process decisions.</p>
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
					Data analysis connects directly to your <a href="/features/tailored-to-you" class="text-brand-600 dark:text-brand-400 underline">business context</a>, informs <a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">decision deliberations</a>, and enables meaningful <a href="/features/competitor-analysis" class="text-brand-600 dark:text-brand-400 underline">benchmarking against competitors</a>.
				</p>
				<Button variant="brand" size="lg" onclick={() => window.location.href = '/'}>
					Request Early Access
				</Button>
			</div>
		</section>
	</main>

	<Footer />
</div>
