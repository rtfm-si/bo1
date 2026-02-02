<script lang="ts">
	/**
	 * HeroCarousel - Product demo carousel for landing page
	 * Shows: Problem input → Expert discussion → Report output
	 * Uses CSS transforms for smooth transitions (no juddery fly animations)
	 */
	import { onMount, onDestroy } from 'svelte';
	import { MessageSquare, FileText, Users, Lightbulb, AlertTriangle, ArrowRight, Quote } from 'lucide-svelte';

	// Carousel state
	let currentSlide = $state(0);
	let autoPlayInterval: ReturnType<typeof setInterval> | null = null;
	let typedText = $state('');
	let isTypingComplete = $state(false);

	const SLIDE_COUNT = 3;
	const AUTO_ADVANCE_MS = 7000;

	// Sample content
	const problemStatement = "Should we raise a Series A now or wait 6 months for better metrics?";

	// Expert contributions aligned with PersonaContribution styling
	const expertContributions = [
		{
			name: "Maria Santos",
			archetype: "Financial Strategist",
			initials: "MS",
			borderColor: "border-l-slate-400 dark:border-l-slate-500", // analytical style
			avatarColor: "bg-emerald-100 text-emerald-700 border-emerald-300 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-700",
			content: "Current market conditions favor companies with 18+ months runway. Your burn rate suggests urgency, but dilution at current metrics could be costly long-term."
		},
		{
			name: "Ahmad Hassan",
			archetype: "Risk Officer",
			initials: "AH",
			borderColor: "border-l-slate-400 dark:border-l-slate-500", // analytical style
			avatarColor: "bg-red-100 text-red-700 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700",
			content: "Waiting carries execution risk if market conditions deteriorate. Consider a bridge round to extend runway while improving key metrics."
		}
	];

	// PDF report sections matching actual output structure
	const reportMetrics = [
		{ value: "5", label: "Experts" },
		{ value: "3", label: "Rounds" },
		{ value: "12", label: "Insights" },
		{ value: "8m", label: "Analysis" }
	];

	const reportOutput = {
		bottomLine: "Pursue bridge financing ($500K-1M) to extend runway to 18 months while improving MRR growth to 15%+ MoM before revisiting Series A.",
		takeaways: [
			"Current runway creates negotiation pressure",
			"Bridge extends optionality without major dilution",
			"15%+ MoM growth unlocks better Series A terms"
		],
		blindSpots: "Team may be underestimating competitive timing risk",
		nextSteps: [
			"Schedule 3-5 bridge investor calls",
			"Set 90-day MRR acceleration targets",
			"Revisit Series A timeline in Q2"
		]
	};

	// Typewriter effect
	function startTyping() {
		typedText = '';
		isTypingComplete = false;
		let i = 0;
		const typeInterval = setInterval(() => {
			if (i < problemStatement.length) {
				typedText += problemStatement[i];
				i++;
			} else {
				clearInterval(typeInterval);
				isTypingComplete = true;
			}
		}, 40);
	}

	// Navigation
	function goToSlide(index: number) {
		currentSlide = index;
		resetAutoPlay();
		if (index === 0) {
			startTyping();
		}
	}

	function nextSlide() {
		goToSlide((currentSlide + 1) % SLIDE_COUNT);
	}

	function prevSlide() {
		goToSlide((currentSlide - 1 + SLIDE_COUNT) % SLIDE_COUNT);
	}

	function resetAutoPlay() {
		if (autoPlayInterval) {
			clearInterval(autoPlayInterval);
		}
		autoPlayInterval = setInterval(nextSlide, AUTO_ADVANCE_MS);
	}

	onMount(() => {
		startTyping();
		autoPlayInterval = setInterval(nextSlide, AUTO_ADVANCE_MS);
	});

	onDestroy(() => {
		if (autoPlayInterval) {
			clearInterval(autoPlayInterval);
		}
	});
</script>

<div class="relative w-full max-w-2xl mx-auto">
	<!-- Carousel Container -->
	<div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
		<!-- Slides wrapper with CSS transform transitions -->
		<div class="relative min-h-[340px]">
			<!-- Slide 1: Problem Statement Input -->
			<div
				class="absolute inset-0 p-6 transition-all duration-500 ease-out {currentSlide === 0
					? 'opacity-100 translate-x-0'
					: currentSlide > 0
						? 'opacity-0 -translate-x-8 pointer-events-none'
						: 'opacity-0 translate-x-8 pointer-events-none'}"
			>
				<div class="flex items-center gap-2 mb-4">
					<div class="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
						<MessageSquare size={16} class="text-brand-600 dark:text-brand-400" />
					</div>
					<span class="text-sm font-medium text-slate-600 dark:text-slate-400">Your Decision</span>
				</div>

				<div class="bg-slate-50 dark:bg-slate-900 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
					<p class="text-lg text-slate-900 dark:text-white font-medium min-h-[3.5rem] leading-relaxed">
						{typedText}<span class="inline-block w-0.5 h-5 bg-brand-500 ml-0.5 {isTypingComplete ? 'animate-pulse' : 'animate-blink'}"></span>
					</p>
				</div>

				<div class="mt-6 flex items-center gap-3">
					<div class="flex-1 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
						<div class="h-full bg-brand-500 rounded-full animate-progress"></div>
					</div>
					<span class="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">Analyzing...</span>
				</div>

				<p class="mt-4 text-sm text-slate-500 dark:text-slate-400 text-center">
					Assembling expert panel for your decision...
				</p>
			</div>

			<!-- Slide 2: Expert Discussion -->
			<div
				class="absolute inset-0 p-6 transition-all duration-500 ease-out {currentSlide === 1
					? 'opacity-100 translate-x-0'
					: currentSlide > 1
						? 'opacity-0 -translate-x-8 pointer-events-none'
						: 'opacity-0 translate-x-8 pointer-events-none'}"
			>
				<div class="flex items-center gap-2 mb-4">
					<div class="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
						<Users size={16} class="text-blue-600 dark:text-blue-400" />
					</div>
					<span class="text-sm font-medium text-slate-600 dark:text-slate-400">Experts Deliberate</span>
				</div>

				<div class="space-y-3">
					{#each expertContributions as expert (expert.name)}
						<div class="border-l-4 {expert.borderColor} pl-3 py-2 bg-slate-50 dark:bg-slate-900 rounded-r-lg">
							<div class="flex items-start gap-3">
								<div class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm border-2 {expert.avatarColor}">
									{expert.initials}
								</div>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="font-semibold text-sm text-neutral-900 dark:text-neutral-100">{expert.name}</span>
										<span class="text-xs text-neutral-600 dark:text-neutral-400">— {expert.archetype}</span>
									</div>
									<p class="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
										{expert.content}
									</p>
								</div>
							</div>
						</div>
					{/each}
				</div>

				<p class="mt-4 text-xs text-slate-500 dark:text-slate-400 text-center italic">
					+ 3 more experts contributing perspectives...
				</p>
			</div>

			<!-- Slide 3: Report Output -->
			<div
				class="absolute inset-0 p-5 transition-all duration-500 ease-out {currentSlide === 2
					? 'opacity-100 translate-x-0'
					: currentSlide < 2
						? 'opacity-0 translate-x-8 pointer-events-none'
						: 'opacity-0 -translate-x-8 pointer-events-none'}"
			>
				<div class="flex items-center gap-2 mb-3">
					<div class="w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
						<FileText size={16} class="text-purple-600 dark:text-purple-400" />
					</div>
					<span class="text-sm font-medium text-slate-600 dark:text-slate-400">Your Report</span>
				</div>

				<!-- Metrics grid -->
				<div class="grid grid-cols-4 gap-1.5 mb-3">
					{#each reportMetrics as metric (metric.label)}
						<div class="text-center p-1.5 bg-slate-50 dark:bg-slate-900 rounded-lg">
							<div class="text-base font-bold text-slate-900 dark:text-white">{metric.value}</div>
							<div class="text-[10px] text-slate-500 dark:text-slate-400">{metric.label}</div>
						</div>
					{/each}
				</div>

				<!-- The Bottom Line - prominent quote style -->
				<div class="bg-brand-50 dark:bg-brand-900/20 rounded-lg p-3 mb-2 border-l-4 border-l-brand-500">
					<div class="flex items-start gap-2">
						<Quote size={14} class="text-brand-500 flex-shrink-0 mt-0.5" />
						<div>
							<h4 class="font-semibold text-xs text-brand-700 dark:text-brand-400 mb-1">The Bottom Line</h4>
							<p class="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
								{reportOutput.bottomLine}
							</p>
						</div>
					</div>
				</div>

				<!-- Two column layout for remaining sections -->
				<div class="grid grid-cols-2 gap-2">
					<!-- Key Takeaways -->
					<div class="bg-slate-50 dark:bg-slate-900 rounded-lg p-2">
						<div class="flex items-center gap-1.5 mb-1.5">
							<Lightbulb size={12} class="text-amber-500" />
							<h4 class="font-semibold text-[11px] text-slate-900 dark:text-white">Key Takeaways</h4>
						</div>
						<ul class="space-y-0.5">
							{#each reportOutput.takeaways as takeaway}
								<li class="text-[10px] text-slate-600 dark:text-slate-400 flex items-start gap-1">
									<span class="text-brand-500 mt-0.5">•</span>
									<span>{takeaway}</span>
								</li>
							{/each}
						</ul>
					</div>

					<!-- Next Steps -->
					<div class="bg-slate-50 dark:bg-slate-900 rounded-lg p-2">
						<div class="flex items-center gap-1.5 mb-1.5">
							<ArrowRight size={12} class="text-emerald-500" />
							<h4 class="font-semibold text-[11px] text-slate-900 dark:text-white">Next Steps</h4>
						</div>
						<ul class="space-y-0.5">
							{#each reportOutput.nextSteps as step, i}
								<li class="text-[10px] text-slate-600 dark:text-slate-400 flex items-start gap-1">
									<span class="text-emerald-500 font-medium">{i + 1}.</span>
									<span>{step}</span>
								</li>
							{/each}
						</ul>
					</div>
				</div>

				<!-- Blind Spots indicator -->
				<div class="mt-2 flex items-center gap-2 px-2 py-1.5 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
					<AlertTriangle size={12} class="text-amber-500 flex-shrink-0" />
					<p class="text-[10px] text-amber-700 dark:text-amber-400">
						<span class="font-semibold">Blind Spot:</span> {reportOutput.blindSpots}
					</p>
				</div>
			</div>
		</div>
	</div>

	<!-- Slide Indicators -->
	<div class="flex justify-center gap-2 mt-4">
		{#each Array(SLIDE_COUNT) as _, i (i)}
			<button
				onclick={() => goToSlide(i)}
				class="h-2 rounded-full transition-all duration-300 {currentSlide === i
					? 'bg-brand-500 w-6'
					: 'bg-slate-300 dark:bg-slate-600 hover:bg-slate-400 dark:hover:bg-slate-500 w-2'}"
				aria-label="Go to slide {i + 1}"
			></button>
		{/each}
	</div>

	<!-- Slide Labels -->
	<div class="flex justify-center gap-8 mt-3 text-sm text-slate-500 dark:text-slate-400">
		<button
			onclick={() => goToSlide(0)}
			class="hover:text-brand-600 dark:hover:text-brand-400 transition-colors {currentSlide === 0 ? 'text-brand-600 dark:text-brand-400 font-medium' : ''}"
		>
			Ask
		</button>
		<button
			onclick={() => goToSlide(1)}
			class="hover:text-brand-600 dark:hover:text-brand-400 transition-colors {currentSlide === 1 ? 'text-brand-600 dark:text-brand-400 font-medium' : ''}"
		>
			Discuss
		</button>
		<button
			onclick={() => goToSlide(2)}
			class="hover:text-brand-600 dark:hover:text-brand-400 transition-colors {currentSlide === 2 ? 'text-brand-600 dark:text-brand-400 font-medium' : ''}"
		>
			Decide
		</button>
	</div>
</div>

<style>
	@keyframes blink {
		0%, 50% { opacity: 1; }
		51%, 100% { opacity: 0; }
	}

	.animate-blink {
		animation: blink 0.8s infinite;
	}

	@keyframes progress {
		0% { width: 0%; }
		100% { width: 100%; }
	}

	.animate-progress {
		animation: progress 3s ease-out forwards;
	}
</style>
