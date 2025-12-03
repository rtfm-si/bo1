<script lang="ts">
	/**
	 * TaskStatusSelect - Dropdown for selecting task status.
	 */
	import { getTaskStatusColor } from '$lib/utils/persona-colors';

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
			color: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
		},
		{
			value: 'accepted',
			label: 'Accepted',
			color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
		},
		{
			value: 'in_progress',
			label: 'In Progress',
			color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
		},
		{
			value: 'delayed',
			label: 'Delayed',
			color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
		},
		{
			value: 'rejected',
			label: 'Rejected',
			color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
		},
		{
			value: 'complete',
			label: 'Complete',
			color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
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
		)} cursor-pointer focus:ring-2 focus:ring-blue-500 shadow-sm"
	>
		{#each statusOptions as option}
			<option value={option.value}>{option.label}</option>
		{/each}
	</select>
</div>
