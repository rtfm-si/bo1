<script lang="ts">
	/**
	 * FollowupBanner - Nudges user to record outcomes for old decisions
	 * Displayed on the meetings list page.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { PendingFollowupResponse } from '$lib/api/types';
	import { X, ArrowRight } from 'lucide-svelte';

	let followups = $state<PendingFollowupResponse[]>([]);
	let dismissed = $state(false);

	onMount(async () => {
		try {
			followups = await apiClient.getPendingFollowups();
		} catch {
			// Silently fail — non-critical
		}
	});

	function dismiss() {
		dismissed = true;
	}
</script>

{#if !dismissed && followups.length > 0}
	<div class="mb-6 rounded-xl border border-brand-200 dark:border-brand-800 bg-brand-50 dark:bg-brand-950 p-4">
		<div class="flex items-start justify-between gap-3">
			<div class="flex-1 space-y-2">
				<p class="text-sm font-medium text-brand-800 dark:text-brand-200">
					How did your decisions turn out?
				</p>
				{#each followups.slice(0, 3) as followup (followup.decision_id)}
					<a
						href="/meeting/{followup.session_id}#decision-gate"
						class="flex items-center gap-2 text-sm text-brand-700 dark:text-brand-300 hover:text-brand-900 dark:hover:text-brand-100 group"
					>
						<ArrowRight class="w-4 h-4 flex-shrink-0 group-hover:translate-x-0.5 transition-transform" />
						<span>
							You decided on <strong>"{followup.chosen_option_label}"</strong>
							{followup.days_ago} days ago
						</span>
					</a>
				{/each}
			</div>
			<button
				type="button"
				onclick={dismiss}
				class="p-1 text-brand-400 hover:text-brand-600 dark:hover:text-brand-200"
				aria-label="Dismiss"
			>
				<X class="w-4 h-4" />
			</button>
		</div>
	</div>
{/if}
