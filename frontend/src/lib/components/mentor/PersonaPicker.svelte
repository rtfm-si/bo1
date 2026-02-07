<script lang="ts">
	/**
	 * PersonaPicker - Select mentor persona
	 *
	 * Fetches available personas from API and allows manual selection.
	 * Includes "Auto" option that lets AI select based on question.
	 */
	import type { MentorPersonaDetail } from '$lib/api/types';
	import { apiClient } from '$lib/api/client';
	import { User, Target, BarChart3, Sparkles, Briefcase, CheckCircle, ChevronDown, Search } from 'lucide-svelte';
	import { onMount } from 'svelte';

	let {
		selected = null as string | null,
		onChange,
		showDescription = false
	}: {
		selected: string | null;
		onChange: (persona: string | null) => void;
		showDescription?: boolean;
	} = $props();

	// Icon mapping
	const iconMap: Record<string, typeof User> = {
		briefcase: Briefcase,
		'check-circle': CheckCircle,
		'chart-bar': BarChart3,
		user: User,
		target: Target,
		search: Search
	};

	let personas = $state<MentorPersonaDetail[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let expanded = $state(false);

	onMount(async () => {
		try {
			const response = await apiClient.getMentorPersonas();
			personas = response.personas;
		} catch (e) {
			error = 'Failed to load personas';
			console.error('Failed to load mentor personas:', e);
			// Fallback to hardcoded personas
			personas = [
				{
					id: 'general',
					name: 'General Business Advisor',
					description: 'Broad business guidance covering strategy, operations, and decision-making.',
					expertise: ['strategy', 'operations', 'leadership', 'problem-solving'],
					icon: 'briefcase'
				},
				{
					id: 'action_coach',
					name: 'Action & Execution Coach',
					description: 'Focused guidance on task management, prioritization, and getting things done.',
					expertise: ['task management', 'prioritization', 'execution', 'time management', 'delegation'],
					icon: 'check-circle'
				},
				{
					id: 'data_analyst',
					name: 'Data & Analytics Advisor',
					description: 'Expert in data interpretation, metrics analysis, and data-driven decisions.',
					expertise: ['data analysis', 'metrics', 'KPIs', 'visualization', 'business intelligence'],
					icon: 'chart-bar'
				},
				{
					id: 'researcher',
					name: 'Research',
					description: 'Investigates market trends, competitors, and industry insights to inform your decisions.',
					expertise: ['market research', 'competitive analysis', 'industry trends', 'benchmarking'],
					icon: 'search'
				}
			];
		} finally {
			loading = false;
		}
	});

	function getIcon(iconName: string) {
		return iconMap[iconName] || User;
	}

	function getSelectedLabel(): string {
		if (!selected) return 'Auto (AI chooses)';
		const persona = personas.find((p) => p.id === selected);
		return persona?.name || 'Auto (AI chooses)';
	}

	function handleSelect(personaId: string | null) {
		onChange(personaId);
		expanded = false;
	}
</script>

{#if loading}
	<div class="flex gap-2">
		{#each Array(3) as _}
			<div class="h-10 w-28 bg-neutral-200 dark:bg-neutral-700 rounded-lg animate-pulse"></div>
		{/each}
	</div>
{:else}
	{#if showDescription}
		<!-- Dropdown style for larger view with descriptions -->
		<div class="relative">
			<button
				type="button"
				class="flex items-center justify-between w-full px-4 py-3 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-left"
				onclick={() => (expanded = !expanded)}
			>
				<div class="flex items-center gap-2">
					{#if selected}
						{@const persona = personas.find((p) => p.id === selected)}
						{#if persona}
							{@const Icon = getIcon(persona.icon)}
							<Icon class="w-5 h-5 text-brand-500" />
							<span class="font-medium">{persona.name}</span>
						{/if}
					{:else}
						<Sparkles class="w-5 h-5 text-warning-500" />
						<span class="font-medium">Auto (AI chooses)</span>
					{/if}
				</div>
				<ChevronDown class="w-4 h-4 text-neutral-400 transition-transform {expanded ? 'rotate-180' : ''}" />
			</button>

			{#if expanded}
				<div class="absolute z-10 mt-1 w-full bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg">
					<!-- Auto option -->
					<button
						type="button"
						class="w-full px-4 py-3 text-left hover:bg-neutral-50 dark:hover:bg-neutral-700/50 flex items-start gap-3 {!selected ? 'bg-brand-50 dark:bg-brand-900/20' : ''}"
						onclick={() => handleSelect(null)}
					>
						<Sparkles class="w-5 h-5 text-warning-500 mt-0.5" />
						<div>
							<div class="font-medium text-neutral-900 dark:text-neutral-100">Auto (AI chooses)</div>
							<div class="text-sm text-neutral-500 dark:text-neutral-400">
								Let AI select the best persona based on your question
							</div>
						</div>
					</button>

					<div class="border-t border-neutral-100 dark:border-neutral-700"></div>

					<!-- Persona options -->
					{#each personas as persona}
						{@const Icon = getIcon(persona.icon)}
						<button
							type="button"
							class="w-full px-4 py-3 text-left hover:bg-neutral-50 dark:hover:bg-neutral-700/50 flex items-start gap-3 {selected === persona.id ? 'bg-brand-50 dark:bg-brand-900/20' : ''}"
							onclick={() => handleSelect(persona.id)}
						>
							<Icon class="w-5 h-5 text-brand-500 mt-0.5" />
							<div>
								<div class="font-medium text-neutral-900 dark:text-neutral-100">{persona.name}</div>
								<div class="text-sm text-neutral-500 dark:text-neutral-400">{persona.description}</div>
								{#if persona.expertise?.length}
									<div class="flex flex-wrap gap-1 mt-1">
										{#each persona.expertise.slice(0, 3) as tag}
											<span class="text-xs px-1.5 py-0.5 bg-neutral-100 dark:bg-neutral-700 rounded text-neutral-600 dark:text-neutral-400">
												{tag}
											</span>
										{/each}
									</div>
								{/if}
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	{:else}
		<!-- Compact button style -->
		<div class="flex flex-wrap gap-2">
			<!-- Auto option -->
			<button
				type="button"
				class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all {!selected
					? 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300 ring-1 ring-warning-500'
					: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'}"
				onclick={() => onChange(null)}
				title="Let AI select the best persona based on your question"
			>
				<Sparkles class="w-4 h-4" />
				<span class="font-medium">Auto</span>
			</button>

			{#each personas as persona}
				{@const Icon = getIcon(persona.icon)}
				<button
					type="button"
					class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all {selected === persona.id
						? 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 ring-1 ring-brand-500'
						: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'}"
					onclick={() => onChange(persona.id)}
					title={persona.description}
				>
					<Icon class="w-4 h-4" />
					<span class="font-medium">{persona.name.split(' ')[0]}</span>
				</button>
			{/each}
		</div>
	{/if}
{/if}
