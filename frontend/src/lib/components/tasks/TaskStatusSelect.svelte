<script lang="ts">
	/**
	 * TaskStatusSelect - Dropdown for selecting task status.
	 */
	import { getTaskStatusColor } from '$lib/utils/colors';

	interface StatusOption {
		value: string;
		label: string;
		color: string;
	}

	interface Props {
		status: string;
		onStatusChange: (status: string) => void;
	}

	let { status, onStatusChange }: Props = $props();

	const statusOptions: StatusOption[] = [
		{
			value: 'pending',
			label: 'Pending',
			color: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300'
		},
		{
			value: 'accepted',
			label: 'Accepted',
			color: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300'
		},
		{
			value: 'in_progress',
			label: 'In Progress',
			color: 'bg-info-100 text-info-700 dark:bg-info-900/30 dark:text-info-300'
		},
		{
			value: 'delayed',
			label: 'Delayed',
			color: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300'
		},
		{
			value: 'rejected',
			label: 'Rejected',
			color: 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300'
		},
		{
			value: 'complete',
			label: 'Complete',
			color: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300'
		},
		{
			value: 'failed',
			label: 'Failed',
			color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
		}
	];

	function handleChange(e: Event) {
		const target = e.currentTarget as HTMLSelectElement;
		onStatusChange(target.value);
	}
</script>

<div class="flex-shrink-0 w-full sm:w-auto">
	<select
		value={status}
		onchange={handleChange}
		class="w-full sm:w-auto px-4 py-2.5 text-sm font-medium rounded-lg border-0 {getTaskStatusColor(
			status
		)} cursor-pointer focus:ring-2 focus:ring-info-500 shadow-sm"
	>
		{#each statusOptions as option}
			<option value={option.value}>{option.label}</option>
		{/each}
	</select>
</div>
