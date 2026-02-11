<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/api/client';
	import type { DateActivitiesResponse } from '$lib/api/types';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';

	import { formatDate } from '$lib/utils/time-formatting';
	const dateParam = $derived($page.params.date ?? '');

	// Validate YYYY-MM-DD format
	const isValidDate = $derived(/^\d{4}-\d{2}-\d{2}$/.test(dateParam));

	const activitiesData = useDataFetch(() => apiClient.getActivitiesByDate(dateParam));

	$effect(() => {
		if (isValidDate) {
			activitiesData.fetch();
		}
	});


	const typeLabels: Record<string, string> = {
		session: 'Meetings',
		action_completed: 'Actions Completed',
		action_started: 'Actions Started',
		mentor_session: 'Advisor Sessions',
		planned_start: 'Planned Starts',
		planned_due: 'Due Dates'
	};

	const typeIcons: Record<string, string> = {
		session: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
		action_completed: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
		action_started: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
		mentor_session: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
		planned_start: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
		planned_due: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2'
	};

	// Group activities by type
	const grouped = $derived.by(() => {
		if (!activitiesData.data?.activities) return {};
		const groups: Record<string, typeof activitiesData.data.activities> = {};
		for (const item of activitiesData.data.activities) {
			if (!groups[item.type]) groups[item.type] = [];
			groups[item.type].push(item);
		}
		return groups;
	});
</script>

<svelte:head>
	<title>{isValidDate ? formatDate(dateParam) : 'Invalid Date'} - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-900 dark:to-neutral-800">
	<div class="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-8">
		<!-- Back button + heading -->
		<div class="mb-6">
			<button
				onclick={() => goto('/dashboard')}
				class="flex items-center gap-1 text-sm text-brand-600 dark:text-brand-400 hover:underline mb-3"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
				Back to Dashboard
			</button>

			{#if isValidDate}
				<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">
					{formatDate(dateParam)}
				</h1>
			{:else}
				<h1 class="text-2xl font-bold text-error-600 dark:text-error-400">Invalid date format</h1>
				<p class="mt-2 text-neutral-600 dark:text-neutral-400">Expected YYYY-MM-DD format.</p>
			{/if}
		</div>

		{#if !isValidDate}
			<!-- Invalid date — nothing to render -->
		{:else if activitiesData.isLoading}
			<div class="space-y-4">
				{#each Array(3) as _, i (i)}
					<ShimmerSkeleton type="card" />
				{/each}
			</div>
		{:else if activitiesData.error}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-error-200 dark:border-error-800 p-6 text-center">
				<p class="text-error-600 dark:text-error-400">{activitiesData.error}</p>
			</div>
		{:else if !activitiesData.data || activitiesData.data.total === 0}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
				<svg class="w-12 h-12 mx-auto text-neutral-300 dark:text-neutral-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
				</svg>
				<p class="text-neutral-500 dark:text-neutral-400">No activity on this date</p>
			</div>
		{:else}
			<!-- Grouped activity list -->
			<div class="space-y-6">
				{#each Object.entries(grouped) as [type, items] (type)}
					<div>
						<h2 class="flex items-center gap-2 text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={typeIcons[type] || typeIcons.session} />
							</svg>
							{typeLabels[type] || type}
							<span class="text-xs font-normal text-neutral-400 dark:text-neutral-500">({items.length})</span>
						</h2>

						<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each items as item (item.id)}
								{#if item.url}
									<a
										href={item.url}
										class="flex items-center gap-3 px-4 py-3 hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors"
									>
										<span class="flex-1 min-w-0 text-sm text-neutral-900 dark:text-white truncate">{item.title}</span>
										<svg class="w-4 h-4 text-neutral-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
										</svg>
									</a>
								{:else}
									<div class="flex items-center gap-3 px-4 py-3">
										<span class="flex-1 min-w-0 text-sm text-neutral-900 dark:text-white truncate">{item.title}</span>
									</div>
								{/if}
							{/each}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
