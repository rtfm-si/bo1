<script lang="ts">
	import { onMount } from 'svelte';
	import { env } from '$env/dynamic/public';
	import { user } from '$lib/stores/auth';
	import AnalyticsChatMessage from '$lib/components/admin/AnalyticsChatMessage.svelte';
	import AnalyticsChatInput from '$lib/components/admin/AnalyticsChatInput.svelte';
	import SavedAnalysesList from '$lib/components/admin/SavedAnalysesList.svelte';
	import { adminApi, type SavedAnalysis } from '$lib/api/admin';

	interface StepData {
		step: number;
		description?: string;
		sql?: string;
		columns?: string[];
		row_count?: number;
		chart_config?: { data?: unknown[]; layout?: Record<string, unknown> } | null;
		summary?: string;
		error?: string;
	}

	interface ChatMessage {
		id: string;
		role: 'user' | 'assistant';
		content: string;
		steps?: StepData[];
		suggestions?: string[];
		isStreaming?: boolean;
	}

	let messages = $state<ChatMessage[]>([]);
	let conversationId = $state<string | null>(null);
	let model = $state('sonnet');
	let isStreaming = $state(false);
	let showSaved = $state(false);
	let savedAnalyses = $state<SavedAnalysis[]>([]);
	let chatContainer: HTMLDivElement = $state(null!);

	// Current streaming state
	let currentSteps = $state<StepData[]>([]);
	let currentSuggestions = $state<string[]>([]);

	onMount(() => {
		if (!$user?.is_admin) return;
	});

	function scrollToBottom() {
		if (chatContainer) {
			requestAnimationFrame(() => {
				chatContainer.scrollTop = chatContainer.scrollHeight;
			});
		}
	}

	async function handleSend(question: string) {
		if (isStreaming) return;

		// Add user message
		messages = [
			...messages,
			{ id: crypto.randomUUID(), role: 'user', content: question }
		];

		// Add placeholder assistant message
		const assistantId = crypto.randomUUID();
		messages = [
			...messages,
			{ id: assistantId, role: 'assistant', content: '', steps: [], isStreaming: true }
		];

		isStreaming = true;
		currentSteps = [];
		currentSuggestions = [];
		scrollToBottom();

		try {
			const baseUrl = env.PUBLIC_API_URL || 'http://localhost:8000';

			// Get CSRF token
			const csrfMatch = document.cookie.match(/(?:^|; )csrf_token=([^;]*)/);
			const csrfToken = csrfMatch ? decodeURIComponent(csrfMatch[1]) : null;

			const headers: Record<string, string> = { 'Content-Type': 'application/json' };
			if (csrfToken) headers['X-CSRF-Token'] = csrfToken;

			const response = await fetch(`${baseUrl}/api/admin/analytics-chat/ask`, {
				method: 'POST',
				credentials: 'include',
				headers,
				body: JSON.stringify({
					question,
					conversation_id: conversationId,
					model
				})
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			const reader = response.body?.getReader();
			if (!reader) throw new Error('No response body');

			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() || '';

				for (const line of lines) {
					if (line.startsWith('event: ')) {
						lastEventType = line.slice(7).trim();
						continue;
					}
					if (line.startsWith('data: ')) {
						try {
							const data = JSON.parse(line.slice(6));
							handleSSEEvent(lastEventType, data, assistantId);
							scrollToBottom();
						} catch {
							// ignore parse errors
						}
					}
				}
			}
		} catch (e) {
			console.error('Analytics chat error:', e);
			// Update the assistant message with error
			updateAssistantMessage(assistantId, {
				content: `Error: ${e instanceof Error ? e.message : 'Unknown error'}`,
				isStreaming: false
			});
		} finally {
			isStreaming = false;
			// Finalize the assistant message
			updateAssistantMessage(assistantId, {
				steps: [...currentSteps],
				suggestions: [...currentSuggestions],
				isStreaming: false
			});
		}
	}

	// We need to track event type across lines
	let lastEventType = '';

	function handleSSEEvent(eventType: string, data: Record<string, unknown>, assistantId: string) {
		switch (eventType) {
			case 'thinking': {
				const status = data.status === 'planning'
					? 'Planning analysis...'
					: `Executing ${data.step_count} steps...`;
				updateAssistantMessage(assistantId, { content: status });
				break;
			}
			case 'conversation':
				conversationId = data.conversation_id as string;
				break;
			case 'step_start': {
				const stepIdx = data.step as number;
				ensureStep(stepIdx);
				currentSteps[stepIdx] = { ...currentSteps[stepIdx], description: data.description as string };
				updateAssistantSteps(assistantId);
				break;
			}
			case 'sql': {
				const stepIdx = data.step as number;
				ensureStep(stepIdx);
				currentSteps[stepIdx] = { ...currentSteps[stepIdx], sql: data.sql as string };
				updateAssistantSteps(assistantId);
				break;
			}
			case 'data': {
				const stepIdx = data.step as number;
				ensureStep(stepIdx);
				currentSteps[stepIdx] = {
					...currentSteps[stepIdx],
					columns: data.columns as string[],
					row_count: data.row_count as number
				};
				updateAssistantSteps(assistantId);
				break;
			}
			case 'chart': {
				const stepIdx = data.step as number;
				ensureStep(stepIdx);
				currentSteps[stepIdx] = {
					...currentSteps[stepIdx],
					chart_config: data.figure_json as StepData['chart_config']
				};
				updateAssistantSteps(assistantId);
				break;
			}
			case 'step_summary': {
				const stepIdx = data.step as number;
				ensureStep(stepIdx);
				currentSteps[stepIdx] = { ...currentSteps[stepIdx], summary: data.summary as string };
				updateAssistantSteps(assistantId);
				break;
			}
			case 'step_complete':
				break;
			case 'suggestions':
				currentSuggestions = data.suggestions as string[];
				break;
			case 'done':
				break;
			case 'error':
				updateAssistantMessage(assistantId, {
					content: `Error: ${data.error}`,
					isStreaming: false
				});
				break;
		}
	}

	function ensureStep(idx: number) {
		while (currentSteps.length <= idx) {
			currentSteps.push({ step: currentSteps.length });
		}
	}

	function updateAssistantMessage(id: string, updates: Partial<ChatMessage>) {
		messages = messages.map((m) =>
			m.id === id ? { ...m, ...updates } : m
		);
	}

	function updateAssistantSteps(assistantId: string) {
		updateAssistantMessage(assistantId, { steps: [...currentSteps] });
	}

	function handleSuggestionClick(suggestion: string) {
		handleSend(suggestion);
	}

	function handleClear() {
		messages = [];
		conversationId = null;
		currentSteps = [];
		currentSuggestions = [];
	}

	async function handleSave() {
		if (messages.length < 2) return;

		// Find the last assistant message with steps
		const lastAssistant = [...messages].reverse().find(
			(m) => m.role === 'assistant' && m.steps && m.steps.length > 0
		);
		if (!lastAssistant?.steps) return;

		const lastUser = [...messages].reverse().find((m) => m.role === 'user');
		if (!lastUser) return;

		try {
			await adminApi.saveAnalyticsChatAnalysis({
				title: lastUser.content.slice(0, 100),
				description: '',
				original_question: lastUser.content,
				steps: lastAssistant.steps.map((s) => ({
					description: s.description || '',
					sql: s.sql || '',
					chart_config: s.chart_config || null
				}))
			});
		} catch (e) {
			console.error('Failed to save analysis:', e);
		}
	}

	async function loadSaved() {
		try {
			savedAnalyses = await adminApi.listAnalyticsChatSaved();
			showSaved = true;
		} catch (e) {
			console.error('Failed to load saved analyses:', e);
		}
	}

	async function handleRerun(id: string) {
		const analysis = savedAnalyses.find((a) => a.id === id);
		if (analysis) {
			showSaved = false;
			handleSend(analysis.original_question);
		}
	}

	async function handleDeleteSaved(id: string) {
		try {
			await adminApi.deleteAnalyticsChatSaved(id);
			savedAnalyses = savedAnalyses.filter((a) => a.id !== id);
		} catch (e) {
			console.error('Failed to delete analysis:', e);
		}
	}
</script>

<svelte:head>
	<title>Analytics Chat | Admin</title>
</svelte:head>

<div class="h-[calc(100vh-4rem)] flex flex-col max-w-6xl mx-auto">
	<!-- Header -->
	<div
		class="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700"
	>
		<div class="flex items-center gap-2">
			<a
				href="/admin"
				class="text-sm text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300"
			>
				Admin
			</a>
			<span class="text-neutral-300 dark:text-neutral-600">/</span>
			<h1 class="text-sm font-semibold text-neutral-900 dark:text-white">Analytics Chat</h1>
		</div>
		<div class="flex items-center gap-2">
			<button
				class="text-xs px-3 py-1.5 rounded-lg border border-neutral-200 dark:border-neutral-600 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
				onclick={loadSaved}
			>
				Saved
			</button>
			<button
				class="text-xs px-3 py-1.5 rounded-lg border border-neutral-200 dark:border-neutral-600 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-colors"
				onclick={handleClear}
			>
				Clear
			</button>
		</div>
	</div>

	<!-- Messages -->
	<div bind:this={chatContainer} class="flex-1 overflow-y-auto px-4 py-4 space-y-4">
		{#if messages.length === 0}
			<div class="flex items-center justify-center h-full">
				<div class="text-center">
					<div class="text-4xl mb-3">&#x1F4CA;</div>
					<p class="text-lg font-medium text-neutral-700 dark:text-neutral-300">
						Analytics Chat
					</p>
					<p class="text-sm text-neutral-500 dark:text-neutral-400 mt-1 max-w-md">
						Ask questions about your database in natural language.
						I'll write SQL, run queries, and visualize the results.
					</p>
				</div>
			</div>
		{:else}
			{#each messages as message (message.id)}
				<AnalyticsChatMessage
					role={message.role}
					content={message.content}
					steps={message.steps}
					suggestions={message.suggestions}
					isStreaming={message.isStreaming}
					onSuggestionClick={handleSuggestionClick}
				/>
			{/each}
		{/if}
	</div>

	<!-- Input -->
	<AnalyticsChatInput
		disabled={isStreaming}
		bind:model
		onSend={handleSend}
		onSave={messages.length >= 2 ? handleSave : undefined}
	/>
</div>

<!-- Saved analyses sidebar -->
{#if showSaved}
	<!-- Backdrop -->
	<button
		class="fixed inset-0 bg-black/20 z-40"
		onclick={() => (showSaved = false)}
		aria-label="Close saved analyses"
	></button>
	<SavedAnalysesList
		analyses={savedAnalyses}
		onRun={handleRerun}
		onDelete={handleDeleteSaved}
		onClose={() => (showSaved = false)}
	/>
{/if}
