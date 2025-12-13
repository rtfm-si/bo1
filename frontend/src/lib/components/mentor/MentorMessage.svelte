<script lang="ts">
	/**
	 * MentorMessage - Display a single mentor chat message
	 */
	import type { MentorMessage as MessageType, MentorPersonaId } from '$lib/api/types';
	import { User, Bot, Target, BarChart3, Calendar, CheckSquare, Database } from 'lucide-svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';

	let {
		message,
		isStreaming = false
	}: {
		message: MessageType;
		isStreaming?: boolean;
	} = $props();

	const isUser = message.role === 'user';

	function getPersonaIcon(persona: MentorPersonaId | null | undefined) {
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

	// Parse @mentions in user content for display as chips
	interface ParsedMention {
		type: 'meeting' | 'action' | 'dataset';
		id: string;
	}

	function parseMentionsFromContent(content: string): { text: string; mentions: ParsedMention[] } {
		const mentionPattern = /@(meeting|action|dataset):([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/g;
		const mentions: ParsedMention[] = [];
		let match;

		while ((match = mentionPattern.exec(content)) !== null) {
			mentions.push({
				type: match[1] as 'meeting' | 'action' | 'dataset',
				id: match[2]
			});
		}

		// Clean text (remove @type:id patterns)
		const cleanText = content.replace(mentionPattern, '').trim().replace(/\s+/g, ' ');

		return { text: cleanText, mentions };
	}

	function getMentionUrl(type: string, id: string): string {
		switch (type) {
			case 'meeting':
				return `/meeting/${id}`;
			case 'action':
				return `/actions/${id}`;
			case 'dataset':
				return `/datasets/${id}`;
			default:
				return '#';
		}
	}

	function getMentionIcon(type: string) {
		switch (type) {
			case 'meeting':
				return Calendar;
			case 'action':
				return CheckSquare;
			case 'dataset':
				return Database;
			default:
				return null;
		}
	}

	const parsed = $derived(isUser ? parseMentionsFromContent(message.content) : null);
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
			<!-- User message with mention chips -->
			{#if parsed && parsed.mentions.length > 0}
				<p class="text-sm whitespace-pre-wrap mb-2">{parsed.text}</p>
				<div class="flex flex-wrap gap-1.5">
					{#each parsed.mentions as mention}
						{@const MentionIcon = getMentionIcon(mention.type)}
						<a
							href={getMentionUrl(mention.type, mention.id)}
							class="inline-flex items-center gap-1 px-2 py-0.5 bg-white/20 hover:bg-white/30 rounded-full text-xs font-medium transition-colors"
							title="View {mention.type}"
						>
							{#if MentionIcon}
								<svelte:component this={MentionIcon} class="w-3 h-3" />
							{/if}
							<span class="capitalize">{mention.type}</span>
						</a>
					{/each}
				</div>
			{:else}
				<p class="text-sm whitespace-pre-wrap">{message.content}</p>
			{/if}
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
