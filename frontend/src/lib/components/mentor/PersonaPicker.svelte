<script lang="ts">
	/**
	 * PersonaPicker - Select mentor persona
	 */
	import type { MentorPersona } from '$lib/api/types';
	import { User, Target, BarChart3 } from 'lucide-svelte';

	let {
		selected = 'general',
		onChange
	}: {
		selected: MentorPersona;
		onChange: (persona: MentorPersona) => void;
	} = $props();

	const personas = [
		{
			id: 'general' as const,
			name: 'General Mentor',
			description: 'Strategic advice & guidance',
			icon: User
		},
		{
			id: 'action_coach' as const,
			name: 'Action Coach',
			description: 'Prioritization & execution',
			icon: Target
		},
		{
			id: 'data_analyst' as const,
			name: 'Data Analyst',
			description: 'Data insights & metrics',
			icon: BarChart3
		}
	];
</script>

<div class="flex flex-wrap gap-2">
	{#each personas as persona}
		<button
			type="button"
			class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all {selected ===
			persona.id
				? 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 ring-1 ring-brand-500'
				: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'}"
			onclick={() => onChange(persona.id)}
		>
			<persona.icon class="w-4 h-4" />
			<span class="font-medium">{persona.name}</span>
		</button>
	{/each}
</div>
