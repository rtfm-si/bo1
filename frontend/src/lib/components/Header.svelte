<script lang="ts">
	/**
	 * Header Component - Reusable navigation header with logo and auth
	 */
	import { goto } from '$app/navigation';
	import Button from '$lib/components/ui/Button.svelte';
	import { isAuthenticated, user, signOut } from '$lib/stores/auth';

	// Props
	let {
		transparent = false,
		showCTA = true,
	}: {
		transparent?: boolean;
		showCTA?: boolean;
	} = $props();

	// Navigation handlers
	function handleSignIn() {
		goto('/login');
	}

	function handleGetStarted() {
		goto('/waitlist');
	}

	function handleNewMeeting() {
		goto('/meeting/new');
	}

	async function handleSignOut() {
		await signOut();
		goto('/');
	}

	const headerClasses = $derived(
		transparent
			? 'bg-transparent'
			: 'bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800'
	);
</script>

<header class={`sticky top-0 z-50 ${headerClasses}`}>
	<nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
		<div class="flex items-center justify-between h-16">
			<!-- Logo -->
			<a href="/" class="flex items-center gap-3 group">
				<img
					src="/logo.svg"
					alt="Board of One"
					class="h-10 w-10 transition-transform group-hover:scale-105"
				/>
				<span
					class="text-xl font-bold text-neutral-900 dark:text-neutral-100 hidden sm:block"
				>
					Board of One
				</span>
			</a>

			<!-- Desktop Navigation -->
			<div class="hidden md:flex items-center gap-6">
				{#if $isAuthenticated}
					<a
						href="/dashboard"
						class="text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
					>
						Dashboard
					</a>
					<a
						href="/settings"
						class="text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
					>
						Settings
					</a>
				{:else}
					<a
						href="/#how-it-works"
						class="text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
					>
						How It Works
					</a>
					<a
						href="/#features"
						class="text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
					>
						Features
					</a>
				{/if}
			</div>

			<!-- CTA Buttons -->
			{#if showCTA}
				<div class="flex items-center gap-3">
					{#if $isAuthenticated}
						{#if $user?.email && !$user.email.endsWith('@placeholder.local')}
							<span class="text-sm text-neutral-600 dark:text-neutral-400 mr-2">
								{$user.email}
							</span>
						{/if}
						<Button variant="ghost" size="sm" onclick={handleSignOut}>
							Sign Out
						</Button>
						<Button variant="brand" size="sm" onclick={handleNewMeeting}>
							New Meeting
						</Button>
					{:else}
						<Button variant="ghost" size="sm" onclick={handleSignIn}> Sign In </Button>
						<Button variant="brand" size="sm" onclick={handleGetStarted}> Join Waitlist </Button>
					{/if}
				</div>
			{/if}
		</div>
	</nav>
</header>
