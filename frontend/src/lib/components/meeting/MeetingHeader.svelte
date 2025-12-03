<script lang="ts">
	import { Pause, Play } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';

	interface Props {
		sessionId: string;
		sessionStatus: string | undefined;
		onPause: () => Promise<void>;
		onResume: () => Promise<void>;
	}

	let { sessionId, sessionStatus, onPause, onResume }: Props = $props();
</script>

<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 sticky top-0 z-10">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-4">
				<a
					href="/dashboard"
					class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
					aria-label="Back to dashboard"
				>
					<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
					</svg>
				</a>
				<div class="flex-1">
					<h1 class="text-[1.875rem] font-semibold leading-tight text-neutral-900 dark:text-white">
						Meeting in Progress
					</h1>
				</div>
			</div>

			<div class="flex items-center gap-2">
				{#if sessionStatus === 'active'}
					<Button variant="secondary" size="md" onclick={onPause}>
						{#snippet children()}
							<Pause size={16} />
							<span>Pause</span>
						{/snippet}
					</Button>
				{:else if sessionStatus === 'paused'}
					<Button variant="brand" size="md" onclick={onResume}>
						{#snippet children()}
							<Play size={16} />
							<span>Resume</span>
						{/snippet}
					</Button>
				{/if}
			</div>
		</div>
	</div>
</header>
