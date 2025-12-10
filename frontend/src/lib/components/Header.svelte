<script lang="ts">
	/**
	 * Header Component - Reusable navigation header with logo and auth
	 */
	import { goto, beforeNavigate } from '$app/navigation';
	import Button from '$lib/components/ui/Button.svelte';
	import { isAuthenticated, user, signOut } from '$lib/stores/auth';
	import { Menu, X } from 'lucide-svelte';

	// Props
	let {
		transparent = false,
		showCTA = true,
	}: {
		transparent?: boolean;
		showCTA?: boolean;
	} = $props();

	// Mobile menu state
	let mobileMenuOpen = $state(false);

	function toggleMobileMenu() {
		mobileMenuOpen = !mobileMenuOpen;
	}

	function closeMobileMenu() {
		mobileMenuOpen = false;
	}

	// Close mobile menu on navigation
	beforeNavigate(() => {
		mobileMenuOpen = false;
	});

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
			<!-- Mobile menu button -->
			<button
				class="md:hidden p-2 -ml-2 text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400"
				onclick={toggleMobileMenu}
				aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
				aria-expanded={mobileMenuOpen}
			>
				{#if mobileMenuOpen}
					<X class="h-6 w-6" />
				{:else}
					<Menu class="h-6 w-6" />
				{/if}
			</button>

			<!-- Logo -->
			<a href="/" class="flex items-center gap-3 group" onclick={closeMobileMenu}>
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
						href="/actions"
						class="text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
					>
						Actions
					</a>
					<a
						href="/projects"
						class="text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
					>
						Projects
					</a>
					<a
						href="/datasets"
						class="text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
					>
						Datasets
					</a>
					<a
						href="/settings"
						class="text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
					>
						Settings
					</a>
					{#if $user?.is_admin}
						<a
							href="/admin"
							class="text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300 transition-colors font-medium"
						>
							Admin
						</a>
					{/if}
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

	<!-- Mobile Navigation Menu -->
	{#if mobileMenuOpen}
		<div class="md:hidden border-t border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
			<div class="px-4 py-4 space-y-3">
				{#if $isAuthenticated}
					<a
						href="/dashboard"
						class="block py-2 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400"
						onclick={closeMobileMenu}
					>
						Dashboard
					</a>
					<a
						href="/actions"
						class="block py-2 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400"
						onclick={closeMobileMenu}
					>
						Actions
					</a>
					<a
						href="/projects"
						class="block py-2 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400"
						onclick={closeMobileMenu}
					>
						Projects
					</a>
					<a
						href="/datasets"
						class="block py-2 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400"
						onclick={closeMobileMenu}
					>
						Datasets
					</a>
					<a
						href="/settings"
						class="block py-2 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400"
						onclick={closeMobileMenu}
					>
						Settings
					</a>
					{#if $user?.is_admin}
						<a
							href="/admin"
							class="block py-2 text-base font-medium text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300"
							onclick={closeMobileMenu}
						>
							Admin
						</a>
					{/if}
					<div class="pt-3 border-t border-neutral-200 dark:border-neutral-700">
						{#if $user?.email && !$user.email.endsWith('@placeholder.local')}
							<p class="py-2 text-sm text-neutral-500 dark:text-neutral-400">
								{$user.email}
							</p>
						{/if}
						<div class="flex flex-col gap-2 pt-2">
							<Button variant="brand" size="sm" onclick={() => { closeMobileMenu(); handleNewMeeting(); }}>
								New Meeting
							</Button>
							<Button variant="ghost" size="sm" onclick={() => { closeMobileMenu(); handleSignOut(); }}>
								Sign Out
							</Button>
						</div>
					</div>
				{:else}
					<a
						href="/#how-it-works"
						class="block py-2 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400"
						onclick={closeMobileMenu}
					>
						How It Works
					</a>
					<a
						href="/#features"
						class="block py-2 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400"
						onclick={closeMobileMenu}
					>
						Features
					</a>
					<div class="pt-3 border-t border-neutral-200 dark:border-neutral-700">
						<div class="flex flex-col gap-2 pt-2">
							<Button variant="brand" size="sm" onclick={() => { closeMobileMenu(); handleGetStarted(); }}>
								Join Waitlist
							</Button>
							<Button variant="ghost" size="sm" onclick={() => { closeMobileMenu(); handleSignIn(); }}>
								Sign In
							</Button>
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</header>
