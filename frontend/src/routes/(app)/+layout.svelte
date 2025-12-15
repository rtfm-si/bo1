<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { isAuthenticated, isLoading } from '$lib/stores/auth';
	import { loadWorkspaces } from '$lib/stores/workspace';
	import { ActivityStatus, LOADING_MESSAGES } from '$lib/components/ui/loading';
	import { createLogger } from '$lib/utils/debug';
	import type { Snippet } from 'svelte';
	import Header from '$lib/components/Header.svelte';
	import Breadcrumb from '$lib/components/ui/Breadcrumb.svelte';
	import ServiceStatusBanner from '$lib/components/ui/ServiceStatusBanner.svelte';
	import ToastContainer from '$lib/components/ui/ToastContainer.svelte';
	import ImpersonationBanner from '$lib/components/admin/ImpersonationBanner.svelte';
	import { getBreadcrumbsWithData } from '$lib/utils/breadcrumbs';
	import { breadcrumbLabels } from '$lib/stores/breadcrumbLabels';
	import { adminApi, type ImpersonationSessionResponse } from '$lib/api/admin';

	const log = createLogger('AppLayout');

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();

	let authChecked = $state(false);
	let impersonationSession = $state<ImpersonationSessionResponse | null>(null);

	// Generate breadcrumbs from current path with dynamic labels
	const breadcrumbs = $derived(getBreadcrumbsWithData($page.url.pathname, $breadcrumbLabels));

	// Pages where we don't show breadcrumbs (top-level pages accessible from nav)
	const hideBreadcrumbPaths = ['/dashboard', '/actions', '/projects', '/datasets', '/settings'];
	const showBreadcrumbs = $derived(!hideBreadcrumbPaths.includes($page.url.pathname));

	// Check for active impersonation session (admin only)
	async function checkImpersonation() {
		try {
			const status = await adminApi.getImpersonationStatus();
			if (status.is_impersonating && status.session) {
				impersonationSession = status.session;
				log.log('Active impersonation session detected:', status.session.target_email);
			}
		} catch {
			// Not an admin or no active session - ignore silently
		}
	}

	// Handle impersonation end
	function handleImpersonationEnd() {
		impersonationSession = null;
		// Reload the page to refresh user context
		window.location.reload();
	}

	onMount(() => {
		log.log('Checking authentication...');

		// Subscribe to auth loading state
		const unsubscribe = isLoading.subscribe(async (loading) => {
			// Once auth check completes (isLoading becomes false)
			if (!loading) {
				log.log('Auth check complete. Authenticated:', $isAuthenticated);

				if (!$isAuthenticated) {
					// Not authenticated - redirect to login
					goto('/login');
				} else {
					// Authenticated - allow rendering and load workspaces
					authChecked = true;
					// Load workspaces in background (non-blocking)
					loadWorkspaces().catch((e) => log.warn('Failed to load workspaces:', e));
					// Check for active impersonation (admin only)
					checkImpersonation();
				}
			}
		});

		return unsubscribe;
	});
</script>

{#if !authChecked}
	<!-- Show loading state while checking auth -->
	<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 px-4" data-testid="auth-loading">
		<div class="max-w-md w-full bg-white dark:bg-slate-800 rounded-lg shadow-lg p-8 border border-slate-200 dark:border-slate-700">
			<ActivityStatus
				variant="card"
				message={LOADING_MESSAGES.auth.verifying}
				phase={LOADING_MESSAGES.generic.pleaseWait}
			/>
		</div>
	</div>
{:else}
	<!-- Auth verified - show protected content -->
	<div class="min-h-screen bg-slate-50 dark:bg-slate-900">
		<!-- Skip link for keyboard navigation (a11y) -->
		<a
			href="#main-content"
			class="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-brand-600 focus:text-white focus:rounded-md focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500"
		>
			Skip to main content
		</a>
		{#if impersonationSession}
			<ImpersonationBanner session={impersonationSession} onEnd={handleImpersonationEnd} />
		{/if}
		<ServiceStatusBanner />
		<Header />
		{#if showBreadcrumbs && breadcrumbs.length > 0}
			<nav aria-label="Breadcrumb" class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
				<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
					<Breadcrumb items={breadcrumbs} />
				</div>
			</nav>
		{/if}
		<main id="main-content">
			{@render children()}
		</main>
		<ToastContainer />
	</div>
{/if}
