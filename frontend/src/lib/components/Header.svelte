<script lang="ts">
	/**
	 * Header Component - Reusable navigation header with logo and auth
	 */
	import { goto, beforeNavigate } from '$app/navigation';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import NavDropdown from '$lib/components/ui/NavDropdown.svelte';
	import WorkspaceSwitcher from '$lib/components/workspace/WorkspaceSwitcher.svelte';
	import CreateWorkspaceModal from '$lib/components/workspace/CreateWorkspaceModal.svelte';
	import { isAuthenticated, user, signOut } from '$lib/stores/auth';
	import { Menu, X, ChevronDown, ChevronRight, HelpCircle } from 'lucide-svelte';

	// Check if a nav link is active (supports prefix matching for nested routes)
	function isActive(href: string): boolean {
		const pathname = $page.url.pathname;
		if (href === '/dashboard' || href === '/settings') {
			return pathname === href;
		}
		return pathname === href || pathname.startsWith(href + '/');
	}

	// Navigation link groups
	const workLinks = [
		{ href: '/actions', label: 'Actions' },
		{ href: '/projects', label: 'Projects' },
	];

	const dataLinks = [
		{ href: '/datasets', label: 'Datasets' },
		{ href: '/mentor', label: 'Mentor' },
	];

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
	let mobileWorkExpanded = $state(false);
	let mobileDataExpanded = $state(false);

	// Workspace modal state
	let showCreateWorkspaceModal = $state(false);

	function toggleMobileMenu() {
		mobileMenuOpen = !mobileMenuOpen;
		// Reset expanded groups when closing
		if (!mobileMenuOpen) {
			mobileWorkExpanded = false;
			mobileDataExpanded = false;
		}
	}

	function closeMobileMenu() {
		mobileMenuOpen = false;
		mobileWorkExpanded = false;
		mobileDataExpanded = false;
	}

	// Close mobile menu on navigation
	beforeNavigate(() => {
		mobileMenuOpen = false;
		mobileWorkExpanded = false;
		mobileDataExpanded = false;
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

	// Check if group is active (any child link is active)
	function isGroupActive(links: { href: string }[]): boolean {
		const pathname = $page.url.pathname;
		return links.some((link) => pathname === link.href || pathname.startsWith(link.href + '/'));
	}
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

			<!-- Workspace Switcher (authenticated only, desktop) -->
			{#if $isAuthenticated}
				<div class="hidden md:block ml-4">
					<WorkspaceSwitcher onCreateWorkspace={() => (showCreateWorkspaceModal = true)} />
				</div>
			{/if}

			<!-- Desktop Navigation -->
			<div class="hidden md:flex items-center gap-5">
				{#if $isAuthenticated}
					<a
						href="/dashboard"
						class={isActive('/dashboard')
							? 'text-brand-600 dark:text-brand-400 font-medium'
							: 'text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors'}
					>
						Dashboard
					</a>
					<NavDropdown label="Work" links={workLinks} isGroupActive={() => isGroupActive(workLinks)} />
					<NavDropdown label="Data" links={dataLinks} isGroupActive={() => isGroupActive(dataLinks)} />
					<a
						href="/settings"
						class={isActive('/settings')
							? 'text-brand-600 dark:text-brand-400 font-medium'
							: 'text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors'}
					>
						Settings
					</a>
					<a
						href="/help"
						class={isActive('/help')
							? 'text-brand-600 dark:text-brand-400 font-medium'
							: 'text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors'}
						title="Help Center"
					>
						<HelpCircle class="w-5 h-5" />
					</a>
					{#if $user?.is_admin}
						<a
							href="/admin"
							class={isActive('/admin')
								? 'text-amber-700 dark:text-amber-300 font-bold'
								: 'text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300 transition-colors font-medium'}
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
			<div class="px-4 py-4 space-y-1">
				{#if $isAuthenticated}
					<!-- Mobile Workspace Switcher -->
					<div class="pb-3 mb-1 border-b border-neutral-200 dark:border-neutral-700">
						<span class="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-2 block">Workspace</span>
						<WorkspaceSwitcher onCreateWorkspace={() => { closeMobileMenu(); showCreateWorkspaceModal = true; }} />
					</div>

					<a
						href="/dashboard"
						class={isActive('/dashboard')
							? 'block py-3 text-base font-medium text-brand-600 dark:text-brand-400'
							: 'block py-3 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400'}
						onclick={closeMobileMenu}
					>
						Dashboard
					</a>

					<!-- Work Group (collapsible) -->
					<div class="border-t border-neutral-100 dark:border-neutral-800">
						<button
							type="button"
							class="w-full flex items-center justify-between py-3 text-base font-medium {isGroupActive(workLinks)
								? 'text-brand-600 dark:text-brand-400'
								: 'text-neutral-700 dark:text-neutral-300'}"
							onclick={() => (mobileWorkExpanded = !mobileWorkExpanded)}
							aria-expanded={mobileWorkExpanded}
						>
							Work
							{#if mobileWorkExpanded}
								<ChevronDown class="w-5 h-5" />
							{:else}
								<ChevronRight class="w-5 h-5" />
							{/if}
						</button>
						{#if mobileWorkExpanded}
							<div class="pl-4 pb-2 space-y-1">
								{#each workLinks as link}
									<a
										href={link.href}
										class={isActive(link.href)
											? 'block py-2 text-sm font-medium text-brand-600 dark:text-brand-400'
											: 'block py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-brand-600 dark:hover:text-brand-400'}
										onclick={closeMobileMenu}
									>
										{link.label}
									</a>
								{/each}
							</div>
						{/if}
					</div>

					<!-- Data Group (collapsible) -->
					<div class="border-t border-neutral-100 dark:border-neutral-800">
						<button
							type="button"
							class="w-full flex items-center justify-between py-3 text-base font-medium {isGroupActive(dataLinks)
								? 'text-brand-600 dark:text-brand-400'
								: 'text-neutral-700 dark:text-neutral-300'}"
							onclick={() => (mobileDataExpanded = !mobileDataExpanded)}
							aria-expanded={mobileDataExpanded}
						>
							Data
							{#if mobileDataExpanded}
								<ChevronDown class="w-5 h-5" />
							{:else}
								<ChevronRight class="w-5 h-5" />
							{/if}
						</button>
						{#if mobileDataExpanded}
							<div class="pl-4 pb-2 space-y-1">
								{#each dataLinks as link}
									<a
										href={link.href}
										class={isActive(link.href)
											? 'block py-2 text-sm font-medium text-brand-600 dark:text-brand-400'
											: 'block py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-brand-600 dark:hover:text-brand-400'}
										onclick={closeMobileMenu}
									>
										{link.label}
									</a>
								{/each}
							</div>
						{/if}
					</div>

					<div class="border-t border-neutral-100 dark:border-neutral-800">
						<a
							href="/settings"
							class={isActive('/settings')
								? 'block py-3 text-base font-medium text-brand-600 dark:text-brand-400'
								: 'block py-3 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400'}
							onclick={closeMobileMenu}
						>
							Settings
						</a>
					</div>
					<div class="border-t border-neutral-100 dark:border-neutral-800">
						<a
							href="/help"
							class={isActive('/help')
								? 'block py-3 text-base font-medium text-brand-600 dark:text-brand-400'
								: 'block py-3 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400'}
							onclick={closeMobileMenu}
						>
							Help
						</a>
					</div>
					{#if $user?.is_admin}
						<div class="border-t border-neutral-100 dark:border-neutral-800">
							<a
								href="/admin"
								class={isActive('/admin')
									? 'block py-3 text-base font-bold text-amber-700 dark:text-amber-300'
									: 'block py-3 text-base font-medium text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300'}
								onclick={closeMobileMenu}
							>
								Admin
							</a>
						</div>
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
						class="block py-3 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400"
						onclick={closeMobileMenu}
					>
						How It Works
					</a>
					<a
						href="/#features"
						class="block py-3 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400"
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

<!-- Create Workspace Modal -->
<CreateWorkspaceModal bind:open={showCreateWorkspaceModal} />
