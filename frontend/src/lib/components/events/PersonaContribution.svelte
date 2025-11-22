<script lang="ts">
	/**
	 * PersonaContribution Event Component
	 * Displays an expert's contribution to the deliberation
	 */
	import type { ContributionEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: ContributionEvent;
	}

	let { event }: Props = $props();

	// Persona-specific colors for visual distinction
	function getPersonaColor(code: string): string {
		const colors: Record<string, string> = {
			'fi': 'bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200 border-emerald-300 dark:border-emerald-700',
			'co': 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border-blue-300 dark:border-blue-700',
			'cu': 'bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 border-purple-300 dark:border-purple-700',
			'bo': 'bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 border-orange-300 dark:border-orange-700',
			'sk': 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 border-red-300 dark:border-red-700',
			'sa': 'bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200 border-indigo-300 dark:border-indigo-700',
			'le': 'bg-pink-100 dark:bg-pink-900 text-pink-800 dark:text-pink-200 border-pink-300 dark:border-pink-700',
			'te': 'bg-cyan-100 dark:bg-cyan-900 text-cyan-800 dark:text-cyan-200 border-cyan-300 dark:border-cyan-700',
		};
		return colors[code] || 'bg-slate-100 dark:bg-slate-900 text-slate-800 dark:text-slate-200 border-slate-300 dark:border-slate-700';
	}

	function getPersonaInitials(name: string): string {
		const parts = name.split(' ');
		if (parts.length >= 2) {
			return parts[0][0] + parts[1][0];
		}
		return name.substring(0, 2).toUpperCase();
	}
</script>

<div class="space-y-3">
	<div class="flex items-start gap-3">
		<div
			class="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center font-bold text-base border-2 {getPersonaColor(event.data.persona_code)}"
		>
			{getPersonaInitials(event.data.persona_name)}
		</div>
		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-2 mb-2 flex-wrap">
				<h3 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
					{event.data.persona_name}
				</h3>
				<Badge variant="brand" size="sm">Round {event.data.round}</Badge>
				{#if event.data.contribution_type === 'initial'}
					<Badge variant="success" size="sm">Initial</Badge>
				{:else}
					<Badge variant="neutral" size="sm">Follow-up</Badge>
				{/if}
			</div>

			<div
				class="prose prose-sm dark:prose-invert max-w-none text-neutral-700 dark:text-neutral-300"
			>
				<p class="whitespace-pre-wrap">{event.data.content}</p>
			</div>
		</div>
	</div>
</div>
