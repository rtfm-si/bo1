<script lang="ts">
	/**
	 * Onboarding Checklist - Guides new users through initial setup
	 *
	 * Shows a checklist of steps for new users to complete.
	 * Dismissed when all steps complete or user clicks dismiss.
	 */

	import type { UserContext } from '$lib/api/types';

	// Props
	let {
		userContext = null,
		sessionCount = 0,
		onDismiss,
	}: {
		userContext?: UserContext | null;
		sessionCount?: number;
		onDismiss: () => void;
	} = $props();

	// Onboarding steps with completion logic
	const steps = $derived([
		{
			id: 'context',
			title: 'Set up business context',
			description: 'Help us understand your business for better recommendations',
			href: '/context/overview',
			completed: !!(userContext?.business_model || userContext?.product_description),
		},
		{
			id: 'meeting',
			title: 'Run your first meeting',
			description: 'Get expert perspectives on a decision',
			href: '/meeting/new',
			completed: sessionCount > 0,
		},
		{
			id: 'settings',
			title: 'Review your settings',
			description: 'Customize notifications and preferences',
			href: '/settings',
			completed: !!userContext?.onboarding_completed,
		},
	]);

	const completedCount = $derived(steps.filter((s) => s.completed).length);
	const allComplete = $derived(completedCount === steps.length);
</script>

{#if !allComplete}
	<div
		class="bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-lg p-4 mb-6"
	>
		<!-- Header -->
		<div class="flex items-start justify-between mb-4">
			<div>
				<h3 class="text-sm font-semibold text-brand-900 dark:text-brand-100">
					Welcome! Let's get you started
				</h3>
				<p class="text-xs text-brand-600 dark:text-brand-400 mt-0.5">
					{completedCount} of {steps.length} steps complete
				</p>
			</div>
			<button
				type="button"
				onclick={onDismiss}
				class="text-brand-500 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-200 p-1 rounded"
				aria-label="Dismiss onboarding"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M6 18L18 6M6 6l12 12"
					/>
				</svg>
			</button>
		</div>

		<!-- Progress bar -->
		<div class="h-1.5 bg-brand-100 dark:bg-brand-800 rounded-full mb-4 overflow-hidden">
			<div
				class="h-full bg-brand-500 dark:bg-brand-400 rounded-full transition-all duration-300"
				style="width: {(completedCount / steps.length) * 100}%"
			></div>
		</div>

		<!-- Steps -->
		<div class="space-y-2">
			{#each steps as step}
				<a
					href={step.href}
					class="flex items-center gap-3 p-2 rounded-md hover:bg-brand-100 dark:hover:bg-brand-800/50 transition-colors group"
				>
					<!-- Checkbox -->
					<div
						class={`flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
							step.completed
								? 'bg-brand-500 dark:bg-brand-400 border-brand-500 dark:border-brand-400'
								: 'border-brand-300 dark:border-brand-600 group-hover:border-brand-400 dark:group-hover:border-brand-500'
						}`}
					>
						{#if step.completed}
							<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
							</svg>
						{/if}
					</div>

					<!-- Content -->
					<div class="flex-1 min-w-0">
						<p
							class={`text-sm font-medium ${
								step.completed
									? 'text-brand-500 dark:text-brand-400 line-through'
									: 'text-brand-900 dark:text-brand-100'
							}`}
						>
							{step.title}
						</p>
						{#if !step.completed}
							<p class="text-xs text-brand-600 dark:text-brand-400">
								{step.description}
							</p>
						{/if}
					</div>

					<!-- Arrow -->
					{#if !step.completed}
						<svg
							class="w-4 h-4 text-brand-400 dark:text-brand-500 group-hover:translate-x-0.5 transition-transform"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
					{/if}
				</a>
			{/each}
		</div>
	</div>
{/if}
