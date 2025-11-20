<script context="module" lang="ts">
	// Types
	export interface Persona {
		name: string;
		code: string;
		expertise: string;
	}
</script>

<script lang="ts">
	/**
	 * ContributionCard Component - Expert contribution display
	 * Used to show advisor messages in deliberation feed
	 */

	import Avatar from './Avatar.svelte';
	import Badge from './Badge.svelte';
	import type { Snippet } from 'svelte';

	// Props
	interface Props {
		persona: Persona;
		content: string;
		timestamp: Date;
		confidence?: 'high' | 'medium' | 'low';
		actions?: Snippet;
	}

	let {
		persona,
		content,
		timestamp,
		confidence = 'medium',
		actions
	}: Props = $props();

	// Confidence badge config
	const confidenceConfig = {
		high: { variant: 'success' as const, label: 'High Confidence' },
		medium: { variant: 'info' as const, label: 'Medium Confidence' },
		low: { variant: 'warning' as const, label: 'Low Confidence' },
	};

	// Format timestamp
	function formatTimestamp(date: Date): string {
		const now = new Date();
		const diff = now.getTime() - date.getTime();
		const seconds = Math.floor(diff / 1000);
		const minutes = Math.floor(seconds / 60);
		const hours = Math.floor(minutes / 60);

		if (seconds < 60) return 'just now';
		if (minutes < 60) return `${minutes}m ago`;
		if (hours < 24) return `${hours}h ago`;

		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		});
	}

	const formattedTime = $derived(formatTimestamp(timestamp));
	const confidenceBadge = $derived(confidenceConfig[confidence]);
</script>

<article
	class="bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
>
	<!-- Header -->
	<div class="flex items-start gap-3 mb-3">
		<Avatar name={persona.name} size="md" />

		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-2 mb-1">
				<h3 class="font-semibold text-neutral-900 dark:text-neutral-100 truncate">
					{persona.name}
				</h3>
				<Badge variant="neutral" size="sm">{persona.code}</Badge>
			</div>

			<p class="text-xs text-neutral-600 dark:text-neutral-400 truncate">
				{persona.expertise}
			</p>
		</div>

		<div class="flex flex-col items-end gap-1">
			<time
				class="text-xs text-neutral-500 dark:text-neutral-400"
				datetime={timestamp.toISOString()}
			>
				{formattedTime}
			</time>
			<Badge variant={confidenceBadge.variant} size="sm">
				{confidenceBadge.label}
			</Badge>
		</div>
	</div>

	<!-- Content -->
	<div class="prose prose-sm dark:prose-invert max-w-none">
		<p class="text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
			{content}
		</p>
	</div>

	<!-- Actions (optional slot) -->
	{#if actions}
		<div class="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700">
			{@render actions()}
		</div>
	{/if}
</article>
