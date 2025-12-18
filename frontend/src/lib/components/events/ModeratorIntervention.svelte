<script lang="ts">
	/**
	 * ModeratorIntervention Event Component
	 * Displays a moderator's intervention to balance the discussion
	 */
	import type { ModeratorInterventionEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';
	import { AlertCircle, Target } from 'lucide-svelte';
	import type { ComponentType } from 'svelte';

	interface Props {
		event: ModeratorInterventionEvent;
	}

	let { event }: Props = $props();

	const moderatorLabels: Record<string, string> = {
		contrarian: 'Contrarian Perspective',
		balance: 'Balance Discussion',
		focus: 'Refocus Discussion',
	};

	const moderatorIcons: Record<string, ComponentType> = {
		contrarian: AlertCircle,
		balance: AlertCircle,
		focus: Target,
	};
</script>

<div class="space-y-3">
	<div
		class="border-l-4 border-warning-500 bg-warning-50 dark:bg-warning-900/20 rounded-lg p-4"
	>
		<div class="flex items-start gap-3">
			{#if event.data.moderator_type === 'focus'}
				<Target size={20} class="text-warning-600 dark:text-warning-400 flex-shrink-0 mt-0.5" />
			{:else}
				<AlertCircle size={20} class="text-warning-600 dark:text-warning-400 flex-shrink-0 mt-0.5" />
			{/if}
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-2">
					<h3 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
						Moderator Intervention
					</h3>
					<Badge variant="warning" size="sm">
						{moderatorLabels[event.data.moderator_type]}
					</Badge>
				</div>

				<div class="mb-2">
					<p class="text-sm text-neutral-600 dark:text-neutral-400 italic mb-1">
						Trigger: {event.data.trigger_reason}
					</p>
					<p class="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
						{event.data.content}
					</p>
				</div>

				<div class="text-xs text-neutral-500 dark:text-neutral-400">
					Round {event.data.round}
				</div>
			</div>
		</div>
	</div>
</div>
