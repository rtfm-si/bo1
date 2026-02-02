<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import {
		createFeaturePageSchema,
		createFeatureBreadcrumbSchema,
		createFeatureFAQSchema,
		serializeJsonLd,
		type FeaturePageConfig
	} from '$lib/utils/jsonld';

	const featureConfig: FeaturePageConfig = {
		slug: 'data-analysis',
		title: 'Data Analysis',
		description: 'Ground your decisions in real metrics. Connect spreadsheets, CSVs, or Google Sheets and let Board of One extract insights automatically.',
		category: 'Context Aggregation',
		datePublished: '2024-01-15',
		dateModified: '2024-12-01'
	};

	const faqs = [
		{
			question: 'What file formats does Board of One support for data analysis?',
			answer: 'Board of One supports CSV files, Excel spreadsheets (.xlsx, .xls), and direct Google Sheets connections. You can upload files directly or connect cloud spreadsheets for automatic syncing. The system handles most common data formats including dates, currencies, and percentages automatically.'
		},
		{
			question: 'Is my business data secure when I upload it?',
			answer: 'Yes, your data security is our priority. All uploads are encrypted in transit and at rest. Your data is isolated to your account and never shared with other users or used to train AI models. You can delete your data at any time, and we follow SOC 2 security practices.'
		},
		{
			question: 'How does data analysis inform my decisions?',
			answer: 'When you run a deliberation session, Board of One automatically references relevant data insights. For example, if you\'re deciding on pricing, the system will surface your current margins, customer acquisition costs, and revenue trends. Expert personas can cite specific metrics to support their recommendations.'
		},
		{
			question: 'Can I connect Google Sheets directly?',
			answer: 'Yes, you can connect Google Sheets for automatic syncing. Once connected, Board of One will pull the latest data whenever you start a deliberation or mentor chat. This ensures your insights are always based on current information without manual re-uploads.'
		},
		{
			question: 'What insights does Board of One extract automatically?',
			answer: 'Board of One identifies trends over time, calculates key business metrics (growth rates, averages, totals), detects anomalies or outliers, finds correlations between variables, and segments your data by relevant categories. The system focuses on actionable insights that can inform strategic decisions.'
		},
		{
			question: 'How often should I update my data?',
			answer: 'For most solopreneurs, weekly or monthly updates work well depending on your business velocity. If you\'re connected to Google Sheets, updates happen automatically. The key is ensuring your data reflects your current reality before making important decisions.'
		},
		{
			question: 'Do I need to be technical to use data analysis?',
			answer: 'No technical skills required. You upload your data and Board of One handles the analysis. You don\'t need to know SQL, Python, or statistics. The system presents insights in plain language and explains what the numbers mean for your business decisions.'
		},
		{
			question: 'How does this integrate with other Board of One features?',
			answer: 'Data analysis is foundational. Your metrics inform deliberation sessions, mentor chats reference your numbers, competitor benchmarking compares your performance, and SEO recommendations consider your current traffic data. Upload once, benefit everywhere.'
		}
	];

	const breadcrumbSchema = createFeatureBreadcrumbSchema(featureConfig);
	const articleSchema = createFeaturePageSchema(featureConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>Data Analysis for Solopreneurs - Board of One</title>
	<meta name="description" content="Ground your decisions in real metrics. Connect spreadsheets, CSVs, or Google Sheets and let Board of One extract insights automatically. No data team required." />
	<link rel="canonical" href="https://boardof.one/features/data-analysis" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/features/data-analysis" />
	<meta property="og:title" content="Data Analysis for Solopreneurs - Board of One" />
	<meta property="og:description" content="Ground your decisions in real metrics. No data team required." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Data Analysis for Solopreneurs - Board of One" />
	<meta name="twitter:description" content="Ground your decisions in real metrics. No data team required." />
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
					Stop making gut decisions. Ground every choice in what your data actually says—without hiring a data analyst or learning SQL.
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The problem: flying blind on metrics
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						As a solopreneur, you're sitting on valuable data. Your revenue numbers, customer acquisition costs, conversion rates, churn metrics—it's all there in spreadsheets. But turning that raw data into actionable insight? That's where most solo founders get stuck.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						You don't have a data team to crunch numbers. You don't have an analyst to spot trends. So when a big decision lands—"Should I raise prices? Which channel is actually working? Where's my growth coming from?"—you end up going with intuition instead of evidence.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Intuition isn't wrong. But it's incomplete. And for high-stakes decisions, incomplete information leads to avoidable mistakes.
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
						Board of One's data analysis capability means you can upload a spreadsheet and immediately ask strategic questions about it. No formulas, no pivot tables, no learning new software. The system identifies patterns, anomalies, and trends—then feeds those insights directly into your deliberations.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						When you're debating whether to raise prices, the expert personas don't just give generic advice. They reference your actual margins, your customer acquisition costs, your revenue trends. Real numbers. Real context. Real recommendations.
					</p>
				</div>
				<div class="space-y-8">
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">1</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Connect your data</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Upload CSVs, Excel files, or connect Google Sheets directly. Your data stays private, encrypted, and isolated to your account.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">2</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Automatic insight extraction</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Board of One analyzes your data to identify trends, calculate key metrics, detect anomalies, and surface patterns you might miss scrolling through rows.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">3</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Data-informed deliberation</h3>
							<p class="text-neutral-600 dark:text-neutral-400">When you run a decision session, your data insights are automatically referenced. Expert perspectives cite specific metrics to support their recommendations.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Why Different -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Why this is different
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none mb-10">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Generic AI tools can analyze data, but they don't know your business. They can't tell you whether a 15% month-over-month growth rate is good for <em>your</em> stage and <em>your</em> market. They don't understand that your Q4 dip is seasonal, not concerning.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One combines your data with your business context. It knows your strategy, your constraints, your competitive landscape. So when it analyzes your numbers, the insights are relevant to your actual situation—not generic observations that require you to translate them to your reality.
					</p>
				</div>
			</div>
		</section>

		<!-- Example Use Cases -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					Example use cases
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Revenue analysis</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Upload your sales data to understand which products drive growth, identify seasonal patterns, and spot declining segments before they become problems. "Your enterprise tier grew 40% last quarter while starter tier declined—should we shift focus?"</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Customer cohort analysis</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Understand retention by signup date, identify your best customer segments, and make data-backed decisions about who to target. "Customers from organic search retain 2x better than paid—worth reallocating budget?"</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Marketing spend analysis</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Connect your ad spend data to understand CAC by channel, identify diminishing returns, and optimize budget allocation. "Your LinkedIn CAC has increased 3x in 6 months—time to test other channels?"</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Operational metrics</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Track support ticket trends, delivery times, or any operational KPI—then use insights to inform process decisions. "Response times have crept up 25%—is it volume growth or efficiency decline?"</p>
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

		<!-- Part of the System -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4 text-center">
					Part of a cohesive system
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-8 max-w-2xl mx-auto text-center">
					Data analysis doesn't exist in isolation. It's deeply integrated with every other Board of One capability.
				</p>
				<div class="grid md:grid-cols-3 gap-6 mb-8">
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Informs Decisions</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Every <a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">deliberation session</a> can reference your uploaded metrics for data-grounded recommendations.</p>
					</div>
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Enables Benchmarking</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm"><a href="/features/competitor-analysis" class="text-brand-600 dark:text-brand-400 underline">Competitor analysis</a> compares your performance against industry standards and peer metrics.</p>
					</div>
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Enriches Context</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Your numbers become part of your <a href="/features/tailored-to-you" class="text-brand-600 dark:text-brand-400 underline">business context</a>, making all features more relevant.</p>
					</div>
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
