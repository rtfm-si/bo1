<script lang="ts">
	/**
	 * ProjectSuggestions - Display AI-generated project suggestions from a completed meeting
	 *
	 * Shows suggestions derived from meeting actions, allowing users to:
	 * - View suggested project groupings
	 * - See which actions would be assigned
	 * - Create projects with one click
	 *
	 * Only shown for completed/terminated meetings.
	 */
	import { apiClient } from '$lib/api/client';
	import type { ProjectSuggestion, CreatedProjectResponse } from '$lib/api/types';
	import {
		Check,
		FolderPlus,
		Info,
		Lightbulb,
		Loader2,
		RefreshCw,
		Sparkles,
		X
	} from 'lucide-svelte';
	import { slide } from 'svelte/transition';

	interface Props {
		/** Session ID to analyze */
		sessionId: string;
		/** Callback when a project is created */
		onProjectCreated?: (project: CreatedProjectResponse['project']) => void;
	}

	let { sessionId, onProjectCreated }: Props = $props();

	let isLoading = $state(false);
	let isCreating = $state<string | null>(null); // Track which suggestion is being created
	let suggestions = $state<ProjectSuggestion[]>([]);
	let createdProjects = $state<Set<string>>(new Set()); // Track created by suggestion name
	let error = $state<string | null>(null);
	let hasLoaded = $state(false);

	// Load suggestions when component mounts or sessionId changes
	$effect(() => {
		if (sessionId && !hasLoaded) {
			loadSuggestions();
		}
	});

	async function loadSuggestions() {
		isLoading = true;
		error = null;
		try {
			const response = await apiClient.getProjectSuggestions(sessionId, 0.6);
			suggestions = response.suggestions;
			hasLoaded = true;
		} catch (err: unknown) {
			const apiError = err as { status?: number; message?: string };
			if (apiError.status === 400) {
				// Session not completed - expected case
				error = 'Project suggestions are only available for completed meetings.';
			} else {
				error = 'Failed to load project suggestions.';
				console.error('Failed to load suggestions:', err);
			}
		} finally {
			isLoading = false;
		}
	}

	async function createProject(suggestion: ProjectSuggestion) {
		isCreating = suggestion.name;
		try {
			const response = await apiClient.createSuggestedProject(sessionId, {
				name: suggestion.name,
				description: suggestion.description,
				action_ids: suggestion.action_ids
			});
			createdProjects.add(suggestion.name);
			createdProjects = createdProjects; // Trigger reactivity
			onProjectCreated?.(response.project);
		} catch (err) {
			console.error('Failed to create project:', err);
			error = 'Failed to create project. Please try again.';
		} finally {
			isCreating = null;
		}
	}

	// Confidence indicator color
	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.8) return 'text-success-600 dark:text-success-400';
		if (confidence >= 0.7) return 'text-warning-600 dark:text-warning-400';
		return 'text-gray-600 dark:text-gray-400';
	}
</script>

<div class="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
	<!-- Header -->
	<div class="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
		<div class="flex items-center gap-2">
			<Sparkles class="h-5 w-5 text-brand-500" />
			<h3 class="font-medium text-gray-900 dark:text-gray-100">Project Suggestions</h3>
		</div>
		<button
			type="button"
			class="rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
			onclick={loadSuggestions}
			disabled={isLoading}
			title="Refresh suggestions"
		>
			<RefreshCw class="h-4 w-4 {isLoading ? 'animate-spin' : ''}" />
		</button>
	</div>

	<!-- Content -->
	<div class="p-4">
		{#if isLoading && !hasLoaded}
			<div class="flex flex-col items-center justify-center py-8">
				<Loader2 class="h-8 w-8 animate-spin text-brand-500" />
				<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Analyzing meeting actions...</p>
			</div>
		{:else if error}
			<div class="flex items-center gap-2 rounded-md bg-gray-50 p-4 dark:bg-gray-900/50">
				<Info class="h-5 w-5 shrink-0 text-gray-400" />
				<p class="text-sm text-gray-600 dark:text-gray-400">{error}</p>
			</div>
		{:else if suggestions.length === 0}
			<div class="flex flex-col items-center py-6 text-center">
				<Lightbulb class="h-10 w-10 text-gray-300 dark:text-gray-600" />
				<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
					No project suggestions found for this meeting.
				</p>
				<p class="text-xs text-gray-500 dark:text-gray-500">
					This can happen if the meeting's actions don't form clear groupings.
				</p>
			</div>
		{:else}
			<div class="space-y-3">
				{#each suggestions as suggestion (suggestion.name)}
					{@const isCreated = createdProjects.has(suggestion.name)}
					<div
						class="rounded-lg border p-4 transition-colors {isCreated
							? 'border-success-200 bg-success-50/50 dark:border-success-800 dark:bg-success-900/20'
							: 'border-gray-200 bg-gray-50/50 dark:border-gray-700 dark:bg-gray-900/30'}"
						transition:slide={{ duration: 200 }}
					>
						<div class="flex items-start justify-between gap-4">
							<div class="flex-1">
								<div class="flex items-center gap-2">
									<h4 class="font-medium text-gray-900 dark:text-gray-100">
										{suggestion.name}
									</h4>
									<span class={`text-xs ${getConfidenceColor(suggestion.confidence)}`}>
										{Math.round(suggestion.confidence * 100)}% match
									</span>
								</div>
								<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
									{suggestion.description}
								</p>
								<p class="mt-2 text-xs text-gray-500 dark:text-gray-500">
									{suggestion.action_ids.length} action{suggestion.action_ids.length === 1 ? '' : 's'}
									would be assigned
								</p>
								{#if suggestion.rationale}
									<p class="mt-1 text-xs italic text-gray-400 dark:text-gray-500">
										"{suggestion.rationale}"
									</p>
								{/if}
							</div>

							{#if createdProjects.has(suggestion.name)}
								<div class="flex items-center gap-1 rounded-full bg-success-100 px-2 py-1 text-success-700 dark:bg-success-900/50 dark:text-success-400">
									<Check class="h-4 w-4" />
									<span class="text-xs font-medium">Created</span>
								</div>
							{:else}
								<button
									type="button"
									class="flex items-center gap-1 rounded-md bg-brand-500 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-600 disabled:opacity-50"
									onclick={() => createProject(suggestion)}
									disabled={isCreating !== null}
								>
									{#if isCreating === suggestion.name}
										<Loader2 class="h-4 w-4 animate-spin" />
									{:else}
										<FolderPlus class="h-4 w-4" />
									{/if}
									Create
								</button>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
