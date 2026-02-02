<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';
</script>

<svelte:head>
	<title>Project Management - Board of One</title>
	<meta name="description" content="Group related decisions and actions by project. Track initiatives from decision through execution with integrated Kanban boards and progress tracking." />
	<link rel="canonical" href="https://boardof.one/features/project-management" />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Follow-through</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Project Management
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Group related decisions and actions by project or initiative. Track progress from decision through completion.
				</p>
			</div>
		</section>

		<!-- Why It Matters -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Why project organization matters for solopreneurs
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Decisions don't exist in isolation. A product launch involves dozens of decisions—pricing, positioning, timeline, features to include, channels to target. Keeping track of how these decisions relate to each other and what actions they generate is crucial.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One's project management lets you group related decisions and actions together. See the full history of a strategic initiative, track which actions are complete, and understand how one decision led to another.
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
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Create projects</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Organize your work into projects or initiatives. "Q1 Product Launch", "Pricing Overhaul", "New Market Expansion"—whatever makes sense for your business.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">2</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Link decisions and actions</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Every decision and resulting action can be tagged to a project. See all the thinking and work that's gone into an initiative in one place.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">3</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Track progress</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Use the integrated Kanban board to track actions from "To Do" through "Done". See at a glance how your initiatives are progressing.</p>
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
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Project dashboard</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">See all your active initiatives, their progress, and upcoming actions in one view.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Decision history</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">See every decision related to a project, with full context and reasoning.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Kanban boards</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Visual task tracking with drag-and-drop cards. Move actions through your workflow.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Progress tracking</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">See how many actions are complete, in progress, or blocked. Understand where initiatives are stalling.</p>
					</div>
				</div>
			</div>
		</section>

		<!-- Use Cases -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Example projects
				</h2>
				<div class="grid md:grid-cols-3 gap-4">
					<div class="bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Product Launch</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">5 decisions • 12 actions</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Pricing Strategy</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">3 decisions • 8 actions</p>
					</div>
					<div class="bg-white dark:bg-neutral-900 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Q1 Marketing</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">4 decisions • 15 actions</p>
					</div>
				</div>
			</div>
		</section>

		<!-- Part of the System -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">
					Part of a cohesive system
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-6 max-w-2xl mx-auto">
					Projects connect <a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">decisions and replanning</a> with execution. Actions generated from deliberations flow into projects automatically.
				</p>
				<Button variant="brand" size="lg" onclick={() => window.location.href = '/'}>
					Request Early Access
				</Button>
			</div>
		</section>
	</main>

	<Footer />
</div>
