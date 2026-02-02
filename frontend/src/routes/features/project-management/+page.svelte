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
		slug: 'project-management',
		title: 'Project Management',
		description: 'Group related decisions and actions by project. Track initiatives from decision through execution with integrated Kanban boards and progress tracking.',
		category: 'Follow-through',
		datePublished: '2024-01-15',
		dateModified: '2024-12-01'
	};

	const faqs = [
		{
			question: 'How do projects connect to decisions?',
			answer: 'Every decision you make in Board of One can be tagged to a project. When a deliberation generates action items, those actions automatically appear in the project\'s Kanban board. This creates a direct link from strategic thinking to execution—you can trace any action back to the decision that created it.'
		},
		{
			question: 'Can I have multiple projects running at once?',
			answer: 'Yes. Most solopreneurs have several initiatives running simultaneously—a product launch, a marketing push, a process improvement. Board of One lets you organize by project and switch between them easily. Each project has its own decision history, action list, and progress tracking.'
		},
		{
			question: 'How does the Kanban board work?',
			answer: 'The Kanban board shows all actions for a project organized by status: To Do, In Progress, and Done. Drag cards between columns as work progresses. See at a glance what\'s pending, what\'s active, and what\'s complete. It\'s simple by design—powerful enough to track work, simple enough not to become work itself.'
		},
		{
			question: 'What triggers a replanning session?',
			answer: 'You can trigger replanning manually when circumstances change, or Board of One can suggest it based on signals: an action has been stuck too long, new data contradicts original assumptions, or a related decision has changed. Replanning lets you revisit decisions with new information rather than continuing on an outdated path.'
		},
		{
			question: 'Can I export project history?',
			answer: 'Yes. You can export a project\'s complete history—all decisions, their reasoning, actions taken, and outcomes—to PDF or Markdown. This is useful for stakeholder updates, board reports, or simply having a record of how an initiative evolved from idea to completion.'
		},
		{
			question: 'How do I know when a project is complete?',
			answer: 'A project is complete when all actions are done and you\'ve achieved the intended outcome. Board of One tracks completion rate and can prompt you to close projects that appear finished. You can also archive projects to keep history without cluttering your active workspace.'
		},
		{
			question: 'What if a project needs to change direction?',
			answer: 'That\'s what replanning is for. When new information suggests your current approach isn\'t working, reopen the original decision (or start a new deliberation) with updated context. The expert panel will reassess and may recommend different actions. The project history preserves the old plan so you can understand the evolution.'
		},
		{
			question: 'How is this different from standalone project management tools?',
			answer: 'Most project management tools start with tasks. Board of One starts with decisions. You\'re not just tracking what needs to be done—you\'re tracking why you decided to do it. This decision history becomes invaluable when things don\'t go as planned or when you need to explain your approach to others.'
		}
	];

	const breadcrumbSchema = createFeatureBreadcrumbSchema(featureConfig);
	const articleSchema = createFeaturePageSchema(featureConfig);
	const faqSchema = createFeatureFAQSchema(faqs);
</script>

<svelte:head>
	<title>Project Management for Solopreneurs - Board of One</title>
	<meta name="description" content="Decisions don't exist in isolation. Track initiatives end-to-end from decision through execution with integrated Kanban boards and progress tracking." />
	<link rel="canonical" href="https://boardof.one/features/project-management" />
	<meta property="og:type" content="article" />
	<meta property="og:url" content="https://boardof.one/features/project-management" />
	<meta property="og:title" content="Project Management for Solopreneurs - Board of One" />
	<meta property="og:description" content="Decisions don't exist in isolation. Track initiatives from decision to completion." />
	<meta property="og:image" content="https://boardof.one/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content="Project Management for Solopreneurs - Board of One" />
	<meta name="twitter:description" content="Decisions don't exist in isolation. Track initiatives from decision to completion." />
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
						<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-brand-600 dark:text-brand-400"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
					</div>
					<span class="text-sm font-medium text-brand-600 dark:text-brand-400 uppercase tracking-wide">Follow-through</span>
				</div>
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Project Management
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl">
					Decisions don't exist in isolation. Track initiatives from decision through execution with integrated Kanban boards, progress tracking, and decision history.
				</p>
			</div>
		</section>

		<!-- The Problem -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					The problem: decisions without follow-through
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Making a decision is only half the battle. A product launch involves dozens of decisions—pricing, positioning, timeline, features to include, channels to target. Each decision generates actions. Keeping track of how these decisions relate to each other and what actions they created is crucial.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Most decision-making tools stop at the recommendation. Most project management tools start with tasks, disconnected from the strategic thinking that created them. You end up with decisions in one place, tasks in another, and no clear connection between "why we decided this" and "what we're doing about it."
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Six months later, you look at a stalled task and can't remember why you thought it was important. The strategic context is lost.
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
						Board of One's project management lets you group related decisions and actions together. See the full history of a strategic initiative, track which actions are complete, and understand how one decision led to another.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						When you make a decision, the resulting actions flow directly into your project. When an action stalls, you can trace it back to the decision that created it. When circumstances change, you can replan with full context of what you were trying to achieve and why.
					</p>
				</div>
				<div class="space-y-8">
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">1</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Create projects</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Organize your work into projects or initiatives. "Q1 Product Launch," "Pricing Strategy Overhaul," "New Market Expansion"—whatever makes sense for your business.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">2</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Link decisions and actions</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Every decision and resulting action can be tagged to a project. See all the thinking and work that's gone into an initiative in one place. Trace any task back to the decision that created it.</p>
						</div>
					</div>
					<div class="flex gap-6">
						<div class="flex-shrink-0 w-10 h-10 rounded-full bg-brand-600 dark:bg-brand-500 text-white flex items-center justify-center font-bold">3</div>
						<div>
							<h3 class="text-lg font-bold text-neutral-900 dark:text-neutral-100 mb-2">Track progress</h3>
							<p class="text-neutral-600 dark:text-neutral-400">Use the integrated Kanban board to track actions from "To Do" through "Done." See at a glance how your initiatives are progressing and where things are stuck.</p>
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
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">See all your active initiatives, their progress, and upcoming actions in one view. Know what needs attention without checking multiple places.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Decision history</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">See every decision related to a project, with full context and reasoning. Understand the "why" behind every "what" in your task list.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Kanban boards</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Visual task tracking with drag-and-drop cards. Move actions through your workflow. Simple enough not to become work itself.</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">Progress tracking</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">See how many actions are complete, in progress, or blocked. Understand where initiatives are stalling and need attention.</p>
					</div>
				</div>
			</div>
		</section>

		<!-- Why Different -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Why this is different
				</h2>
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed">
						Most project management tools are about tasks. You create to-do items, organize them, check them off. But where did those tasks come from? Why are you doing them? What happens if circumstances change?
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						Board of One starts with decisions, not tasks. Every action exists because of a strategic choice you made, and that decision—with all its reasoning and context—is preserved. This changes everything about how you work.
					</p>
					<p class="text-lg text-neutral-600 dark:text-neutral-400 leading-relaxed mt-4">
						When a task stalls, you can revisit the decision that created it. When you need to explain your approach to a stakeholder, the reasoning is there. When circumstances change, you know exactly which decisions to reconsider. This is project management with strategic memory.
					</p>
				</div>
			</div>
		</section>

		<!-- Example Projects -->
		<section class="py-16 md:py-20">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Example projects
				</h2>
				<div class="grid md:grid-cols-3 gap-4">
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Product Launch</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">5 decisions • 12 actions • 75% complete</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Pricing Strategy</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">3 decisions • 8 actions • 50% complete</p>
					</div>
					<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
						<h3 class="font-medium text-neutral-900 dark:text-neutral-100 text-sm mb-1">Q1 Marketing</h3>
						<p class="text-neutral-500 dark:text-neutral-400 text-xs">4 decisions • 15 actions • 30% complete</p>
					</div>
				</div>
			</div>
		</section>

		<!-- FAQ Section -->
		<section class="py-16 md:py-20 bg-neutral-50 dark:bg-neutral-800">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-10">
					Frequently asked questions
				</h2>
				<div class="space-y-6">
					{#each faqs as faq}
						<div class="bg-white dark:bg-neutral-900 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-3">{faq.question}</h3>
							<p class="text-neutral-600 dark:text-neutral-400">{faq.answer}</p>
						</div>
					{/each}
				</div>
			</div>
		</section>

		<!-- Part of the System -->
		<section class="py-16 md:py-20 border-t border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4 text-center">
					Part of a cohesive system
				</h2>
				<p class="text-neutral-600 dark:text-neutral-400 mb-8 max-w-2xl mx-auto text-center">
					Project management connects the thinking to the doing.
				</p>
				<div class="grid md:grid-cols-3 gap-6 mb-8">
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">From Decisions</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm"><a href="/features/decisions-replanning" class="text-brand-600 dark:text-brand-400 underline">Deliberation sessions</a> generate actions that flow directly into project boards.</p>
					</div>
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">With Context</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Your <a href="/features/tailored-to-you" class="text-brand-600 dark:text-brand-400 underline">business context</a> and <a href="/features/data-analysis" class="text-brand-600 dark:text-brand-400 underline">data</a> inform replanning decisions.</p>
					</div>
					<div class="text-center">
						<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-2">To Completion</h3>
						<p class="text-neutral-600 dark:text-neutral-400 text-sm">Track progress and trigger replanning when circumstances change.</p>
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
