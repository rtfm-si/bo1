<script lang="ts">
	/**
	 * Mentor Chat Page
	 *
	 * AI-powered business mentor for strategic guidance,
	 * action coaching, and data insights.
	 */
	import MentorChat from '$lib/components/mentor/MentorChat.svelte';
	import Breadcrumb from '$lib/components/ui/Breadcrumb.svelte';
</script>

<svelte:head>
	<title>Mentor | Board of One</title>
	<meta
		name="description"
		content="Get AI-powered business guidance from your personal mentor"
	/>
</svelte:head>

<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
	<!-- Breadcrumb -->
	<div class="mb-6">
		<Breadcrumb
			items={[
				{ label: 'Dashboard', href: '/dashboard' },
				{ label: 'Mentor', href: '/mentor' }
			]}
		/>
	</div>

	<!-- Page Header -->
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-neutral-900 dark:text-white">
			Business Mentor
		</h1>
		<p class="mt-1 text-neutral-600 dark:text-neutral-400">
			Get personalized guidance using your business context, meetings, actions, and data.
		</p>
	</div>

	<!-- Chat Interface -->
	<MentorChat />

	<!-- Tips -->
	<div class="mt-6 p-4 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
		<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
			Tips for better guidance
		</h3>
		<ul class="text-sm text-neutral-600 dark:text-neutral-400 space-y-1">
			<li>Ask specific questions about your business challenges</li>
			<li>Use <strong>Action Coach</strong> when managing tasks and priorities</li>
			<li>For data-specific questions, try the dedicated <a href="/analysis" class="text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 underline">Analysis</a> page</li>
			<li>The mentor uses your business context automatically</li>
		</ul>
	</div>
</div>
