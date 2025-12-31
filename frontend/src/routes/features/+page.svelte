<script lang="ts">
	/**
	 * Features Page - Full capability breakdown
	 * Organized by the 6 management functions
	 */
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Capability {
		name: string;
		description: string;
		details: string[];
	}

	interface ManagementFunction {
		number: number;
		title: string;
		question: string;
		description: string;
		capabilities: Capability[];
	}

	const managementFunctions: ManagementFunction[] = [
		{
			number: 1,
			title: 'Context Aggregation',
			question: "What's going on?",
			description: 'Gather and synthesize the information you need to make informed decisions.',
			capabilities: [
				{
					name: 'Data Analysis',
					description: 'Connect spreadsheets, CSVs, or Google Sheets to ground decisions in real metrics.',
					details: [
						'Upload or connect data sources',
						'Automatic insight extraction',
						'Trend identification and anomaly detection',
						'Data-informed deliberation'
					]
				},
				{
					name: 'Competition Intelligence',
					description: 'Understand what competitors are doing and how the market is shifting.',
					details: [
						'Competitor positioning analysis',
						'Market movement tracking',
						'Competitive threat assessment',
						'Opportunity identification'
					]
				},
				{
					name: 'Business Context',
					description: 'Your evolving business context informs every decision.',
					details: [
						'Store strategic context once',
						'Automatically referenced in deliberations',
						'Evolves as your business grows',
						'No repeated explanations'
					]
				}
			]
		},
		{
			number: 2,
			title: 'Option Generation',
			question: 'What could we do?',
			description: 'Surface options and approaches you might not have considered.',
			capabilities: [
				{
					name: 'Mentor 1:1s',
					description: 'On-demand conversations with AI mentors who know your business context.',
					details: [
						'Choose from expert archetypes',
						'Context-aware guidance',
						'Exploratory conversations',
						'Brainstorming and ideation'
					]
				},
				{
					name: 'Structured Deliberation',
					description: 'Multi-perspective analysis that surfaces options systematically.',
					details: [
						'3-5 expert perspectives per decision',
						'Different viewpoints and biases',
						'Comprehensive option mapping',
						'Creative problem-solving'
					]
				}
			]
		},
		{
			number: 3,
			title: 'Risk & Downside Pressure',
			question: 'What could break?',
			description: 'Challenge assumptions and surface risks before they become problems.',
			capabilities: [
				{
					name: 'Expert Challenge Rounds',
					description: 'Each perspective actively challenges the others, surfacing blind spots.',
					details: [
						'Adversarial questioning',
						'Assumption testing',
						'Edge case identification',
						'Downside scenario planning'
					]
				},
				{
					name: 'Risk Assessment',
					description: 'Systematic identification of what could go wrong.',
					details: [
						'Probability and impact analysis',
						'Mitigation strategies',
						'Contingency planning',
						'Risk-adjusted recommendations'
					]
				}
			]
		},
		{
			number: 4,
			title: 'Alignment & Trade-offs',
			question: 'What do we prioritise?',
			description: 'Navigate competing priorities and make clear trade-off decisions.',
			capabilities: [
				{
					name: 'Multi-Perspective Synthesis',
					description: 'Converge multiple viewpoints into a coherent recommendation.',
					details: [
						'Weighted perspective integration',
						'Trade-off documentation',
						'Priority alignment',
						'Clear decision rationale'
					]
				},
				{
					name: 'Strategic Alignment',
					description: 'Ensure decisions align with your broader goals and constraints.',
					details: [
						'Goal alignment checking',
						'Resource constraint awareness',
						'Timeline considerations',
						'Stakeholder impact analysis'
					]
				}
			]
		},
		{
			number: 5,
			title: 'Decision Documentation',
			question: 'Why did we choose this?',
			description: 'Capture reasoning so decisions can be defended, reviewed, and learned from.',
			capabilities: [
				{
					name: 'Decision Logs',
					description: 'Every decision is captured with full reasoning and context.',
					details: [
						'Complete deliberation history',
						'Reasoning documentation',
						'Searchable decision archive',
						'Audit trail for stakeholders'
					]
				},
				{
					name: 'Shareable Summaries',
					description: 'Generate summaries to share with teams, boards, or advisors.',
					details: [
						'One-click summary generation',
						'Secure sharing links',
						'Export to PDF or Markdown',
						'Stakeholder-ready formats'
					]
				}
			]
		},
		{
			number: 6,
			title: 'Follow-through',
			question: 'Course correction',
			description: 'Turn decisions into actions and adapt when reality changes.',
			capabilities: [
				{
					name: 'Actions & Kanban',
					description: 'Every decision generates actionable next steps, tracked to completion.',
					details: [
						'Auto-generated action items',
						'Kanban board tracking',
						'Progress visibility',
						'Completion tracking'
					]
				},
				{
					name: 'Replanning',
					description: 'When circumstances change, revisit and adapt your decisions.',
					details: [
						'Triggered replanning sessions',
						'Context change detection',
						'Decision revision workflow',
						'Learning from outcomes'
					]
				},
				{
					name: 'Outcome Tracking',
					description: 'Feed results back into future decisions for continuous improvement.',
					details: [
						'Outcome logging',
						'Decision effectiveness metrics',
						'Pattern recognition',
						'Improved future recommendations'
					]
				}
			]
		}
	];

	// Additional standalone capabilities
	const additionalCapabilities = [
		{
			name: 'SEO & Marketing Analysis',
			description: 'Understand your search visibility and marketing positioning.',
			category: 'Growth'
		},
		{
			name: 'Benchmark Comparisons',
			description: 'See how your metrics compare to industry standards.',
			category: 'Context'
		},
		{
			name: 'Project Organization',
			description: 'Group related decisions and actions by project or initiative.',
			category: 'Organization'
		}
	];
</script>

<svelte:head>
	<title>Features - Board of One</title>
	<meta
		name="description"
		content="Explore the full capabilities of Board of One. A management operating system organized around the 6 core functions of management."
	/>
</svelte:head>

<div class="min-h-screen flex flex-col bg-white dark:bg-neutral-900">
	<Header />

	<main class="flex-1">
		<!-- Hero -->
		<section class="py-16 md:py-24 bg-gradient-to-b from-brand-50 to-white dark:from-neutral-800 dark:to-neutral-900">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h1 class="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					A complete management<br />
					<span class="text-brand-600 dark:text-brand-400 italic">operating system</span>
				</h1>
				<p class="text-xl text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
					Every capability maps to one of the six functions that management actually performs.
					No feature bloat. No complexity for its own sake.
				</p>
			</div>
		</section>

		<!-- Management Functions -->
		<section class="py-16 md:py-24">
			<div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
				<div class="space-y-24">
					{#each managementFunctions as func}
						<div class="relative">
							<!-- Function Header -->
							<div class="flex items-start gap-6 mb-8">
								<div class="flex-shrink-0 w-16 h-16 rounded-2xl bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
									<span class="text-2xl font-bold text-brand-600 dark:text-brand-400">{func.number}</span>
								</div>
								<div>
									<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100">
										{func.title}
									</h2>
									<p class="text-lg text-brand-600 dark:text-brand-400 italic mt-1">
										{func.question}
									</p>
									<p class="text-neutral-600 dark:text-neutral-400 mt-2 max-w-2xl">
										{func.description}
									</p>
								</div>
							</div>

							<!-- Capabilities Grid -->
							<div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6 pl-0 md:pl-22">
								{#each func.capabilities as capability}
									<div class="bg-neutral-50 dark:bg-neutral-800 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-600 transition-colors">
										<h3 class="font-bold text-lg text-neutral-900 dark:text-neutral-100 mb-2">
											{capability.name}
										</h3>
										<p class="text-neutral-600 dark:text-neutral-400 text-sm mb-4">
											{capability.description}
										</p>
										<ul class="space-y-2">
											{#each capability.details as detail}
												<li class="flex items-start gap-2 text-sm text-neutral-700 dark:text-neutral-300">
													<span class="text-brand-600 dark:text-brand-400 mt-0.5">+</span>
													<span>{detail}</span>
												</li>
											{/each}
										</ul>
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			</div>
		</section>

		<!-- Additional Capabilities -->
		<section class="py-16 bg-neutral-50 dark:bg-neutral-800 border-y border-neutral-200 dark:border-neutral-700">
			<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
				<h2 class="text-2xl font-bold text-neutral-900 dark:text-neutral-100 text-center mb-8">
					Plus more capabilities
				</h2>
				<div class="grid md:grid-cols-3 gap-6">
					{#each additionalCapabilities as cap}
						<div class="text-center">
							<span class="inline-block px-3 py-1 text-xs font-medium text-brand-600 dark:text-brand-400 bg-brand-100 dark:bg-brand-900/30 rounded-full mb-3">
								{cap.category}
							</span>
							<h3 class="font-bold text-neutral-900 dark:text-neutral-100 mb-1">
								{cap.name}
							</h3>
							<p class="text-sm text-neutral-600 dark:text-neutral-400">
								{cap.description}
							</p>
						</div>
					{/each}
				</div>
			</div>
		</section>

		<!-- Philosophy -->
		<section class="py-16 md:py-24">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-2xl md:text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-6">
					Why we built it this way
				</h2>
				<div class="space-y-4 text-neutral-600 dark:text-neutral-400 text-lg leading-relaxed">
					<p>
						Most tools add features to check boxes. We built features to serve the six functions that management actually performs.
					</p>
					<p>
						Every capability earns its place by helping you aggregate context, generate options, pressure-test risks, align trade-offs, document decisions, or follow through.
					</p>
					<p class="text-neutral-900 dark:text-neutral-100 font-medium">
						If it doesn't serve one of those functions, it doesn't belong in Board of One.
					</p>
				</div>
			</div>
		</section>

		<!-- CTA -->
		<section class="py-16 md:py-24 bg-gradient-to-r from-brand-600 to-brand-700 dark:from-brand-700 dark:to-brand-800">
			<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
				<h2 class="text-3xl md:text-4xl font-bold text-white mb-4">
					Ready to see it in action?
				</h2>
				<p class="text-lg text-brand-100 mb-8">
					Request early access and start making management-grade decisions.
				</p>
				<Button
					variant="secondary"
					size="lg"
					onclick={() => window.location.href = '/'}
					class="transform hover:scale-105 transition-transform duration-300"
				>
					Request Early Access
				</Button>
			</div>
		</section>
	</main>

	<Footer />
</div>

<style>
	/* Offset for the capability grid to align with function text */
	@media (min-width: 768px) {
		.pl-22 {
			padding-left: 5.5rem;
		}
	}
</style>
