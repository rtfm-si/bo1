<script lang="ts">
	/**
	 * SynthesisProgress - Multi-step synthesis progress indicator
	 *
	 * Shows a visual progress indicator for multi-step synthesis operations
	 * with animated transitions between steps.
	 *
	 * Props:
	 * - currentStep: number - Index of current step (0-based)
	 * - steps: Array<{ label: string; status: 'pending' | 'active' | 'complete' }>
	 * - isActive: boolean - Whether the process is currently running
	 *
	 * Example usage:
	 * <SynthesisProgress
	 *   currentStep={2}
	 *   steps={[
	 *     { label: 'Analyzing', status: 'complete' },
	 *     { label: 'Synthesizing', status: 'complete' },
	 *     { label: 'Finalizing', status: 'active' },
	 *     { label: 'Complete', status: 'pending' }
	 *   ]}
	 *   isActive={true}
	 * />
	 */

	import { CheckCircle, Circle, Loader2 } from 'lucide-svelte';

	interface Step {
		label: string;
		status: 'pending' | 'active' | 'complete';
	}

	interface Props {
		currentStep: number;
		steps: Step[];
		isActive: boolean;
	}

	let { currentStep, steps, isActive }: Props = $props();

	// Get icon and styles for each step status
	function getStepConfig(step: Step, index: number) {
		switch (step.status) {
			case 'complete':
				return {
					icon: CheckCircle,
					iconColor: 'text-[hsl(142,76%,36%)] dark:text-[hsl(142,76%,60%)]',
					labelColor: 'text-neutral-700 dark:text-neutral-300',
					bgColor: 'bg-[hsl(142,76%,95%)] dark:bg-[hsl(142,76%,20%)]',
					animate: false,
				};
			case 'active':
				return {
					icon: Loader2,
					iconColor: 'text-brand-500 dark:text-brand-400',
					labelColor: 'text-neutral-900 dark:text-white font-semibold',
					bgColor: 'bg-brand-50 dark:bg-brand-900/20',
					animate: true,
				};
			case 'pending':
				return {
					icon: Circle,
					iconColor: 'text-neutral-400 dark:text-neutral-600',
					labelColor: 'text-neutral-500 dark:text-neutral-500',
					bgColor: 'bg-neutral-100 dark:bg-neutral-800',
					animate: false,
				};
		}
	}
</script>

<div class="w-full">
	<!-- Progress Steps -->
	<div class="flex items-center justify-between gap-2">
		{#each steps as step, index (step.label)}
			{@const config = getStepConfig(step, index)}
			{@const isLast = index === steps.length - 1}
			{@const Icon = config.icon}

			<div class="flex items-center gap-2 flex-1">
				<!-- Step Indicator -->
				<div
					class="flex items-center gap-2 px-3 py-2 rounded-md {config.bgColor} transition-all duration-300 flex-1"
				>
					<!-- Icon -->
					<Icon
						size={16}
						class="{config.iconColor} {config.animate ? 'animate-spin' : ''} flex-shrink-0"
					/>

					<!-- Label -->
					<span class="text-[0.75rem] {config.labelColor} transition-all duration-300 truncate">
						{step.label}
					</span>
				</div>

				<!-- Connector Line (not shown for last step) -->
				{#if !isLast}
					<div class="flex-shrink-0 w-4 h-0.5 bg-neutral-200 dark:bg-neutral-700">
						<!-- Progress fill (shows when step is complete or active) -->
						{#if step.status === 'complete' || (step.status === 'active' && isActive)}
							<div
								class="h-full bg-brand-500 dark:bg-brand-400 transition-all duration-500"
								style="width: {step.status === 'complete' ? '100%' : '50%'}"
							></div>
						{/if}
					</div>
				{/if}
			</div>
		{/each}
	</div>

	<!-- Progress Bar (optional visual reinforcement) -->
	<div class="mt-3 w-full h-1 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
		<div
			class="h-full bg-gradient-to-r from-brand-500 to-brand-400 transition-all duration-500 ease-out"
			style="width: {(currentStep / (steps.length - 1)) * 100}%"
		></div>
	</div>
</div>

<style>
	/* Smooth animations for step transitions */
	.flex-1 {
		transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
	}
</style>
