<script lang="ts">
	// Basic landing page for Board of One
	let title = 'Board of One';
</script>

<main class="max-w-7xl mx-auto px-4 py-16">
	<div class="text-center">
		<h1 class="text-5xl font-bold mb-4 text-gray-900 dark:text-gray-100">
			{title}
		</h1>
		<p class="text-xl text-gray-600 dark:text-gray-400 mb-12">
			AI-Powered Multi-Agent Deliberation System
		</p>
	</div>

	<section class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
		<div class="card">
			<h2 class="text-2xl font-semibold mb-3 text-gray-800 dark:text-gray-200">
				Expert Personas
			</h2>
			<p class="text-gray-600 dark:text-gray-400">
				3-5 expert AI personas debate your problem from different perspectives
			</p>
		</div>

		<div class="card">
			<h2 class="text-2xl font-semibold mb-3 text-gray-800 dark:text-gray-200">
				Structured Synthesis
			</h2>
			<p class="text-gray-600 dark:text-gray-400">
				AI-powered consensus building through multi-round deliberation
			</p>
		</div>

		<div class="card">
			<h2 class="text-2xl font-semibold mb-3 text-gray-800 dark:text-gray-200">
				Real-time Streaming
			</h2>
			<p class="text-gray-600 dark:text-gray-400">
				Watch the deliberation unfold in real-time with SSE streaming
			</p>
		</div>
	</section>

	<div class="text-center">
		<a href="/dashboard" class="btn-primary inline-block text-lg">
			Get Started
		</a>
	</div>
</main>
