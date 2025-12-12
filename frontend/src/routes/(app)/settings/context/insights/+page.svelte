<script lang="ts">
	/**
	 * Insights - Clarifications learned from meetings
	 *
	 * Displays Q&A pairs from clarifying questions answered during meetings.
	 * These insights help improve future meetings by providing relevant context.
	 */
	import { onMount } from 'svelte';
	import { apiClient, type ClarificationInsight } from '$lib/api/client';
	import Alert from '$lib/components/ui/Alert.svelte';

	// State
	let insights = $state<ClarificationInsight[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let deletingQuestion = $state<string | null>(null);
	let deleteSuccess = $state<string | null>(null);
	let editingQuestion = $state<string | null>(null);
	let editValue = $state('');
	let isSaving = $state(false);

	onMount(async () => {
		await loadInsights();
	});

	async function loadInsights() {
		isLoading = true;
		error = null;

		try {
			const response = await apiClient.getInsights();
			insights = response.clarifications;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load insights';
			console.error('Failed to load insights:', e);
		} finally {
			isLoading = false;
		}
	}

	function openEditModal(question: string, answer: string) {
		editingQuestion = question;
		editValue = answer;
	}

	function closeEditModal() {
		editingQuestion = null;
		editValue = '';
	}

	async function saveEdit() {
		if (!editingQuestion || !editValue.trim()) return;

		isSaving = true;
		try {
			const updated = await apiClient.updateInsight(editingQuestion, editValue.trim());
			// Update the insight in the list
			const index = insights.findIndex((i) => i.question === editingQuestion);
			if (index !== -1) {
				insights[index] = updated;
			}
			closeEditModal();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update insight';
		} finally {
			isSaving = false;
		}
	}

	async function deleteInsight(question: string) {
		deletingQuestion = question;

		try {
			await apiClient.deleteInsight(question);
			// Remove from local state
			insights = insights.filter((i) => i.question !== question);
			deleteSuccess = question;
			setTimeout(() => {
				deleteSuccess = null;
			}, 2000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete insight';
		} finally {
			deletingQuestion = null;
		}
	}

	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return 'Unknown date';
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatSessionId(sessionId: string | undefined): string {
		if (!sessionId) return 'Unknown meeting';
		// Show last 8 characters of session ID for brevity
		return sessionId.length > 12 ? `...${sessionId.slice(-8)}` : sessionId;
	}
</script>

<svelte:head>
	<title>Insights - Board of One</title>
</svelte:head>

<div class="space-y-6">
	<!-- Header -->
	<div
		class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
	>
		<div class="flex items-center justify-between">
			<div>
				<h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-2">Meeting Insights</h2>
				<p class="text-slate-600 dark:text-slate-400">
					Information gathered from clarifying questions during your meetings. These help improve
					future recommendations.
				</p>
			</div>
			{#if insights.length > 0}
				<span
					class="px-3 py-1 text-sm font-medium bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-full"
				>
					{insights.length} insight{insights.length !== 1 ? 's' : ''}
				</span>
			{/if}
		</div>
	</div>

	<!-- Error Alert -->
	{#if error}
		<Alert variant="error">
			{error}
			<button
				class="ml-2 underline"
				onclick={() => {
					error = null;
				}}
			>
				Dismiss
			</button>
		</Alert>
	{/if}

	<!-- Loading State -->
	{#if isLoading}
		<div class="flex items-center justify-center py-12">
			<div
				class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"
			></div>
		</div>
	{:else if insights.length === 0}
		<!-- Empty State -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-12 text-center"
		>
			<div class="text-4xl mb-4">
				<span role="img" aria-label="lightbulb">&#128161;</span>
			</div>
			<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-2">No insights yet</h3>
			<p class="text-slate-600 dark:text-slate-400 max-w-md mx-auto">
				When you answer clarifying questions during meetings, they'll appear here. These help our
				experts give you better recommendations in future meetings.
			</p>
		</div>
	{:else}
		<!-- Insights List -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 divide-y divide-slate-200 dark:divide-slate-700"
		>
			{#each insights as insight (insight.question)}
				<div class="p-6 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group">
					<div class="flex items-start justify-between gap-4">
						<div class="flex-1 min-w-0">
							<!-- Question -->
							<div class="flex items-start gap-2 mb-3">
								<span
									class="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 text-xs font-semibold"
								>
									Q
								</span>
								<p class="font-medium text-slate-900 dark:text-white">
									{insight.question}
								</p>
							</div>

							<!-- Answer -->
							<div class="flex items-start gap-2 mb-3 ml-8">
								<span
									class="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-xs font-semibold"
								>
									A
								</span>
								<p class="text-slate-700 dark:text-slate-300">
									{insight.answer}
								</p>
							</div>

							<!-- Metadata -->
							<div class="ml-8 flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
								{#if insight.answered_at}
									<span class="flex items-center gap-1">
										<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
											/>
										</svg>
										{formatDate(insight.answered_at)}
									</span>
								{/if}
								{#if insight.session_id}
									<a
										href="/meeting/{insight.session_id}"
										class="flex items-center gap-1 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
									>
										<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
											/>
										</svg>
										Meeting {formatSessionId(insight.session_id)}
									</a>
								{/if}
							</div>
						</div>

						<!-- Action Buttons -->
						<div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
							<!-- Edit Button -->
							<button
								class="p-2 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
								onclick={() => openEditModal(insight.question, insight.answer)}
								disabled={editingQuestion === insight.question}
								title="Edit this insight"
							>
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
									/>
								</svg>
							</button>

							<!-- Delete Button -->
							<button
								class="p-2 text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
								onclick={() => deleteInsight(insight.question)}
								disabled={deletingQuestion === insight.question}
								title="Delete this insight"
							>
								{#if deletingQuestion === insight.question}
									<div
										class="w-5 h-5 border-2 border-red-600 border-t-transparent rounded-full animate-spin"
									></div>
								{:else}
									<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
										/>
									</svg>
								{/if}
							</button>
						</div>
					</div>

					{#if deleteSuccess === insight.question}
						<div class="mt-2 text-sm text-green-600 dark:text-green-400">Deleted!</div>
					{/if}
				</div>
			{/each}
		</div>

		<!-- Info Box -->
		<div
			class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4"
		>
			<div class="flex gap-3">
				<svg
					class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<div class="text-sm text-blue-900 dark:text-blue-200">
					<p class="font-semibold mb-1">How insights improve your meetings</p>
					<p class="text-blue-800 dark:text-blue-300">
						When you answer clarifying questions, those answers are saved here and automatically
						used in future meetings. This means experts don't need to ask the same questions again,
						and they can provide more personalized recommendations from the start.
					</p>
				</div>
			</div>
		</div>
	{/if}

	<!-- Edit Modal -->
	{#if editingQuestion}
		<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50">
			<div
				class="bg-white dark:bg-slate-800 rounded-xl shadow-lg max-w-md w-full border border-slate-200 dark:border-slate-700"
			>
				<!-- Header -->
				<div class="border-b border-slate-200 dark:border-slate-700 p-6">
					<h3 class="text-lg font-semibold text-slate-900 dark:text-white">Edit Insight</h3>
					<p class="text-sm text-slate-600 dark:text-slate-400 mt-1">
						Update your answer to help keep your business context current.
					</p>
				</div>

				<!-- Content -->
				<div class="p-6 space-y-4">
					<!-- Question (read-only) -->
					<div>
						<span class="block text-sm font-medium text-slate-900 dark:text-white mb-2">
							Question
						</span>
						<p class="p-3 bg-slate-100 dark:bg-slate-700/50 text-slate-700 dark:text-slate-300 rounded-lg text-sm">
							{editingQuestion}
						</p>
					</div>

					<!-- Answer (editable) -->
					<div>
						<label for="edit-answer" class="block text-sm font-medium text-slate-900 dark:text-white mb-2">
							Your Answer
						</label>
						<textarea
							id="edit-answer"
							bind:value={editValue}
							class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-500 dark:placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
							rows="4"
							disabled={isSaving}
						></textarea>
					</div>
				</div>

				<!-- Footer -->
				<div class="border-t border-slate-200 dark:border-slate-700 p-6 flex gap-3 justify-end">
					<button
						class="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
						onclick={closeEditModal}
						disabled={isSaving}
					>
						Cancel
					</button>
					<button
						class="px-4 py-2 text-sm font-medium bg-brand-600 hover:bg-brand-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
						onclick={saveEdit}
						disabled={isSaving || !editValue.trim()}
					>
						{#if isSaving}
							<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
							Saving...
						{:else}
							Save
						{/if}
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
