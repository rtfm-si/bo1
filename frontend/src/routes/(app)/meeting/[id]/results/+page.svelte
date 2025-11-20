<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';

	const sessionId = $page.params.id;
	let session: any = null;
	let synthesis: string = '';

	onMount(async () => {
		const response = await fetch(`/api/v1/sessions/${sessionId}`, {
			credentials: 'include'
		});
		session = await response.json();
		synthesis = session.final_synthesis || 'Synthesis pending...';
	});
</script>

<div class="min-h-screen bg-slate-50 dark:bg-slate-900 p-8">
	<div class="max-w-4xl mx-auto">
		<a href="/dashboard" class="text-blue-600 hover:text-blue-700 mb-4 inline-block">← Back to Dashboard</a>

		<h1 class="text-3xl font-bold mb-6">Meeting Results</h1>

		{#if session}
			<div class="bg-white dark:bg-slate-800 rounded-lg p-8 mb-6 border">
				<h2 class="text-xl font-semibold mb-4">Problem Statement</h2>
				<p class="text-slate-700 dark:text-slate-300">{session.problem_statement}</p>
			</div>

			<div class="bg-white dark:bg-slate-800 rounded-lg p-8 border">
				<h2 class="text-xl font-semibold mb-4">Final Synthesis</h2>
				<div class="prose dark:prose-invert max-w-none">
					<p class="whitespace-pre-wrap text-slate-700 dark:text-slate-300">{synthesis}</p>
				</div>
			</div>

			<div class="mt-6 grid grid-cols-2 gap-4 text-sm">
				<div class="bg-white dark:bg-slate-800 p-4 rounded-lg border">
					<p class="text-slate-600 dark:text-slate-400">Rounds</p>
					<p class="text-2xl font-bold">{session.round_number}</p>
				</div>
				<div class="bg-white dark:bg-slate-800 p-4 rounded-lg border">
					<p class="text-slate-600 dark:text-slate-400">Status</p>
					<p class="text-2xl font-bold">{session.status}</p>
				</div>
			</div>
		{/if}
	</div>
</div>
