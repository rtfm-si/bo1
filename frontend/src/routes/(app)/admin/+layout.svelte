<script lang="ts">
	/**
	 * Admin Layout - Client-side guard for admin routes
	 * Redirects non-admin users to dashboard
	 */
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user, isLoading } from '$lib/stores/auth';
	import { RefreshCw } from 'lucide-svelte';
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();

	let checkComplete = $state(false);

	onMount(() => {
		// Wait for auth to load, then check admin status
		const unsubscribe = isLoading.subscribe((loading) => {
			if (!loading) {
				if (!$user?.is_admin) {
					goto('/dashboard');
				} else {
					checkComplete = true;
				}
			}
		});

		return unsubscribe;
	});
</script>

{#if checkComplete}
	{@render children()}
{:else}
	<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex items-center justify-center">
		<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
	</div>
{/if}
