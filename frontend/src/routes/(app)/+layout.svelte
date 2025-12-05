<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isAuthenticated, isLoading } from '$lib/stores/auth';
	import { ActivityStatus, LOADING_MESSAGES } from '$lib/components/ui/loading';
	import { createLogger } from '$lib/utils/debug';
	import type { Snippet } from 'svelte';

	const log = createLogger('AppLayout');

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();

	let authChecked = $state(false);

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
	{@render children()}
{/if}
