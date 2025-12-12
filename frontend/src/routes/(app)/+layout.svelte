<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { isAuthenticated, isLoading } from '$lib/stores/auth';
	import { ActivityStatus, LOADING_MESSAGES } from '$lib/components/ui/loading';
	import { createLogger } from '$lib/utils/debug';
	import type { Snippet } from 'svelte';
	import Header from '$lib/components/Header.svelte';
	import Breadcrumb from '$lib/components/ui/Breadcrumb.svelte';
	import ServiceStatusBanner from '$lib/components/ui/ServiceStatusBanner.svelte';
	import { getBreadcrumbsWithData } from '$lib/utils/breadcrumbs';
	import { breadcrumbLabels } from '$lib/stores/breadcrumbLabels';

	const log = createLogger('AppLayout');

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();

	let authChecked = $state(false);

	// Generate breadcrumbs from current path with dynamic labels
	const breadcrumbs = $derived(getBreadcrumbsWithData($page.url.pathname, $breadcrumbLabels));

	// Pages where we don't show breadcrumbs (top-level pages accessible from nav)
	const hideBreadcrumbPaths = ['/dashboard', '/actions', '/projects', '/datasets', '/settings'];
	const showBreadcrumbs = $derived(!hideBreadcrumbPaths.includes($page.url.pathname));

	onMount(() => {
		log.log('Checking authentication...');

		// Subscribe to auth loading state
		const unsubscribe = isLoading.subscribe((loading) => {
			// Once auth check completes (isLoading becomes false)
			if (!loading) {
				log.log('Auth check complete. Authenticated:', $isAuthenticated);

				if (!$isAuthenticated) {
					// Not authenticated - redirect to login
					goto('/login');
				} else {
					// Authenticated - allow rendering
					authChecked = true;
				}
			}
		});

		return unsubscribe;
	});
</script>

{#if !authChecked}
	<!-- Show loading state while checking auth -->
	<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 px-4">
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
		<ServiceStatusBanner />
		<Header />
		{#if showBreadcrumbs && breadcrumbs.length > 0}
			<div class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
				<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
					<Breadcrumb items={breadcrumbs} />
				</div>
			</div>
		{/if}
		{@render children()}
	</div>
{/if}
