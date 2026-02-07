<script lang="ts">
	/**
	 * Meeting Report Page - Direct PDF Export
	 *
	 * Loads session data and auto-triggers print dialog for PDF export.
	 * Linked from Reports > Meetings list.
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import { generateReportHTML, type ReportAction } from '$lib/utils/pdf-report-generator';
	import type { SSEEvent } from '$lib/api/sse-events';
	import Spinner from '$lib/components/ui/Spinner.svelte';

	// sessionId is always defined when this route matches (guaranteed by [id] in path)
	const sessionId = $page.params.id as string;

	let status = $state<'loading' | 'generating' | 'ready' | 'error'>('loading');
	let errorMessage = $state('');

	onMount(async () => {
		try {
			// Load session
			const session = await apiClient.getSession(sessionId);

			if (session.status !== 'completed') {
				// Redirect to meeting page if not completed
				goto(`/meeting/${sessionId}`, { replaceState: true });
				return;
			}

			// Load events
			const eventsResponse = await apiClient.getSessionEvents(sessionId);
			const events: SSEEvent[] = eventsResponse.events || [];

			// Load actions
			let actions: ReportAction[] = [];
			try {
				const actionsResponse = await apiClient.getSessionActions(sessionId);
				actions = actionsResponse.tasks.map((task) => ({
					id: task.id,
					title: task.title,
					description: task.description || '',
					status: task.status,
					priority: (task.priority as 'high' | 'medium' | 'low') || 'medium',
					timeline: task.timeline || '',
					target_end_date: (task as { suggested_completion_date?: string }).suggested_completion_date || null,
					what_and_how: task.what_and_how || [],
					success_criteria: task.success_criteria || [],
					dependencies: task.dependencies || [],
					category: task.category || undefined,
				}));
			} catch {
				// Continue without actions
			}

			status = 'generating';

			// Generate report HTML
			// Cast session.problem to expected type (API returns {[key: string]: unknown})
			const reportHTML = generateReportHTML({
				session: {
					...session,
					problem: session.problem as { statement: string; context?: Record<string, unknown> },
				},
				events,
				sessionId: sessionId,
				actions,
			});

			// Write to document and trigger print
			document.open();
			document.write(reportHTML);
			document.close();

			status = 'ready';

			// Trigger print dialog after render
			setTimeout(() => window.print(), 300);
		} catch (err) {
			status = 'error';
			errorMessage = err instanceof Error ? err.message : 'Failed to load report';
		}
	});
</script>

<svelte:head>
	<title>Loading Report...</title>
</svelte:head>

{#if status === 'loading' || status === 'generating'}
	<div class="min-h-screen bg-white flex items-center justify-center">
		<div class="text-center">
			<Spinner size="lg" class="mx-auto mb-4" />
			<p class="text-neutral-600">
				{status === 'loading' ? 'Loading meeting data...' : 'Generating report...'}
			</p>
		</div>
	</div>
{:else if status === 'error'}
	<div class="min-h-screen bg-white flex items-center justify-center">
		<div class="text-center max-w-md">
			<div class="text-error-500 mb-4">
				<svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
				</svg>
			</div>
			<h2 class="text-xl font-semibold text-neutral-900 mb-2">Failed to load report</h2>
			<p class="text-neutral-600 mb-4">{errorMessage}</p>
			<a
				href="/meeting/{sessionId}"
				class="inline-flex items-center gap-2 text-info-600 hover:text-info-700 font-medium"
			>
				Go to meeting
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
				</svg>
			</a>
		</div>
	</div>
{/if}
