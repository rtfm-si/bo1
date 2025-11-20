<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';

	const sessionId = $page.params.id;

	interface SessionData {
		id: string;
		problem_statement: string;
		status: string;
		phase: string;
		round_number: number;
		total_cost: number;
		created_at: string;
	}

	interface StreamEvent {
		type: string;
		data: any;
		timestamp: string;
	}

	let session: SessionData | null = null;
	let events: StreamEvent[] = [];
	let isLoading = true;
	let error: string | null = null;
	let eventSource: EventSource | null = null;
	let autoScroll = true;

	onMount(async () => {
		const unsubscribe = isAuthenticated.subscribe((authenticated) => {
			if (!authenticated) {
				goto('/login');
			}
		});

		await loadSession();
		startEventStream();

		return unsubscribe;
	});

	onDestroy(() => {
		if (eventSource) {
			eventSource.close();
		}
	});

	async function loadSession() {
		try {
			const response = await fetch(`/api/v1/sessions/${sessionId}`, {
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error('Failed to load session');
			}

			session = await response.json();
			isLoading = false;
		} catch (err) {
			console.error('Failed to load session:', err);
			error = err instanceof Error ? err.message : 'Failed to load session';
			isLoading = false;
		}
	}

	function startEventStream() {
		eventSource = new EventSource(`/api/stream/deliberation/${sessionId}`);

		eventSource.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				events = [...events, {
					type: data.type || 'message',
					data: data,
					timestamp: new Date().toISOString()
				}];

				// Auto-scroll to bottom
				if (autoScroll) {
					setTimeout(() => {
						const container = document.getElementById('events-container');
						if (container) {
							container.scrollTop = container.scrollHeight;
						}
					}, 100);
				}

				// Update session data if present
				if (data.session) {
					session = { ...session, ...data.session };
				}

			} catch (err) {
				console.error('Failed to parse SSE event:', err);
			}
		};

		eventSource.addEventListener('phase_change', (event: MessageEvent) => {
			const data = JSON.parse(event.data);
			events = [...events, {
				type: 'phase_change',
				data: data,
				timestamp: new Date().toISOString()
			}];
		});

		eventSource.addEventListener('persona_contribution', (event: MessageEvent) => {
			const data = JSON.parse(event.data);
			events = [...events, {
				type: 'persona_contribution',
				data: data,
				timestamp: new Date().toISOString()
			}];
		});

		eventSource.addEventListener('synthesis', (event: MessageEvent) => {
			const data = JSON.parse(event.data);
			events = [...events, {
				type: 'synthesis',
				data: data,
				timestamp: new Date().toISOString()
			}];
		});

		eventSource.addEventListener('complete', (event: MessageEvent) => {
			events = [...events, {
				type: 'complete',
				data: JSON.parse(event.data),
				timestamp: new Date().toISOString()
			}];
			eventSource?.close();
		});

		eventSource.onerror = () => {
			console.error('SSE connection error');
			eventSource?.close();
		};
	}

	async function handlePause() {
		try {
			await fetch(`/api/v1/sessions/${sessionId}/pause`, {
				method: 'POST',
				credentials: 'include'
			});
		} catch (err) {
			console.error('Failed to pause session:', err);
		}
	}

	async function handleResume() {
		try {
			await fetch(`/api/v1/sessions/${sessionId}/resume`, {
				method: 'POST',
				credentials: 'include'
			});
			startEventStream();
		} catch (err) {
			console.error('Failed to resume session:', err);
		}
	}

	async function handleKill() {
		if (!confirm('Are you sure you want to stop this meeting? This cannot be undone.')) {
			return;
		}

		try {
			await fetch(`/api/v1/sessions/${sessionId}/kill`, {
				method: 'POST',
				credentials: 'include'
			});
			eventSource?.close();
		} catch (err) {
			console.error('Failed to kill session:', err);
		}
	}

	function getEventIcon(type: string): string {
		const icons = {
			phase_change: '🔄',
			persona_contribution: '💭',
			synthesis: '✨',
			complete: '✅',
			error: '❌',
			message: 'ℹ️'
		};
		return icons[type as keyof typeof icons] || 'ℹ️';
	}

	function formatTimestamp(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleTimeString();
	}
</script>

<svelte:head>
	<title>Meeting {sessionId} - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
	<!-- Header -->
	<header class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-10">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/dashboard"
						class="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors duration-200"
					>
						<svg class="w-5 h-5 text-slate-600 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</a>
					<div>
						<h1 class="text-xl font-bold text-slate-900 dark:text-white">
							Meeting in Progress
						</h1>
						{#if session}
							<p class="text-sm text-slate-600 dark:text-slate-400">
								{session.phase.replace(/_/g, ' ')} - Round {session.round_number}
							</p>
						{/if}
					</div>
				</div>

				<div class="flex items-center gap-2">
					{#if session?.status === 'active'}
						<button
							on:click={handlePause}
							class="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white text-sm font-medium rounded-lg transition-colors duration-200"
						>
							⏸ Pause
						</button>
					{:else if session?.status === 'paused'}
						<button
							on:click={handleResume}
							class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors duration-200"
						>
							▶ Resume
						</button>
					{/if}

					<button
						on:click={handleKill}
						class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors duration-200"
					>
						⏹ Stop
					</button>

					{#if session}
						<div class="px-4 py-2 bg-slate-100 dark:bg-slate-700 rounded-lg text-sm text-slate-700 dark:text-slate-300">
							${session.total_cost.toFixed(2)}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
			<!-- Events Stream -->
			<div class="lg:col-span-2">
				<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700">
					<div class="border-b border-slate-200 dark:border-slate-700 p-4 flex items-center justify-between">
						<h2 class="text-lg font-semibold text-slate-900 dark:text-white">
							Deliberation Stream
						</h2>
						<label class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
							<input
								type="checkbox"
								bind:checked={autoScroll}
								class="rounded"
							/>
							Auto-scroll
						</label>
					</div>

					<div
						id="events-container"
						class="h-[600px] overflow-y-auto p-4 space-y-4"
					>
						{#if isLoading}
							<div class="flex items-center justify-center h-full">
								<svg class="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
							</div>
						{:else if events.length === 0}
							<div class="flex items-center justify-center h-full text-slate-500 dark:text-slate-400">
								<p>Waiting for deliberation to start...</p>
							</div>
						{:else}
							{#each events as event}
								<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
									<div class="flex items-start gap-3">
										<span class="text-2xl">{getEventIcon(event.type)}</span>
										<div class="flex-1">
											<div class="flex items-center justify-between mb-2">
												<span class="text-sm font-semibold text-slate-900 dark:text-white">
													{event.type.replace(/_/g, ' ').toUpperCase()}
												</span>
												<span class="text-xs text-slate-500 dark:text-slate-400">
													{formatTimestamp(event.timestamp)}
												</span>
											</div>

											{#if event.type === 'persona_contribution'}
												<div class="mb-2">
													<span class="inline-block px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 text-xs font-medium rounded">
														{event.data.persona_name}
													</span>
												</div>
												<p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
													{event.data.content}
												</p>
											{:else if event.type === 'synthesis'}
												<p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
													{event.data.content}
												</p>
											{:else if event.type === 'phase_change'}
												<p class="text-sm text-slate-700 dark:text-slate-300">
													Moving to: <strong>{event.data.new_phase}</strong>
												</p>
											{:else}
												<pre class="text-xs text-slate-600 dark:text-slate-400 overflow-x-auto">
													{JSON.stringify(event.data, null, 2)}
												</pre>
											{/if}
										</div>
									</div>
								</div>
							{/each}
						{/if}
					</div>
				</div>
			</div>

			<!-- Sidebar -->
			<div class="space-y-6">
				<!-- Problem Statement -->
				{#if session}
					<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-6">
						<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-3">
							Problem Statement
						</h3>
						<p class="text-sm text-slate-700 dark:text-slate-300">
							{session.problem_statement}
						</p>
					</div>

					<!-- Status Card -->
					<div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-6">
						<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">
							Status
						</h3>
						<dl class="space-y-3 text-sm">
							<div>
								<dt class="text-slate-600 dark:text-slate-400">Status</dt>
								<dd class="font-medium text-slate-900 dark:text-white mt-1">
									{session.status.toUpperCase()}
								</dd>
							</div>
							<div>
								<dt class="text-slate-600 dark:text-slate-400">Phase</dt>
								<dd class="font-medium text-slate-900 dark:text-white mt-1">
									{session.phase.replace(/_/g, ' ')}
								</dd>
							</div>
							<div>
								<dt class="text-slate-600 dark:text-slate-400">Round</dt>
								<dd class="font-medium text-slate-900 dark:text-white mt-1">
									{session.round_number}
								</dd>
							</div>
							<div>
								<dt class="text-slate-600 dark:text-slate-400">Cost</dt>
								<dd class="font-medium text-slate-900 dark:text-white mt-1">
									${session.total_cost.toFixed(2)}
								</dd>
							</div>
						</dl>
					</div>

					<!-- Actions -->
					{#if session.status === 'completed'}
						<a
							href="/meeting/{sessionId}/results"
							class="block w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white text-center font-medium rounded-lg transition-colors duration-200"
						>
							View Results
						</a>
					{/if}
				{/if}
			</div>
		</div>
	</main>
</div>
