<script lang="ts">
	import { AlertCircle, ArrowRight, Ban } from 'lucide-svelte';
	import { Button, Modal } from '$lib/components/ui';
	import { apiClient } from '$lib/api/client';

	interface Props {
		sessionId: string;
		open: boolean;
		onClose: () => void;
		onTerminated: (result: {
			termination_type: string;
			billable_portion: number;
			completed_sub_problems: number;
			total_sub_problems: number;
		}) => void;
	}

	let { sessionId, open, onClose, onTerminated }: Props = $props();

	type TerminationType = 'blocker_identified' | 'user_cancelled' | 'continue_best_effort';

	let selectedType = $state<TerminationType | null>(null);
	let reason = $state('');
	let isSubmitting = $state(false);
	let error = $state<string | null>(null);

	const terminationOptions = [
		{
			type: 'blocker_identified' as const,
			title: 'Critical Blocker Found',
			description: "I've identified a critical blocker and need to provide more information before continuing.",
			icon: AlertCircle,
			iconClass: 'text-warning-600 dark:text-warning-400'
		},
		{
			type: 'continue_best_effort' as const,
			title: 'Continue with Best Effort',
			description: 'Get results now based on what has been completed, even if analysis is incomplete.',
			icon: ArrowRight,
			iconClass: 'text-brand-600 dark:text-brand-400'
		},
		{
			type: 'user_cancelled' as const,
			title: 'Cancel Meeting',
			description: 'Stop the meeting entirely. No further analysis will be performed.',
			icon: Ban,
			iconClass: 'text-error-600 dark:text-error-400'
		}
	];

	async function handleSubmit() {
		if (!selectedType) return;

		isSubmitting = true;
		error = null;

		try {
			const result = await apiClient.terminateSession(sessionId, selectedType, reason || undefined);
			onTerminated({
				termination_type: result.termination_type,
				billable_portion: result.billable_portion,
				completed_sub_problems: result.completed_sub_problems,
				total_sub_problems: result.total_sub_problems
			});
			onClose();
		} catch (err) {
			console.error('Failed to terminate session:', err);
			error = err instanceof Error ? err.message : 'Failed to terminate meeting';
		} finally {
			isSubmitting = false;
		}
	}

	function handleClose() {
		if (!isSubmitting) {
			selectedType = null;
			reason = '';
			error = null;
			onClose();
		}
	}
</script>

<Modal {open} title="End Meeting Early" size="md" onclose={handleClose} closable={!isSubmitting}>
	<div class="space-y-6">
		<!-- Options -->
		<div class="space-y-3">
			{#each terminationOptions as option (option.type)}
				<button
					type="button"
					class="w-full p-4 text-left rounded-lg border-2 transition-colors
						{selectedType === option.type
							? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
							: 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'}"
					onclick={() => (selectedType = option.type)}
					disabled={isSubmitting}
				>
					<div class="flex items-start gap-3">
						<option.icon size={24} class={option.iconClass} />
						<div>
							<h3 class="font-medium text-neutral-900 dark:text-white">{option.title}</h3>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{option.description}</p>
						</div>
					</div>
				</button>
			{/each}
		</div>

		<!-- Reason input -->
		{#if selectedType}
			<div>
				<label
					for="termination-reason"
					class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
				>
					{selectedType === 'blocker_identified' ? 'Describe the blocker (optional):' : 'Reason (optional):'}
				</label>
				<textarea
					id="termination-reason"
					bind:value={reason}
					rows={3}
					class="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-lg
						bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white
						placeholder-neutral-400 dark:placeholder-neutral-500
						focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
					placeholder={selectedType === 'blocker_identified'
						? 'e.g., Missing critical market data for the European expansion analysis...'
						: 'e.g., Timeline changed, no longer relevant...'}
					disabled={isSubmitting}
				></textarea>
			</div>
		{/if}

		<!-- Error message -->
		{#if error}
			<div class="p-3 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg">
				<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
			</div>
		{/if}
	</div>

	{#snippet footer()}
		<div class="flex items-center justify-end gap-3">
			<Button variant="secondary" size="md" onclick={handleClose} disabled={isSubmitting}>
				Cancel
			</Button>
			<Button
				variant={selectedType === 'user_cancelled' ? 'danger' : 'brand'}
				size="md"
				onclick={handleSubmit}
				disabled={!selectedType || isSubmitting}
			>
				{isSubmitting ? 'Ending...' : 'End Meeting'}
			</Button>
		</div>
	{/snippet}
</Modal>
