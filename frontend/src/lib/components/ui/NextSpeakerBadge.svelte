<script lang="ts">
	interface Props {
		speakerName: string;
		message?: string;
	}

	let { speakerName, message = 'is preparing insights...' }: Props = $props();
</script>

<div class="flex items-center gap-2 py-2 px-3 bg-yellow-50 dark:bg-yellow-900/20
			border border-yellow-200 dark:border-yellow-800 rounded-lg animate-pulse">
	<div class="w-2 h-2 bg-yellow-500 rounded-full"></div>
	<span class="text-sm font-medium text-yellow-800 dark:text-yellow-200">
		{speakerName} {message}
	</span>
</div>
