<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { isAuthenticated, isLoading } from '$lib/stores/auth';
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();

	let authChecked = $state(false);

	onMount(() => {
		console.log('[App Layout] Checking authentication...');

		// Subscribe to auth loading state
		const unsubscribe = isLoading.subscribe((loading) => {
			console.log('[App Layout] Auth loading:', loading);

			// Once auth check completes (isLoading becomes false)
			if (!loading) {
				console.log('[App Layout] Auth check complete. Authenticated:', $isAuthenticated);

				if (!$isAuthenticated) {
					// Not authenticated - redirect to login
					console.log('[App Layout] Not authenticated, redirecting to login...');
					goto('/login');
				} else {
					// Authenticated - allow rendering
					console.log('[App Layout] Authenticated, showing protected content');
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
			<div class="text-center">
				<div class="mx-auto flex items-center justify-center mb-4">
					<svg class="animate-spin h-12 w-12 text-blue-600 dark:text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
				</div>
				<h2 class="text-xl font-semibold text-slate-900 dark:text-white mb-2">
					Verifying authentication...
				</h2>
				<p class="text-slate-600 dark:text-slate-400">
					Please wait a moment.
				</p>
			</div>
		</div>
	</div>
{:else}
	<!-- Auth verified - show protected content -->
	{@render children()}
{/if}
