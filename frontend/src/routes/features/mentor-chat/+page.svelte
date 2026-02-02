<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
</script>

<svelte:head>
	<title>Mentor Chat - Board of One</title>
	<meta name="description" content="On-demand 1:1 conversations with AI mentors who know your business context. Brainstorm, explore ideas, and get guidance when you need it." />
	<link rel="canonical" href="https://boardof.one/features/mentor-chat" />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Option Generation</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Mentor Chat
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					On-demand conversations with AI mentors who understand your business. Brainstorm ideas, explore options, and get guidance—without scheduling a call.
				</p>
			</div>
		</section>

		<!-- Why It Matters -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Why mentor access matters for solopreneurs
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Running a business solo means you're often the only person thinking about your problems. You don't have a co-founder to bounce ideas off, and advisors are expensive or unavailable when you need them most—at 11pm before a big decision.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One's mentor chat gives you access to expert perspectives whenever you need them. Choose from different mentor archetypes—strategic, financial, operational—and have exploratory conversations that help you think through challenges before they become urgent decisions.
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
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Choose your mentor</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Select from expert archetypes: strategic advisor, financial analyst, growth marketer, operations expert, and more.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">2</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Context-aware conversation</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Your mentor already knows your business context, metrics, and past decisions—no need to explain from scratch every time.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">3</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Brainstorm and explore</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Talk through ideas, get challenged on assumptions, and explore options in a free-form conversation.</p>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Example Use Cases -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					When to use mentor chat
				</h2>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Early-stage ideation</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">When you're not ready for a full decision session but need to explore a topic. "I'm thinking about launching a second product line—help me think through this."</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Quick sanity checks</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">"Am I missing something obvious here?" Get a fast second opinion before you commit to a direction.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Specialized expertise</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Need financial modeling help? Legal considerations? Pick a mentor with the right expertise for your question.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Processing outcomes</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">After a decision plays out, debrief with a mentor. "This didn't go as planned—help me understand what I missed."</p>
					</div>
				</div>
			</div>
		</section>

		<!-- Mentor vs Deliberation -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Mentor chat vs. full deliberation
				</h2>
				<div class="grid md:grid-cols-2 gap-8">
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-brand-600 dark:text-brand-400 mb-3">Mentor Chat</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>1:1 conversation</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Exploratory, open-ended</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Quick brainstorming</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Single perspective</li>
						</ul>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-brand-600 dark:text-brand-400 mb-3">Full Deliberation</h3>
						<ul class="space-y-2 text-neutral-600 dark:text-neutral-400 text-sm">
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>3-5 expert perspectives</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Structured debate process</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Comprehensive analysis</li>
							<li class="flex items-start gap-2"><span class="text-brand-600">→</span>Clear recommendation</li>
						</ul>
					</div>
				</div>
				<p class="text-neutral-600 dark:text-neutral-400 text-center mt-6">
					Use mentor chat to explore. Use deliberation to decide.
				</p>
			</div>
		</section>

		<!-- Part of the System -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
					Part of a cohesive system
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-2xl mx-auto">
					Mentor conversations draw from your <a href="/features/tailored-to-you" class="text-brand-600 dark:text-brand-400 underline">business context</a> and <a href="/features/data-analysis" class="text-brand-600 dark:text-brand-400 underline">data insights</a>. When you're ready to make a decision, escalate to a full <a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">deliberation session</a>.
				</p>
				<Button variant="brand" size="lg" onclick={() => window.location.href = '/'}>
					Request Early Access
				</Button>
			</div>
		</section>
	</main>

	<Footer />
</div>
