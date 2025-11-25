<script lang="ts">
	/**
	 * Comprehensive Meeting Results Page
	 *
	 * Displays a polished, executive-ready view of completed deliberations:
	 * - Executive summary and key recommendation
	 * - Expert panel composition
	 * - Detailed synthesis with all sections
	 * - Individual expert recommendations
	 * - Actionable tasks with accept/reject functionality
	 * - Meeting quality metrics
	 * - Export options (PDF, Markdown)
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { apiClient } from '$lib/api/client';
	import { parseSynthesisXML, isXMLFormatted, type SynthesisSection } from '$lib/utils/xml-parser';
	import ActionableTasks from '$lib/components/events/ActionableTasks.svelte';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { CheckCircle, Download, ArrowLeft, Users, TrendingUp, Target, Clock } from 'lucide-svelte';
	import type { SessionDetailResponse } from '$lib/api/types';

	const sessionId: string = $page.params.id!; // SvelteKit guarantees this exists due to [id] route

	let session = $state<SessionDetailResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	// Parsed synthesis sections
	let synthesis = $state<string>('');
	let sections = $state<SynthesisSection | null>(null);
	let isXML = $state(false);

	// Expert recommendations
	let recommendations = $state<any[]>([]);
	let expandedRecommendations = $state<Set<string>>(new Set());

	onMount(async () => {
		await loadSession();
	});

	async function loadSession() {
		try {
			isLoading = true;
			error = null;

			const data = await apiClient.getSession(sessionId);
			session = data;

			// Extract synthesis from state if available
			synthesis = data.state?.final_synthesis || 'Synthesis pending...';

			// Parse synthesis if XML formatted
			isXML = isXMLFormatted(synthesis);
			if (isXML) {
				sections = parseSynthesisXML(synthesis);
			}

			// Extract recommendations from state if available
			if (data.state?.recommendations && data.state.recommendations.length > 0) {
				recommendations = data.state.recommendations;
			}

			isLoading = false;
		} catch (err) {
			console.error('Failed to load session:', err);
			error = err instanceof Error ? err.message : 'Failed to load session';
			isLoading = false;
		}
	}

	function toggleRecommendation(personaCode: string) {
		if (expandedRecommendations.has(personaCode)) {
			expandedRecommendations.delete(personaCode);
		} else {
			expandedRecommendations.add(personaCode);
		}
		expandedRecommendations = new Set(expandedRecommendations);
	}

	async function exportMarkdown() {
		const markdown = generateMarkdownReport();
		const blob = new Blob([markdown], { type: 'text/markdown' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `meeting-results-${sessionId}.md`;
		a.click();
		URL.revokeObjectURL(url);
	}

	function generateMarkdownReport(): string {
		if (!session) return '';

		let md = `# Meeting Results\n\n`;
		md += `**Session ID:** ${sessionId}\n`;
		md += `**Date:** ${new Date(session.created_at).toLocaleDateString()}\n`;
		md += `**Status:** ${session.status}\n\n`;

		md += `## Problem Statement\n\n${session.problem_statement}\n\n`;

		if (sections?.executive_summary) {
			md += `## Executive Summary\n\n${sections.executive_summary}\n\n`;
		}

		if (sections?.recommendation) {
			md += `## Key Recommendation\n\n${sections.recommendation}\n\n`;
		}

		if (sections?.rationale) {
			md += `## Rationale\n\n${sections.rationale}\n\n`;
		}

		if (recommendations.length > 0) {
			md += `## Expert Recommendations\n\n`;
			recommendations.forEach(rec => {
				md += `### ${rec.persona_name}\n\n`;
				md += `**Recommendation:** ${rec.recommendation}\n\n`;
				md += `**Reasoning:** ${rec.reasoning}\n\n`;
				md += `**Confidence:** ${Math.round(rec.confidence * 100)}%\n\n`;
			});
		}

		md += `## Meeting Metrics\n\n`;
		md += `- **Rounds:** ${session.round_number}\n`;
		md += `- **Duration:** ${formatDuration(session.created_at, session.updated_at)}\n`;

		return md;
	}

	function formatDuration(start: string, end: string): string {
		const diff = new Date(end).getTime() - new Date(start).getTime();
		const minutes = Math.floor(diff / 60000);
		return `${minutes} minutes`;
	}
</script>

<div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
	<div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Header -->
		<div class="mb-8">
			<a
				href="/dashboard"
				class="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 mb-4 transition-colors"
			>
				<ArrowLeft class="w-4 h-4" />
				<span class="font-medium">Back to Dashboard</span>
			</a>

			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-4xl font-bold text-slate-900 dark:text-white mb-2">
						Meeting Results
					</h1>
					{#if session}
						<p class="text-slate-600 dark:text-slate-400">
							{new Date(session.created_at).toLocaleDateString('en-US', {
								weekday: 'long',
								year: 'numeric',
								month: 'long',
								day: 'numeric',
								hour: '2-digit',
								minute: '2-digit'
							})}
						</p>
					{/if}
				</div>

				{#if session && !isLoading}
					<button
						onclick={exportMarkdown}
						class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-sm"
					>
						<Download class="w-4 h-4" />
						Export Report
					</button>
				{/if}
			</div>
		</div>

		{#if isLoading}
			<div class="flex items-center justify-center py-24">
				<div class="text-center">
					<svg class="animate-spin h-12 w-12 text-blue-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					<p class="text-slate-600 dark:text-slate-400">Loading results...</p>
				</div>
			</div>
		{:else if error}
			<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
				<p class="text-red-800 dark:text-red-200">{error}</p>
			</div>
		{:else if session}
			<!-- Main Content Grid -->
			<div class="space-y-6">
				<!-- Meeting Metrics at Top -->
				<div class="grid grid-cols-3 gap-4">
					<div class="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
						<p class="text-slate-600 dark:text-slate-400 text-sm mb-1">Rounds</p>
						<p class="text-3xl font-bold text-slate-900 dark:text-white">{session.state?.round_number || 0}</p>
					</div>
					<div class="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
						<p class="text-slate-600 dark:text-slate-400 text-sm mb-1">Duration</p>
						<p class="text-lg font-semibold text-slate-900 dark:text-white">
							{formatDuration(session.created_at, session.updated_at)}
						</p>
					</div>
					<div class="bg-white dark:bg-slate-800 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
						<p class="text-slate-600 dark:text-slate-400 text-sm mb-1">Experts</p>
						<p class="text-3xl font-bold text-slate-900 dark:text-white">
							{session.state?.persona_codes?.length || recommendations.length || 0}
						</p>
					</div>
				</div>

				<!-- Expert Panel -->
				{#if session.state?.personas && session.state.personas.length > 0}
					<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
						<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
							<Users class="w-5 h-5 text-purple-600" />
							Expert Panel
						</h2>
						<div class="flex flex-wrap gap-3">
							{#each session.state.personas as persona}
								<div class="flex items-center gap-2 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2">
									<div class="w-8 h-8 bg-gradient-to-br from-purple-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
										{persona.name?.charAt(0) || persona.code?.charAt(0) || '?'}
									</div>
									<div>
										<p class="font-medium text-slate-900 dark:text-white text-sm">{persona.name || persona.code}</p>
										{#if persona.domain_expertise && persona.domain_expertise.length > 0}
											<p class="text-xs text-slate-600 dark:text-slate-400">{persona.domain_expertise.slice(0, 2).join(', ')}</p>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Problem Statement -->
				<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
					<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
						<Target class="w-5 h-5 text-blue-600" />
						Problem Statement
					</h2>
					<p class="text-slate-700 dark:text-slate-300 leading-relaxed">
						{session.problem?.statement || session.problem_statement || 'No problem statement available'}
					</p>
				</div>

				<!-- Sub-Problems -->
				{#if session.problem?.sub_problems && session.problem.sub_problems.length > 0}
					<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
						<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-4">
							Sub-Problems Analyzed
						</h2>
						<div class="space-y-3">
							{#each session.problem.sub_problems as subProblem, index}
								<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
									<div class="flex items-start gap-3">
										<div class="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
											{index + 1}
										</div>
										<div class="flex-1">
											<p class="text-slate-800 dark:text-slate-200 font-medium">{subProblem.goal}</p>
										</div>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Executive Summary & Key Recommendation (Prominent) -->
				{#if sections?.executive_summary || sections?.recommendation}
					<div class="grid md:grid-cols-2 gap-6">
						{#if sections.executive_summary}
							<div class="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border-2 border-blue-200 dark:border-blue-700 rounded-xl p-6 shadow-sm">
								<h3 class="font-semibold text-blue-900 dark:text-blue-100 mb-3 flex items-center gap-2 text-lg">
									<CheckCircle class="w-5 h-5" />
									Executive Summary
								</h3>
								<div class="text-blue-800 dark:text-blue-200 whitespace-pre-wrap leading-relaxed">
									{sections.executive_summary}
								</div>
							</div>
						{/if}

						{#if sections.recommendation}
							<div class="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 border-2 border-green-200 dark:border-green-700 rounded-xl p-6 shadow-sm">
								<h3 class="font-semibold text-green-900 dark:text-green-100 mb-3 flex items-center gap-2 text-lg">
									<TrendingUp class="w-5 h-5" />
									Key Recommendation
								</h3>
								<div class="text-green-800 dark:text-green-200 whitespace-pre-wrap leading-relaxed font-medium">
									{sections.recommendation}
								</div>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Expert Recommendations -->
				{#if recommendations.length > 0}
					<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
						<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
							<Users class="w-5 h-5 text-purple-600" />
							Expert Recommendations
						</h2>

						<div class="space-y-3">
							{#each recommendations as rec}
								{@const isExpanded = expandedRecommendations.has(rec.persona_code)}
								<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
									<div class="flex items-start justify-between gap-3">
										<div class="flex-1">
											<div class="flex items-center gap-2 mb-2">
												<div class="w-8 h-8 bg-gradient-to-br from-purple-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
													{rec.persona_name?.charAt(0) || '?'}
												</div>
												<h4 class="text-lg font-semibold text-slate-800 dark:text-slate-100">
													{rec.persona_name}
												</h4>
												<Badge variant="neutral" size="sm">
													{Math.round(rec.confidence * 100)}% confidence
												</Badge>
											</div>

											<p class="text-slate-700 dark:text-slate-300 font-medium mb-2 ml-10">
												{rec.recommendation}
											</p>

											<button
												onclick={() => toggleRecommendation(rec.persona_code)}
												class="text-sm text-blue-600 dark:text-blue-400 hover:underline font-medium ml-10"
											>
												{isExpanded ? 'Hide details' : 'View reasoning & conditions'}
											</button>

											{#if isExpanded}
												<div class="mt-3 ml-10 pl-4 border-l-2 border-slate-300 dark:border-slate-600 space-y-2">
													<div>
														<p class="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Reasoning</p>
														<p class="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
															{rec.reasoning}
														</p>
													</div>

													{#if rec.conditions && rec.conditions.length > 0}
														<div>
															<p class="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">Conditions</p>
															<ul class="list-disc list-inside text-sm text-slate-600 dark:text-slate-400 space-y-1">
																{#each rec.conditions as condition}
																	<li>{condition}</li>
																{/each}
															</ul>
														</div>
													{/if}
												</div>
											{/if}
										</div>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Actionable Tasks -->
				<ActionableTasks sessionId={sessionId} />

				<!-- Detailed Synthesis Sections (Collapsible) -->
				{#if sections}
					<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
						<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-4">
							Detailed Analysis
						</h2>

						<div class="space-y-2">
							{#if sections.rationale}
								<details class="bg-slate-50 dark:bg-slate-900/50 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
									<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
										Rationale
									</summary>
									<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap leading-relaxed">
										{sections.rationale}
									</div>
								</details>
							{/if}

							{#if sections.implementation_considerations}
								<details class="bg-slate-50 dark:bg-slate-900/50 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
									<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
										Implementation Considerations
									</summary>
									<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap leading-relaxed">
										{sections.implementation_considerations}
									</div>
								</details>
							{/if}

							{#if sections.risks_and_mitigations}
								<details class="bg-slate-50 dark:bg-slate-900/50 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
									<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
										Risks & Mitigations
									</summary>
									<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap leading-relaxed">
										{sections.risks_and_mitigations}
									</div>
								</details>
							{/if}

							{#if sections.success_metrics}
								<details class="bg-slate-50 dark:bg-slate-900/50 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
									<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
										Success Metrics
									</summary>
									<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap leading-relaxed">
										{sections.success_metrics}
									</div>
								</details>
							{/if}

							{#if sections.timeline}
								<details class="bg-slate-50 dark:bg-slate-900/50 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
									<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
										Timeline
									</summary>
									<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap leading-relaxed">
										{sections.timeline}
									</div>
								</details>
							{/if}

							{#if sections.confidence_assessment}
								<details class="bg-slate-50 dark:bg-slate-900/50 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
									<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
										Confidence Assessment
									</summary>
									<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap leading-relaxed">
										{sections.confidence_assessment}
									</div>
								</details>
							{/if}

							{#if sections.open_questions}
								<details class="bg-slate-50 dark:bg-slate-900/50 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
									<summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300 p-4 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors">
										Open Questions
									</summary>
									<div class="px-4 pb-4 pt-2 text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap leading-relaxed">
										{sections.open_questions}
									</div>
								</details>
							{/if}
						</div>
					</div>
				{:else}
					<!-- Fallback: Raw synthesis if not XML formatted -->
					<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
						<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-4">
							Final Synthesis
						</h2>
						<div class="prose dark:prose-invert max-w-none">
							<p class="whitespace-pre-wrap text-slate-700 dark:text-slate-300 leading-relaxed">
								{synthesis}
							</p>
						</div>
					</div>
				{/if}

			</div>
		{/if}
	</div>
</div>
