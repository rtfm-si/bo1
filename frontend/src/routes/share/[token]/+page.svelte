<script lang="ts">
	/**
	 * Public share view - displays shared meeting data
	 * No authentication required
	 */
	import { Calendar, User, Clock, ExternalLink, ArrowRight } from 'lucide-svelte';
	import { Button } from '$lib/components/ui';
	import type { SharedSession } from './+page.server';

	import { formatDate } from '$lib/utils/time-formatting';
	interface Props {
		data: {
			session: SharedSession;
			token: string;
		};
	}

	let { data }: Props = $props();

	const session = $derived(data.session);


	// Parse synthesis content
	const parsedSynthesis = $derived(() => {
		if (!session.synthesis) return null;

		if (typeof session.synthesis === 'string') {
			// Return raw string wrapped in object
			return { summary: session.synthesis };
		}

		// Already an object
		return session.synthesis as Record<string, unknown>;
	});

	const expiryDate = $derived(() => {
		const date = new Date(session.expires_at);
		const now = new Date();
		const daysLeft = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
		return {
			formatted: date.toLocaleDateString(undefined, {
				month: 'short',
				day: 'numeric',
				year: 'numeric',
			}),
			daysLeft,
		};
	});
</script>

<svelte:head>
	<title>{session.title} - Shared Meeting | Board of One</title>
	<meta name="description" content="View shared meeting summary from Board of One" />
</svelte:head>

<div class="space-y-8">
	<!-- Expiry Notice -->
	{#if expiryDate().daysLeft <= 7}
		<div class="bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg p-4">
			<div class="flex items-center gap-2 text-warning-800 dark:text-warning-200">
				<Clock size={16} />
				<span class="text-sm">
					{#if expiryDate().daysLeft > 0}
						This link expires in {expiryDate().daysLeft} day{expiryDate().daysLeft === 1 ? '' : 's'}
					{:else}
						This link expires today
					{/if}
				</span>
			</div>
		</div>
	{/if}

	<!-- Header Card -->
	<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
		<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white mb-4">
			{session.title}
		</h1>

		<div class="flex flex-wrap gap-4 text-sm text-neutral-600 dark:text-neutral-400">
			<div class="flex items-center gap-2">
				<User size={16} />
				<span>Shared by {session.owner_name}</span>
			</div>
			<div class="flex items-center gap-2">
				<Calendar size={16} />
				<span>{formatDate(session.created_at)}</span>
			</div>
		</div>
	</div>

	<!-- Synthesis / Summary -->
	{#if parsedSynthesis()}
		{@const synthesis = parsedSynthesis()}
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6 space-y-6">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
				Executive Summary
			</h2>

			{#if synthesis && typeof synthesis === 'object'}
				{#if 'summary' in synthesis && synthesis.summary}
					<div class="prose dark:prose-invert max-w-none">
						<p class="text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
							{synthesis.summary}
						</p>
					</div>
				{/if}

				{#if 'key_points' in synthesis && Array.isArray(synthesis.key_points)}
					<div class="space-y-3">
						<h3 class="text-md font-medium text-neutral-900 dark:text-white">Key Points</h3>
						<ul class="space-y-2">
							{#each synthesis.key_points as point}
								<li class="flex items-start gap-2 text-neutral-700 dark:text-neutral-300">
									<ArrowRight size={16} class="mt-0.5 text-brand-500 shrink-0" />
									<span>{point}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				{#if 'recommendations' in synthesis && Array.isArray(synthesis.recommendations)}
					<div class="space-y-3">
						<h3 class="text-md font-medium text-neutral-900 dark:text-white">Recommendations</h3>
						<ul class="space-y-2">
							{#each synthesis.recommendations as rec}
								<li class="flex items-start gap-2 text-neutral-700 dark:text-neutral-300">
									<ArrowRight size={16} class="mt-0.5 text-brand-500 shrink-0" />
									<span>{typeof rec === 'string' ? rec : rec.recommendation || rec.content || JSON.stringify(rec)}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			{/if}
		</div>
	{/if}

	<!-- Conclusion -->
	{#if session.conclusion}
		<div class="bg-white dark:bg-neutral-800 rounded-lg shadow-sm border border-neutral-200 dark:border-neutral-700 p-6">
			<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
				Conclusion
			</h2>
			<div class="prose dark:prose-invert max-w-none">
				<p class="text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
					{typeof session.conclusion === 'string' ? session.conclusion : JSON.stringify(session.conclusion, null, 2)}
				</p>
			</div>
		</div>
	{/if}

	<!-- CTA -->
	<div class="bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-lg p-6 text-center space-y-4">
		<h3 class="text-lg font-semibold text-brand-900 dark:text-brand-100">
			Want to run your own strategic meetings?
		</h3>
		<p class="text-brand-700 dark:text-brand-300 text-sm">
			Board of One helps you make better decisions with AI-powered expert deliberation.
		</p>
		<Button variant="brand" size="lg" onclick={() => window.location.href = '/auth'}>
			{#snippet children()}
				<span>Get Started</span>
				<ExternalLink size={16} />
			{/snippet}
		</Button>
	</div>

	<!-- Disclaimer -->
	<p class="text-xs text-neutral-500 dark:text-neutral-400 text-center">
		This content was generated by AI and shared by {session.owner_name}.
		Always verify important decisions with qualified professionals.
	</p>
</div>
