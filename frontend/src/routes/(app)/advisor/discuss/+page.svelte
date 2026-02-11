<script lang="ts">
	/**
	 * Advisor - Discuss Page
	 * AI assistant chat with conversation history
	 */
	import { page } from '$app/stores';
	import MentorChat from '$lib/components/mentor/MentorChat.svelte';
	import MentorChatHistory from '$lib/components/mentor/MentorChatHistory.svelte';

	// Read query params for pre-filling
	const initialMessage = $page.url.searchParams.get('message') || undefined;
	const initialPersona = $page.url.searchParams.get('persona') as 'general' | 'action_coach' | 'data_analyst' | undefined;
	const initialBlindspotId = $page.url.searchParams.get('blindspot_id') || undefined;
	const initialConversationId = $page.url.searchParams.get('conversation_id') || null;

	// Conversation state - initialize from URL param if provided
	let selectedConversationId = $state<string | null>(initialConversationId);
	let historyComponent: { refresh: () => void } | undefined;

	function handleSelectConversation(id: string) {
		selectedConversationId = id;
	}

	function handleNewConversation() {
		selectedConversationId = null;
	}

	function handleConversationChange(id: string | null) {
		if (id) {
			selectedConversationId = id;
			historyComponent?.refresh();
		}
	}
</script>

<svelte:head>
	<title>Discuss | Advisor | Board of One</title>
	<meta name="description" content="Chat with your AI advisor for business guidance" />
</svelte:head>

<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-6 h-[calc(100vh-4rem)] flex flex-col">
	<div class="mb-6 flex-shrink-0">
		<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">Discuss</h1>
		<p class="mt-1 text-neutral-600 dark:text-neutral-400">
			Chat with your AI advisor for strategic guidance and insights.
		</p>
	</div>

	<div class="flex gap-6 flex-1 min-h-0">
		<aside class="hidden lg:block w-64 flex-shrink-0">
			<div class="h-full bg-white dark:bg-neutral-900 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 overflow-hidden">
				<MentorChatHistory
					bind:this={historyComponent}
					selectedId={selectedConversationId}
					onSelect={handleSelectConversation}
					onNew={handleNewConversation}
				/>
			</div>
		</aside>
		<div class="flex-1 min-w-0">
			<MentorChat
				{initialMessage}
				{initialPersona}
				{initialBlindspotId}
				loadConversationId={selectedConversationId}
				onConversationChange={handleConversationChange}
			/>
		</div>
	</div>
</div>
