<script lang="ts">
	/**
	 * Header Component - Reusable navigation header with logo and auth
	 */
	import { goto, beforeNavigate } from '$app/navigation';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import NavDropdown from '$lib/components/ui/NavDropdown.svelte';
	import FeedbackModal from '$lib/components/feedback/FeedbackModal.svelte';
	import { isAuthenticated, user, signOut } from '$lib/stores/auth';
	import { Menu, X, ChevronDown, ChevronRight, HelpCircle, MessageSquarePlus } from 'lucide-svelte';

	// Pre-read stores to ensure subscriptions happen outside reactive context
	$isAuthenticated;
	$user;

	// Check if a nav link is active (supports prefix matching for nested routes)
	function isActive(href: string): boolean {
		const pathname = $page.url.pathname;
		if (href === '/dashboard' || href === '/settings') {
			return pathname === href;
		}
		return pathname === href || pathname.startsWith(href + '/');
	}

	// Navigation link groups - consolidated under "Board" (Board of One branding)
	const boardLinks = [
		{ href: '/meeting', label: 'Meetings' },
		{ href: '/actions', label: 'Actions' },
		{ href: '/projects', label: 'Projects' },
		{ href: '/mentor', label: 'Mentor' },
		{ href: '/seo', label: 'SEO Tools' },
	];

	// Context navigation (business context settings)
	const contextLinks = [
		{ href: '/context/overview', label: 'Overview' },
		{ href: '/context/metrics', label: 'Metrics' },
		{ href: '/context/insights', label: 'Insights' },
	];

	// Reports navigation (intelligence features)
	const reportsLinks = [
		{ href: '/reports/meetings', label: 'Meetings' },
		{ href: '/reports/competitors', label: 'Competitors' },
		{ href: '/reports/benchmarks', label: 'Benchmarks' },
		{ href: '/reports/trends', label: 'Trends' },
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
	let mobileBoardExpanded = $state(false);
	let mobileContextExpanded = $state(false);
	let mobileReportsExpanded = $state(false);

	// Feedback modal state
	let showFeedbackModal = $state(false);

	function toggleMobileMenu() {
		mobileMenuOpen = !mobileMenuOpen;
		// Reset expanded groups when closing
		if (!mobileMenuOpen) {
			mobileBoardExpanded = false;
			mobileContextExpanded = false;
			mobileReportsExpanded = false;
		}
	}

	function closeMobileMenu() {
		mobileMenuOpen = false;
		mobileBoardExpanded = false;
		mobileContextExpanded = false;
		mobileReportsExpanded = false;
	}

	// Close mobile menu on navigation
	beforeNavigate(() => {
		mobileMenuOpen = false;
		mobileBoardExpanded = false;
		mobileContextExpanded = false;
		mobileReportsExpanded = false;
	});

	// Navigation handlers
	function handleSignIn() {
		goto('/login');
	}

	function handleGetStarted() {
		goto('/waitlist');
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

			<!-- Desktop Navigation -->
			<div class="hidden md:flex items-center gap-4 lg:gap-6">
				{#if $isAuthenticated}
					<a
						href="/dashboard"
						class="text-sm {isActive('/dashboard')
							? 'text-brand-600 dark:text-brand-400 font-medium'
							: 'text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors'}"
					>
						Dashboard
					</a>
					<NavDropdown label="Board" links={boardLinks} isGroupActive={() => isGroupActive(boardLinks)} dataTour="projects-nav" />
					<NavDropdown label="Context" links={contextLinks} isGroupActive={() => isGroupActive(contextLinks)} dataTour="context-nav" />
					<NavDropdown label="Reports" links={reportsLinks} isGroupActive={() => isGroupActive(reportsLinks)} />
					<a
						href="/settings"
						class="text-sm {isActive('/settings')
							? 'text-brand-600 dark:text-brand-400 font-medium'
							: 'text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors'}"
					>
						Settings
					</a>
					<a
						href="/help"
						data-tour="help-nav"
						class={isActive('/help')
							? 'text-brand-600 dark:text-brand-400 font-medium'
							: 'text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors'}
						aria-label="Help Center"
					>
						<HelpCircle class="w-4 h-4" aria-hidden="true" />
					</a>
					<button
						type="button"
						class="text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
						aria-label="Send Feedback"
						onclick={() => (showFeedbackModal = true)}
					>
						<MessageSquarePlus class="w-4 h-4" aria-hidden="true" />
					</button>
					{#if $user?.is_admin}
						<a
							href="/admin"
							class="text-sm {isActive('/admin')
								? 'text-amber-700 dark:text-amber-300 font-bold'
								: 'text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300 transition-colors font-medium'}"
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
				<div class="flex items-center gap-2">
					{#if $isAuthenticated}
						{#if $user?.email && !$user.email.endsWith('@placeholder.local')}
							<span class="text-sm text-neutral-600 dark:text-neutral-400 mr-2">
								{$user.email}
							</span>
						{/if}
						<Button variant="ghost" size="sm" onclick={handleSignOut}>
							Sign Out
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
					<a
						href="/dashboard"
						class={isActive('/dashboard')
							? 'block py-3 text-base font-medium text-brand-600 dark:text-brand-400'
							: 'block py-3 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400'}
						onclick={closeMobileMenu}
					>
						Dashboard
					</a>

					<!-- Board Group (collapsible) -->
					<div class="border-t border-neutral-100 dark:border-neutral-800">
						<button
							type="button"
							class="w-full flex items-center justify-between py-3 text-base font-medium {isGroupActive(boardLinks)
								? 'text-brand-600 dark:text-brand-400'
								: 'text-neutral-700 dark:text-neutral-300'}"
							onclick={() => (mobileBoardExpanded = !mobileBoardExpanded)}
							aria-expanded={mobileBoardExpanded}
						>
							Board
							{#if mobileBoardExpanded}
								<ChevronDown class="w-5 h-5" />
							{:else}
								<ChevronRight class="w-5 h-5" />
							{/if}
						</button>
						{#if mobileBoardExpanded}
							<div class="pl-4 pb-2 space-y-1">
								{#each boardLinks as link}
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

					<!-- Context Group (collapsible) -->
					<div class="border-t border-neutral-100 dark:border-neutral-800">
						<button
							type="button"
							class="w-full flex items-center justify-between py-3 text-base font-medium {isGroupActive(contextLinks)
								? 'text-brand-600 dark:text-brand-400'
								: 'text-neutral-700 dark:text-neutral-300'}"
							onclick={() => (mobileContextExpanded = !mobileContextExpanded)}
							aria-expanded={mobileContextExpanded}
						>
							Context
							{#if mobileContextExpanded}
								<ChevronDown class="w-5 h-5" />
							{:else}
								<ChevronRight class="w-5 h-5" />
							{/if}
						</button>
						{#if mobileContextExpanded}
							<div class="pl-4 pb-2 space-y-1">
								{#each contextLinks as link}
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

					<!-- Reports Group (collapsible) -->
					<div class="border-t border-neutral-100 dark:border-neutral-800">
						<button
							type="button"
							class="w-full flex items-center justify-between py-3 text-base font-medium {isGroupActive(reportsLinks)
								? 'text-brand-600 dark:text-brand-400'
								: 'text-neutral-700 dark:text-neutral-300'}"
							onclick={() => (mobileReportsExpanded = !mobileReportsExpanded)}
							aria-expanded={mobileReportsExpanded}
						>
							Reports
							{#if mobileReportsExpanded}
								<ChevronDown class="w-5 h-5" />
							{:else}
								<ChevronRight class="w-5 h-5" />
							{/if}
						</button>
						{#if mobileReportsExpanded}
							<div class="pl-4 pb-2 space-y-1">
								{#each reportsLinks as link}
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
					<div class="border-t border-neutral-100 dark:border-neutral-800">
						<button
							type="button"
							class="w-full text-left block py-3 text-base font-medium text-neutral-700 dark:text-neutral-300 hover:text-brand-600 dark:hover:text-brand-400"
							onclick={() => { closeMobileMenu(); showFeedbackModal = true; }}
						>
							Send Feedback
						</button>
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

<!-- Feedback Modal -->
{#if $isAuthenticated}
	<FeedbackModal bind:open={showFeedbackModal} />
{/if}
