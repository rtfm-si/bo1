<script lang="ts">
	/**
	 * Settings Layout - Shared layout with sidebar navigation
	 */
	import { page } from '$app/stores';
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();

	// Navigation item type
	interface NavItem {
		href: string;
		label: string;
		icon: string;
		badge?: string;
	}

	interface NavSection {
		title: string;
		items: NavItem[];
	}

	// Navigation structure - Context and Intelligence moved to header nav
	const navSections: NavSection[] = [
		{
			title: 'Account',
			items: [
				{ href: '/settings/account', label: 'Profile', icon: '👤' },
				{ href: '/settings/privacy', label: 'Privacy', icon: '🔒' },
				{ href: '/settings/workspace', label: 'Workspace', icon: '🏢' }
			]
		},
		{
			title: 'Intelligence',
			items: [
				{ href: '/settings/cognition', label: 'Cognitive Profile', icon: '🧠' }
			]
		},
		{
			title: 'Billing',
			items: [
				{ href: '/settings/billing', label: 'Plan & Usage', icon: '💳' }
			]
		}
	];

	// Check if current path matches nav item
	function isActive(href: string): boolean {
		return $page.url.pathname === href || $page.url.pathname.startsWith(href + '/');
	}
</script>

<svelte:head>
	<title>Settings - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
	<!-- Header -->
	<header class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center gap-4">
				<a
					href="/dashboard"
					class="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors duration-200"
					aria-label="Back to dashboard"
				>
					<svg
						class="w-5 h-5 text-slate-600 dark:text-slate-400"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M10 19l-7-7m0 0l7-7m-7 7h18"
						/>
					</svg>
				</a>
				<div>
					<h1 class="text-2xl font-bold text-slate-900 dark:text-white">Settings</h1>
					<p class="text-sm text-slate-600 dark:text-slate-400">
						Manage your account and business context
					</p>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Layout -->
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<div class="flex flex-col lg:flex-row gap-8">
			<!-- Sidebar Navigation -->
			<aside class="lg:w-64 flex-shrink-0">
				<nav class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4 sticky top-24">
					{#each navSections as section, sectionIndex}
						{#if sectionIndex > 0}
							<div class="h-px bg-slate-200 dark:bg-slate-700 my-4"></div>
						{/if}
						<div class="mb-2">
							<h2 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider px-3 mb-2">
								{section.title}
							</h2>
							<ul class="space-y-1">
								{#each section.items as item}
									<li>
										<a
											href={item.href}
											class={[
												'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
												isActive(item.href)
													? 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-400'
													: 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
											].join(' ')}
										>
											<span class="text-base">{item.icon}</span>
											<span class="flex-1">{item.label}</span>
											{#if item.badge}
												<span class="text-xs px-2 py-0.5 bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 rounded-full">
													{item.badge}
												</span>
											{/if}
										</a>
									</li>
								{/each}
							</ul>
						</div>
					{/each}
				</nav>
			</aside>

			<!-- Main Content Area -->
			<main class="flex-1 min-w-0">
				{@render children()}
			</main>
		</div>
	</div>
</div>
