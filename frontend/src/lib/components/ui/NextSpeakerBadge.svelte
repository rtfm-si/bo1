<script lang="ts">
	interface Props {
		speakerName: string;
		message?: string;
	}

	let { speakerName, message = 'is preparing insights...' }: Props = $props();
</script>

<div class="flex items-center gap-2 py-2 px-3 bg-warning-50 dark:bg-warning-900/20
			border border-warning-200 dark:border-warning-800 rounded-lg animate-pulse">
	<div class="w-2 h-2 bg-warning-500 rounded-full"></div>
	<span class="text-sm font-medium text-warning-800 dark:text-warning-200">
		{speakerName} {message}
	</span>
</div>
