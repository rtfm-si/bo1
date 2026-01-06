<script lang="ts">
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { isAuthenticated, isLoading, user } from '$lib/stores/auth';
	import { loadWorkspaces } from '$lib/stores/workspace';
	import { loadPreferences } from '$lib/stores/preferences';
	import { ActivityStatus, LOADING_MESSAGES } from '$lib/components/ui/loading';
	import { createLogger } from '$lib/utils/debug';
	import type { Snippet } from 'svelte';
	import Header from '$lib/components/Header.svelte';
	import Breadcrumb from '$lib/components/ui/Breadcrumb.svelte';
	import ServiceStatusBanner from '$lib/components/ui/ServiceStatusBanner.svelte';
	import ToastContainer from '$lib/components/ui/ToastContainer.svelte';
	import ImpersonationBanner from '$lib/components/admin/ImpersonationBanner.svelte';
	import PasswordUpgradePrompt from '$lib/components/auth/PasswordUpgradePrompt.svelte';
	import { getBreadcrumbsWithData } from '$lib/utils/breadcrumbs';
	import { breadcrumbLabels } from '$lib/stores/breadcrumbLabels';
	import { adminApi, type ImpersonationSessionResponse } from '$lib/api/admin';

	const log = createLogger('AppLayout');

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();

	let authChecked = $state(false);
	let dataLoaded = $state(false);
	let impersonationSession = $state<ImpersonationSessionResponse | null>(null);

	// Pre-read stores to ensure subscriptions happen outside reactive context
	// This prevents state_unsafe_mutation when stores are first accessed in $derived
	$breadcrumbLabels;
	$isLoading;
	$isAuthenticated;

	// Generate breadcrumbs from current path with dynamic labels
	// Use $breadcrumbLabels auto-subscription directly instead of copying to state
	const breadcrumbs = $derived(getBreadcrumbsWithData($page.url.pathname, $breadcrumbLabels));

	// Pages where we don't show breadcrumbs (top-level pages accessible from nav)
	const hideBreadcrumbPaths = ['/dashboard', '/actions', '/projects', '/datasets', '/settings'];
	const showBreadcrumbs = $derived(!hideBreadcrumbPaths.includes($page.url.pathname));

	// Check for active impersonation session from user store data
	function checkImpersonation() {
		// Impersonation metadata is now included in /me response
		// Read user data without tracking to avoid effect dependencies
		const userData = untrack(() => $user);
		if (userData?.is_impersonation) {
			// Build session data from user store
			const remainingSeconds = userData.impersonation_remaining_seconds ?? 1800;
			const expiresAt = userData.impersonation_expires_at ?? new Date(Date.now() + remainingSeconds * 1000).toISOString();
			// Defer state mutation to avoid any reactive cycle issues
			setTimeout(() => {
				impersonationSession = {
					admin_user_id: userData.real_admin_id || '',
					target_user_id: userData.id,
					target_email: userData.email,
					reason: '', // Not stored in /me response, not critical for banner
					is_write_mode: userData.impersonation_write_mode ?? false,
					started_at: new Date().toISOString(), // Approximate, not critical
					remaining_seconds: remainingSeconds,
					expires_at: expiresAt
				};
				log.log('Active impersonation session detected:', userData.email);
			}, 0);
		}
	}

	// Handle impersonation end
	function handleImpersonationEnd() {
		impersonationSession = null;
		// Reload the page to refresh user context
		window.location.reload();
	}

	// Load background data (workspaces, preferences, impersonation check)
	function loadBackgroundData() {
		if (dataLoaded) return;
		dataLoaded = true;
		// Load workspaces in background (non-blocking)
		loadWorkspaces().catch((e) => log.warn('Failed to load workspaces:', e));
		// Load user preferences (currency, etc.)
		loadPreferences().catch((e) => log.warn('Failed to load preferences:', e));
		// Check for active impersonation (admin only)
		checkImpersonation();
	}

	// React to auth state changes using $effect
	// Only track $isLoading and $isAuthenticated - use untrack for authChecked
	// to prevent circular dependency when authChecked is set
	$effect(() => {
		const loading = $isLoading;
		const authenticated = $isAuthenticated;

		log.log('Auth state changed - loading:', loading, 'authenticated:', authenticated);

		if (!loading) {
			if (!authenticated) {
				// Not authenticated - redirect to login
				goto('/login');
			} else {
				// Use untrack to read authChecked without creating a dependency
				// This prevents the effect from re-running when authChecked changes
				const alreadyChecked = untrack(() => authChecked);
				if (!alreadyChecked) {
					// Authenticated - defer state mutation outside reactive cycle
					setTimeout(() => {
						authChecked = true;
						loadBackgroundData();
					}, 0);
				}
			}
		}
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
			<div class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
				<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
					<Breadcrumb items={breadcrumbs} />
				</div>
			</div>
		{/if}
		<main id="main-content">
			{@render children()}
		</main>
		<ToastContainer />
		<!-- Password upgrade prompt for users with weak passwords -->
		<PasswordUpgradePrompt />
	</div>
{/if}
