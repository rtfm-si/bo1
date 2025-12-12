<script lang="ts">
	/**
	 * MentorMessage - Display a single mentor chat message
	 */
	import type { MentorMessage as MessageType, MentorPersona } from '$lib/api/types';
	import { User, Bot, Target, BarChart3 } from 'lucide-svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';

	let {
		message,
		isStreaming = false
	}: {
		message: MessageType;
		isStreaming?: boolean;
	} = $props();

	const isUser = message.role === 'user';

	function getPersonaIcon(persona: MentorPersona | null | undefined) {
		switch (persona) {
			case 'action_coach':
				return Target;
			case 'data_analyst':
				return BarChart3;
			default:
				return Bot;
		}
	}

	const PersonaIcon = getPersonaIcon(message.persona);
</script>

<div class="flex gap-3 {isUser ? 'flex-row-reverse' : ''}">
	<!-- Avatar -->
	<div
		class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center {isUser
			? 'bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400'
			: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400'}"
	>
		{#if isUser}
			<User class="w-4 h-4" />
		{:else}
			<PersonaIcon class="w-4 h-4" />
		{/if}
	</div>

	<!-- Message bubble -->
	<div
		class="flex-1 max-w-[85%] {isUser
			? 'bg-brand-500 text-white rounded-2xl rounded-tr-md px-4 py-2'
			: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-white rounded-2xl rounded-tl-md px-4 py-3'}"
	>
		{#if isUser}
			<p class="text-sm whitespace-pre-wrap">{message.content}</p>
		{:else}
			<div class="prose prose-sm dark:prose-invert max-w-none">
				<MarkdownContent content={message.content} />
			</div>
			{#if isStreaming}
				<span class="inline-block w-2 h-4 bg-brand-500 animate-pulse ml-1"></span>
			{/if}
		{/if}
	</div>
</div>
